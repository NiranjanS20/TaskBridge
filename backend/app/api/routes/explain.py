"""
VASAE Explainability API Routes
-------------------------------
Returns human-readable explanations for allocation decisions.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.audit import AuditLog
from app.models.assignment import Assignment
from app.models.task import Task
from app.models.volunteer import Volunteer
from app.models.user import User
from app.schemas.volunteer_schema import (
    ExplainabilityResponse,
    ExplainabilityFactors,
    AlternativeCandidate,
)
from app.services.auth_service import ROLE_VOLUNTEER
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/explain", tags=["Explainability"])


@router.get("/{task_id}", response_model=ExplainabilityResponse)
async def explain_allocation(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the explainability report for a task's allocation decision.

    Returns:
    - Why this volunteer was chosen
    - Exact factor scores
    - Alternative candidates considered
    """
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

    if not audit:
        raise HTTPException(
            status_code=404,
            detail=f"No allocation record found for task {task_id}",
        )

    # Resolve volunteer name
    volunteer_name = None
    if audit.chosen_volunteer_id:
        vol_result = await db.execute(
            select(Volunteer.name).where(Volunteer.id == audit.chosen_volunteer_id)
        )
        volunteer_name = vol_result.scalar_one_or_none()

    # Build factors
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

    # Build alternatives
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
