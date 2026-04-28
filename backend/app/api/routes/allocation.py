"""
VASAE Allocation API Routes
----------------------------
Triggers and returns allocation cycle results.
This is the heart of the real-time engine.
"""

import time
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.dependencies import get_current_user, require_roles
from app.models.task import Task
from app.models.volunteer import Volunteer
from app.models.assignment import Assignment
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.volunteer_schema import (
    AllocationResult,
    AssignmentResponse,
    ExplainabilityResponse,
    ExplainabilityFactors,
    AlternativeCandidate,
)
from app.core.learning import extract_feature_vector
from app.core.scoring import (
    TaskScoreInput,
    VolunteerScoreInput,
    ScoringWeights,
    compute_vas,
)
from app.core.allocation import allocation_cycle, AllocationDecision
from app.services import lifecycle_service, learning_service
from app.services.auth_service import ROLE_NGO_ADMIN, ROLE_NGO_MANAGER, ROLE_VOLUNTEER
from app.services.prediction_service import get_velocity_factor
from app.config import get_settings
from app.events.event_dispatcher import (
    publish,
    EVENT_ALLOCATION_COMPLETE,
    EVENT_TASK_ASSIGNED,
    EVENT_TASK_ACCEPTED,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/allocate", tags=["Allocation"])
settings = get_settings()


class AssignmentOverrideRequest(BaseModel):
    """Manual override payload for adaptive learning updates."""

    task_id: str = Field(..., min_length=1)
    overridden_volunteer_id: str = Field(..., min_length=1)
    original_volunteer_id: str | None = None
    reason: str | None = Field(default=None, max_length=500)


def _task_to_score_input(task: Task) -> TaskScoreInput:
    """Convert ORM Task to pure scoring input."""
    return TaskScoreInput(
        id=task.id,
        required_skills=task.required_skills or [],
        urgency=task.urgency,
        complexity=task.complexity,
        latitude=task.latitude,
        longitude=task.longitude,
        waiting_time_minutes=task.waiting_time_minutes,
        team_size=task.team_size,
        region=task.region,
    )


def _volunteer_to_score_input(vol: Volunteer, lifecycle_metrics: dict | None = None) -> VolunteerScoreInput:
    """Convert ORM Volunteer to pure scoring input."""
    metrics = lifecycle_metrics or {}
    return VolunteerScoreInput(
        id=vol.id,
        name=vol.name,
        skills=vol.skills or [],
        latitude=vol.latitude,
        longitude=vol.longitude,
        availability=vol.availability,
        reliability=vol.reliability,
        burnout_score=vol.burnout_score,
        engagement_score=float(metrics.get("engagement_score", 0.5)),
        burnout_risk=float(metrics.get("burnout_risk", 0.0)),
        total_assignments=vol.total_assignments,
        active_assignments=vol.active_assignments,
    )


async def _persist_decision(
    db: AsyncSession,
    decision: AllocationDecision,
    task: Task,
    volunteer: Volunteer,
    weight_snapshot: dict | None = None,
) -> Assignment:
    """Persist an allocation decision to DB with full audit reproducibility."""
    # Create assignment
    assignment = Assignment(
        task_id=decision.task_id,
        volunteer_id=decision.volunteer_id,
        vas_score=decision.vas_score,
        status="assigned",
    )
    db.add(assignment)

    # Create audit log with weight snapshot + confidence
    alternatives_data = [
        {
            "volunteer_id": alt.volunteer.id,
            "volunteer_name": alt.volunteer.name,
            "vas_score": round(alt.breakdown.final_vas_score, 4),
            "rejection_reason": "Lower VAS score",
        }
        for alt in decision.alternatives[:3]
    ]

    audit = AuditLog(
        task_id=decision.task_id,
        chosen_volunteer_id=decision.volunteer_id,
        reason=f"Highest VAS score ({decision.vas_score:.4f})",
        vas_score=decision.vas_score,
        factors={
            "skill_match": decision.breakdown.skill_match,
            "proximity": decision.breakdown.proximity,
            "reliability": decision.breakdown.reliability,
            "availability": decision.breakdown.availability,
            "burnout_adjustment": decision.breakdown.burnout_adjustment,
            "volunteer_fit": decision.breakdown.volunteer_fit_adjusted,
            "final_vas_score": decision.breakdown.final_vas_score,
        },
        alternatives=alternatives_data,
        allocation_mode=decision.degradation_mode,
        weight_snapshot=weight_snapshot or {},
        cycle_id=decision.cycle_id or None,
        confidence_score=decision.confidence_score,
    )
    db.add(audit)

    # Update task status
    task.status = "allocated"

    # Update volunteer via lifecycle service
    await lifecycle_service.update_burnout_after_assignment(
        db, volunteer, task.complexity
    )
    await lifecycle_service.record_assignment_metrics(
        db=db,
        volunteer_id=volunteer.id,
    )
    volunteer.status = "deployed"

    await publish(
        EVENT_TASK_ASSIGNED,
        {
            "task_id": decision.task_id,
            "volunteer_id": decision.volunteer_id,
            "vas_score": decision.vas_score,
            "ngo_id": task.ngo_id,
        },
    )

    return assignment


@router.post("/run", response_model=AllocationResult)
async def run_allocation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_NGO_ADMIN, ROLE_NGO_MANAGER)),
):
    """
    Execute a full allocation cycle.

    1. Fetches all pending tasks
    2. Fetches all available volunteers
    3. Runs the core allocation engine (scoring + matching)
    4. Persists assignments + audit logs
    5. Updates volunteer/task statuses
    6. Fires allocation_complete event
    """
    start_time = time.monotonic()

    # Fetch from DB
    pending_tasks_result = await db.execute(
        select(Task).where(Task.status == "pending", Task.ngo_id == current_user.ngo_id)
    )
    pending_tasks = list(pending_tasks_result.scalars().all())

    available_vols = await lifecycle_service.get_available_volunteers(db, ngo_id=current_user.ngo_id)

    if not pending_tasks:
        return AllocationResult(
            assignments_created=0,
            assignments_reassigned=0,
            tasks_unmatched=0,
            cycle_duration_ms=0,
            details=[],
        )

    # Build pure inputs
    task_inputs = [_task_to_score_input(t) for t in pending_tasks]
    metrics_map = await lifecycle_service.get_metrics_map(
        db, [v.id for v in available_vols]
    )
    vol_inputs = [
        _volunteer_to_score_input(
            v,
            {
                "engagement_score": metrics_map.get(v.id).engagement_score if metrics_map.get(v.id) else 0.5,
                "burnout_risk": metrics_map.get(v.id).burnout_risk if metrics_map.get(v.id) else 0.0,
            },
        )
        for v in available_vols
    ]

    # Build weights from config
    base_weights = ScoringWeights(
        k1=settings.VAS_K1,
        k2=settings.VAS_K2,
        k3=settings.VAS_K3,
        k4=settings.VAS_K4,
        fit_skill=settings.FIT_SKILL_WEIGHT,
        fit_proximity=settings.FIT_PROXIMITY_WEIGHT,
        fit_reliability=settings.FIT_RELIABILITY_WEIGHT,
        fit_availability=settings.FIT_AVAILABILITY_WEIGHT,
        max_radius_km=settings.MAX_SEARCH_RADIUS_KM,
    )
    weights = await learning_service.get_effective_scoring_weights(db, base_weights)

    # Get velocity factors per region
    velocity_factors = {}
    for t in pending_tasks:
        if t.region:
            velocity_factors[t.region] = get_velocity_factor(t.region)

    # Build lookup maps for persistence
    task_map = {t.id: t for t in pending_tasks}
    vol_map = {v.id: v for v in available_vols}

    created_assignments: list[Assignment] = []

    async def _persist_callback(decision: AllocationDecision) -> None:
        task_orm = task_map.get(decision.task_id)
        vol_orm = vol_map.get(decision.volunteer_id)
        if task_orm is None or vol_orm is None:
            return
        assignment = await _persist_decision(db, decision, task_orm, vol_orm)
        created_assignments.append(assignment)

    # === RUN CORE ALLOCATION ENGINE ===
    cycle_result = await allocation_cycle(
        tasks=task_inputs,
        volunteers=vol_inputs,
        weights=weights,
        velocity_factors=velocity_factors,
        lock_retry_attempts=settings.LOCK_RETRY_ATTEMPTS,
        persist_decision_callback=_persist_callback,
    )

    # Mark unmatched tasks
    for task_id in cycle_result.unmatched_task_ids:
        # Log audit for unmatched
        audit = AuditLog(
            task_id=task_id,
            chosen_volunteer_id=None,
            reason="No suitable volunteer found",
            factors={},
            alternatives=[],
            allocation_mode="standard",
        )
        db.add(audit)

    await db.commit()

    elapsed_ms = (time.monotonic() - start_time) * 1000

    # Fire completion event
    await publish(EVENT_ALLOCATION_COMPLETE, {
        "assigned": len(created_assignments),
        "unmatched": len(cycle_result.unmatched_task_ids),
        "escalated": len(cycle_result.escalated_task_ids),
        "duration_ms": round(elapsed_ms, 2),
        "ngo_id": current_user.ngo_id,
    })

    logger.info(
        f"Allocation cycle complete in {elapsed_ms:.1f}ms: "
        f"{len(created_assignments)} assigned, "
        f"{len(cycle_result.unmatched_task_ids)} unmatched"
    )

    return AllocationResult(
        assignments_created=len(created_assignments),
        assignments_reassigned=0,
        tasks_unmatched=len(cycle_result.unmatched_task_ids),
        cycle_duration_ms=round(elapsed_ms, 2),
        details=[
            AssignmentResponse.model_validate(a) for a in created_assignments
        ],
    )


@router.get("/assignments")
async def get_assignments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all assignments."""
    query = select(Assignment)
    if current_user.role == ROLE_VOLUNTEER:
        query = query.join(Volunteer, Volunteer.id == Assignment.volunteer_id).where(Volunteer.user_id == current_user.id)
    elif current_user.ngo_id:
        query = query.join(Task, Task.id == Assignment.task_id).where(Task.ngo_id == current_user.ngo_id)
    result = await db.execute(query.order_by(Assignment.assigned_at.desc()))
    assignments = result.scalars().all()
    return [AssignmentResponse.model_validate(a) for a in assignments]


@router.get("/assignments/{task_id}/explain", response_model=ExplainabilityResponse)
async def explain_assignment(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Explain the latest assignment decision for a task."""
    task_result = await db.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if current_user.role != ROLE_VOLUNTEER and current_user.ngo_id and task.ngo_id != current_user.ngo_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if current_user.role == ROLE_VOLUNTEER:
        assignment_check = await db.execute(
            select(Assignment.id)
            .join(Volunteer, Volunteer.id == Assignment.volunteer_id)
            .where(Assignment.task_id == task_id, Volunteer.user_id == current_user.id)
            .limit(1)
        )
        if assignment_check.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.task_id == task_id)
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    audit = result.scalar_one_or_none()
    if audit is None:
        raise HTTPException(status_code=404, detail=f"No assignment explainability record for task {task_id}")

    volunteer_name = None
    if audit.chosen_volunteer_id:
        vol_result = await db.execute(
            select(Volunteer.name).where(Volunteer.id == audit.chosen_volunteer_id)
        )
        volunteer_name = vol_result.scalar_one_or_none()

    factors = None
    if audit.factors and audit.chosen_volunteer_id:
        f = audit.factors
        factors = ExplainabilityFactors(
            skill_match=f.get("skill_match", 0.0),
            proximity=f.get("proximity", 0.0),
            reliability=f.get("reliability", 0.0),
            availability=f.get("availability", 0.0),
            burnout_adjustment=f.get("burnout_adjustment", 1.0),
            volunteer_fit=f.get("volunteer_fit", 0.0),
            final_vas_score=f.get("final_vas_score", 0.0),
        )

    alternatives = [
        AlternativeCandidate(
            volunteer_id=alt.get("volunteer_id", ""),
            volunteer_name=alt.get("volunteer_name", "Unknown"),
            vas_score=alt.get("vas_score", 0.0),
            rejection_reason=alt.get("rejection_reason", "Lower VAS score"),
        )
        for alt in (audit.alternatives or [])
    ]

    return ExplainabilityResponse(
        task_id=audit.task_id,
        chosen_volunteer_id=audit.chosen_volunteer_id,
        chosen_volunteer_name=volunteer_name,
        reason=audit.reason,
        factors=factors,
        alternatives=alternatives,
        allocation_mode=audit.allocation_mode,
        override_flag=audit.override_flag,
        confidence=audit.confidence_score if audit.confidence_score is not None else 0.0,
        created_at=audit.created_at,
    )


@router.post("/assignments/override", status_code=status.HTTP_200_OK)
@router.post("/override", status_code=status.HTTP_200_OK)
async def override_assignment(
    data: AssignmentOverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_NGO_ADMIN, ROLE_NGO_MANAGER)),
):
    """
    Override an existing assignment and feed decision back into adaptive learning.

    Captures:
    - original volunteer
    - overridden volunteer
    - feature vectors for both
    - feature delta and score delta for online weight updates
    """
    task_result = await db.execute(select(Task).where(Task.id == data.task_id))
    task = task_result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {data.task_id} not found")
    if current_user.ngo_id and task.ngo_id != current_user.ngo_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    assignment_result = await db.execute(
        select(Assignment)
        .where(Assignment.task_id == data.task_id)
        .order_by(Assignment.assigned_at.desc())
        .limit(1)
    )
    assignment = assignment_result.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(
            status_code=404,
            detail=f"No existing assignment found for task {data.task_id}",
        )

    original_volunteer_id = data.original_volunteer_id or assignment.volunteer_id
    if original_volunteer_id == data.overridden_volunteer_id:
        raise HTTPException(
            status_code=400,
            detail="Override volunteer must differ from original volunteer",
        )

    volunteers_result = await db.execute(
        select(Volunteer).where(
            Volunteer.id.in_([original_volunteer_id, data.overridden_volunteer_id])
        )
    )
    volunteers = list(volunteers_result.scalars().all())
    volunteer_map = {v.id: v for v in volunteers}

    original_volunteer = volunteer_map.get(original_volunteer_id)
    overridden_volunteer = volunteer_map.get(data.overridden_volunteer_id)

    if original_volunteer is None:
        raise HTTPException(status_code=404, detail=f"Volunteer {original_volunteer_id} not found")
    if overridden_volunteer is None:
        raise HTTPException(
            status_code=404,
            detail=f"Volunteer {data.overridden_volunteer_id} not found",
        )

    base_weights = ScoringWeights(
        k1=settings.VAS_K1,
        k2=settings.VAS_K2,
        k3=settings.VAS_K3,
        k4=settings.VAS_K4,
        fit_skill=settings.FIT_SKILL_WEIGHT,
        fit_proximity=settings.FIT_PROXIMITY_WEIGHT,
        fit_reliability=settings.FIT_RELIABILITY_WEIGHT,
        fit_availability=settings.FIT_AVAILABILITY_WEIGHT,
        max_radius_km=settings.MAX_SEARCH_RADIUS_KM,
    )
    effective_weights = await learning_service.get_effective_scoring_weights(db, base_weights)

    task_input = _task_to_score_input(task)
    override_metrics_map = await lifecycle_service.get_metrics_map(
        db, [original_volunteer.id, overridden_volunteer.id]
    )
    original_metrics = override_metrics_map.get(original_volunteer.id)
    overridden_metrics = override_metrics_map.get(overridden_volunteer.id)
    original_input = _volunteer_to_score_input(
        original_volunteer,
        {
            "engagement_score": original_metrics.engagement_score if original_metrics else 0.5,
            "burnout_risk": original_metrics.burnout_risk if original_metrics else 0.0,
        },
    )
    overridden_input = _volunteer_to_score_input(
        overridden_volunteer,
        {
            "engagement_score": overridden_metrics.engagement_score if overridden_metrics else 0.5,
            "burnout_risk": overridden_metrics.burnout_risk if overridden_metrics else 0.0,
        },
    )
    velocity = get_velocity_factor(task.region) if task.region else 0.0

    original_breakdown = compute_vas(task_input, original_input, effective_weights, velocity)
    new_breakdown = compute_vas(task_input, overridden_input, effective_weights, velocity)

    original_vector = extract_feature_vector(task_input, original_input, effective_weights)
    overridden_vector = extract_feature_vector(task_input, overridden_input, effective_weights)

    # Update assignment target volunteer.
    assignment.volunteer_id = overridden_volunteer.id
    assignment.vas_score = new_breakdown.final_vas_score
    assignment.status = "reassigned"

    # Revert load for original and apply load to overridden volunteer.
    original_volunteer.active_assignments = max(0, original_volunteer.active_assignments - 1)
    original_volunteer.total_assignments = max(0, original_volunteer.total_assignments - 1)
    if original_volunteer.active_assignments == 0 and original_volunteer.status == "deployed":
        original_volunteer.status = "available"

    await lifecycle_service.update_burnout_after_assignment(
        db,
        overridden_volunteer,
        task.complexity,
    )
    await lifecycle_service.record_response_metrics(
        db=db,
        volunteer_id=original_volunteer.id,
        accepted=False,
    )
    await lifecycle_service.record_assignment_metrics(
        db=db,
        volunteer_id=overridden_volunteer.id,
        accepted=True,
    )
    await publish(
        EVENT_TASK_ACCEPTED,
        {
            "task_id": task.id,
            "volunteer_id": overridden_volunteer.id,
            "source": "override",
            "ngo_id": task.ngo_id,
        },
    )
    overridden_volunteer.status = "deployed"

    audit = AuditLog(
        task_id=task.id,
        chosen_volunteer_id=overridden_volunteer.id,
        original_volunteer_id=original_volunteer.id,
        overridden_volunteer_id=overridden_volunteer.id,
        reason=data.reason or "Manual override applied",
        vas_score=new_breakdown.final_vas_score,
        factors={
            "skill_match": new_breakdown.skill_match,
            "proximity": new_breakdown.proximity,
            "reliability": new_breakdown.reliability,
            "availability": new_breakdown.availability,
            "burnout_adjustment": new_breakdown.burnout_adjustment,
            "volunteer_fit": new_breakdown.volunteer_fit_adjusted,
            "final_vas_score": new_breakdown.final_vas_score,
        },
        alternatives=[],
        override_flag=True,
        allocation_mode="override",
        original_feature_vector=original_vector,
        overridden_feature_vector=overridden_vector,
    )
    db.add(audit)

    updated_weights = await learning_service.record_override_feedback(
        db=db,
        task_input=task_input,
        original_volunteer_input=original_input,
        overridden_volunteer_input=overridden_input,
        original_score=original_breakdown.final_vas_score,
        new_score=new_breakdown.final_vas_score,
        base_weights=base_weights,
        task_category=task.category if hasattr(task, 'category') else None,
        task_region=task.region,
    )

    await db.commit()

    return {
        "task_id": task.id,
        "assignment_id": assignment.id,
        "original_volunteer_id": original_volunteer.id,
        "overridden_volunteer_id": overridden_volunteer.id,
        "original_score": original_breakdown.final_vas_score,
        "new_score": new_breakdown.final_vas_score,
        "updated_fit_weights": updated_weights,
    }
