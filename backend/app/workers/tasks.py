"""
VASAE Background Tasks
----------------------
Celery tasks for heavy computation.
Each task has a synchronous fallback for development.

Tier-1 Hardening Extensions:
- Global allocation cycle lock (prevents overlapping cycles)
- Cycle-level metrics (latency, throughput, queue depth)
- Structured logging for observability
"""

from __future__ import annotations

import asyncio
import time
import uuid

from sqlalchemy import select

from app.config import get_settings
from app.core.allocation import AllocationDecision, allocation_cycle
from app.core.scoring import ScoringWeights
from app.db.session import async_session_factory
from app.models.audit import AuditLog
from app.models.task import Task
from app.services import learning_service
from app.services.lifecycle_service import get_available_volunteers, get_metrics_map
from app.services.prediction_service import get_velocity_factor
from app.utils.locks import VolunteerLockManager
from app.utils.logger import get_logger
from app.workers.celery_worker import CELERY_AVAILABLE, celery_app

logger = get_logger(__name__)
settings = get_settings()

# Global cycle lock key — prevents overlapping allocation cycles
_CYCLE_LOCK_KEY = "__allocation_cycle_global__"


async def run_allocation_cycle_async(
    mode: str = "batch",
    trigger_event: str | None = None,
    payload: dict | None = None,
    focus_task_id: str | None = None,
) -> dict:
    """
    Run allocation cycle as a background orchestration unit.

    Hardened with:
    - Global cycle lock to prevent overlapping runs
    - Cycle-level metrics (latency, throughput)
    - Weight snapshot capture in audit logs

    Modes:
    - batch: process all pending tasks
    - streaming: prioritize event-targeted task if provided
    """
    from app.api.routes.allocation import (
        _task_to_score_input,
        _volunteer_to_score_input,
        _persist_decision,
    )

    if payload is None:
        payload = {}

    ngo_id = payload.get("ngo_id")
    cycle_id = str(uuid.uuid4())
    start_time = time.monotonic()

    # --- Global cycle lock ---
    cycle_lock = VolunteerLockManager(
        lock_ttl_seconds=settings.ALLOCATION_CYCLE_LOCK_TTL,
    )
    lock_token = await cycle_lock.acquire_lock(_CYCLE_LOCK_KEY)
    if lock_token is None:
        logger.warning(
            "Allocation cycle skipped — another cycle is in progress "
            "(event=%s mode=%s)", trigger_event, mode,
        )
        return {
            "skipped": True,
            "reason": "concurrent_cycle",
            "trigger_event": trigger_event,
            "mode": mode,
        }

    try:
        async with async_session_factory() as db:
            try:
                if mode == "streaming" and focus_task_id:
                    streaming_query = select(Task).where(Task.id == focus_task_id, Task.status == "pending")
                    if ngo_id:
                        streaming_query = streaming_query.where(Task.ngo_id == ngo_id)
                    result = await db.execute(streaming_query)
                    tasks = list(result.scalars().all())
                    if not tasks:
                        # Fallback to pending queue when the target task is already handled.
                        fallback_query = select(Task).where(Task.status == "pending")
                        if ngo_id:
                            fallback_query = fallback_query.where(Task.ngo_id == ngo_id)
                        fallback = await db.execute(fallback_query)
                        tasks = list(fallback.scalars().all())
                else:
                    batch_query = select(Task).where(Task.status == "pending")
                    if ngo_id:
                        batch_query = batch_query.where(Task.ngo_id == ngo_id)
                    result = await db.execute(batch_query)
                    tasks = list(result.scalars().all())

                volunteers = await get_available_volunteers(db, ngo_id=ngo_id)

                if not tasks or not volunteers:
                    logger.info("Background allocation: nothing to process")
                    return {
                        "assigned": 0,
                        "unmatched": len(tasks),
                        "escalated": 0,
                        "trigger_event": trigger_event,
                        "mode": mode,
                        "cycle_id": cycle_id,
                    }

                # Build inputs
                task_inputs = [_task_to_score_input(t) for t in tasks]
                metrics_map = await get_metrics_map(db, [v.id for v in volunteers])
                vol_inputs = [
                    _volunteer_to_score_input(
                        v,
                        {
                            "engagement_score": metrics_map.get(v.id).engagement_score if metrics_map.get(v.id) else 0.5,
                            "burnout_risk": metrics_map.get(v.id).burnout_risk if metrics_map.get(v.id) else 0.0,
                        },
                    )
                    for v in volunteers
                ]

                base_weights = ScoringWeights(
                    k1=settings.VAS_K1, k2=settings.VAS_K2,
                    k3=settings.VAS_K3, k4=settings.VAS_K4,
                    fit_skill=settings.FIT_SKILL_WEIGHT,
                    fit_proximity=settings.FIT_PROXIMITY_WEIGHT,
                    fit_reliability=settings.FIT_RELIABILITY_WEIGHT,
                    fit_availability=settings.FIT_AVAILABILITY_WEIGHT,
                    max_radius_km=settings.MAX_SEARCH_RADIUS_KM,
                )
                weights = await learning_service.get_effective_scoring_weights(db, base_weights)

                # Capture weight snapshot for audit reproducibility
                weight_snapshot = {
                    "k1": weights.k1, "k2": weights.k2,
                    "k3": weights.k3, "k4": weights.k4,
                    "fit_skill": weights.fit_skill,
                    "fit_proximity": weights.fit_proximity,
                    "fit_reliability": weights.fit_reliability,
                    "fit_availability": weights.fit_availability,
                }

                velocity_factors = {
                    t.region: get_velocity_factor(t.region)
                    for t in tasks if t.region
                }

                task_map = {t.id: t for t in tasks}
                vol_map = {v.id: v for v in volunteers}
                created_assignments = []

                async def _persist_callback(decision: AllocationDecision) -> None:
                    task_orm = task_map.get(decision.task_id)
                    vol_orm = vol_map.get(decision.volunteer_id)
                    if task_orm is None or vol_orm is None:
                        return
                    assignment = await _persist_decision(
                        db, decision, task_orm, vol_orm,
                        weight_snapshot=weight_snapshot,
                    )
                    created_assignments.append(assignment)

                # Run core realtime loop
                cycle_result = await allocation_cycle(
                    task_inputs,
                    vol_inputs,
                    weights,
                    velocity_factors,
                    lock_retry_attempts=settings.LOCK_RETRY_ATTEMPTS,
                    persist_decision_callback=_persist_callback,
                )

                # Log unmatched outcomes for explainability continuity.
                for task_id in cycle_result.unmatched_task_ids:
                    db.add(
                        AuditLog(
                            task_id=task_id,
                            chosen_volunteer_id=None,
                            reason="No suitable volunteer found",
                            factors={},
                            alternatives=[],
                            allocation_mode="standard",
                            weight_snapshot=weight_snapshot,
                            cycle_id=cycle_result.cycle_id,
                        )
                    )

                await db.commit()

                elapsed_ms = (time.monotonic() - start_time) * 1000
                throughput = len(created_assignments) / max(elapsed_ms / 1000, 0.001)

                logger.info(
                    "Background allocation complete: cycle=%s assigned=%s "
                    "unmatched=%s escalated=%s mode=%s event=%s "
                    "latency=%.1fms throughput=%.1f/s",
                    cycle_id[:8],
                    len(created_assignments),
                    len(cycle_result.unmatched_task_ids),
                    len(cycle_result.escalated_task_ids),
                    mode,
                    trigger_event,
                    elapsed_ms,
                    throughput,
                )

                return {
                    "assigned": len(created_assignments),
                    "unmatched": len(cycle_result.unmatched_task_ids),
                    "escalated": len(cycle_result.escalated_task_ids),
                    "trigger_event": trigger_event,
                    "mode": mode,
                    "cycle_id": cycle_id,
                    "latency_ms": round(elapsed_ms, 2),
                    "throughput_per_sec": round(throughput, 2),
                }

            except Exception as e:
                await db.rollback()
                logger.error(f"Background allocation failed: {e}")
                raise

    finally:
        await cycle_lock.release_lock(_CYCLE_LOCK_KEY, lock_token)


async def trigger_realtime_allocation(
    event_type: str,
    payload: dict | None = None,
    mode: str = "streaming",
) -> None:
    """Dispatch allocation execution to Celery worker when available."""
    if payload is None:
        payload = {}

    focus_task_id = payload.get("task_id")

    if CELERY_AVAILABLE and celery_app is not None:
        celery_execute_allocation.delay(
            mode=mode,
            trigger_event=event_type,
            payload=payload,
            focus_task_id=focus_task_id,
        )
        logger.info(
            "Queued realtime allocation job via Celery: event=%s mode=%s task=%s",
            event_type,
            mode,
            (focus_task_id or "-")[:8],
        )
        return

    logger.info("Celery unavailable, running allocation synchronously: event=%s", event_type)
    await run_allocation_cycle_async(
        mode=mode,
        trigger_event=event_type,
        payload=payload,
        focus_task_id=focus_task_id,
    )


if CELERY_AVAILABLE and celery_app is not None:

    @celery_app.task(name="vasae.run_allocation_cycle")
    def celery_execute_allocation(
        mode: str = "batch",
        trigger_event: str | None = None,
        payload: dict | None = None,
        focus_task_id: str | None = None,
    ) -> dict:
        return asyncio.run(
            run_allocation_cycle_async(
                mode=mode,
                trigger_event=trigger_event,
                payload=payload,
                focus_task_id=focus_task_id,
            )
        )
