"""
Fairness and system analytics aggregation service.
"""

from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.assignment import Assignment
from app.models.task import Task
from app.models.volunteer import Volunteer
from app.models.audit import AuditLog
from app.models.volunteer_metrics import VolunteerMetrics
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

_ANALYTICS_CACHE_KEY = "vasae:analytics:overview:v1"
_ANALYTICS_CACHE_TTL_SECONDS = 30


async def _redis_get() -> object | None:
    try:
        import redis.asyncio as redis

        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        return client
    except Exception:
        return None


def _gini(values: list[int]) -> float:
    if not values:
        return 0.0
    vals = sorted(max(v, 0) for v in values)
    n = len(vals)
    total = sum(vals)
    if total <= 0:
        return 0.0
    cum = 0
    for i, val in enumerate(vals, 1):
        cum += i * val
    g = ((2 * cum) / (n * total)) - ((n + 1) / n)
    return round(max(0.0, min(1.0, g)), 4)


async def get_analytics_overview(db: AsyncSession, ngo_id: str | None = None) -> dict:
    redis_client = await _redis_get()
    if redis_client is not None:
        try:
            cached = await redis_client.get(_ANALYTICS_CACHE_KEY)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    total_tasks_query = select(func.count(Task.id))
    if ngo_id:
        total_tasks_query = total_tasks_query.where(Task.ngo_id == ngo_id)
    total_tasks_result = await db.execute(total_tasks_query)
    total_tasks = int(total_tasks_result.scalar() or 0)

    assigned_query = select(func.count(Assignment.id))
    if ngo_id:
        assigned_query = assigned_query.join(Task, Task.id == Assignment.task_id).where(Task.ngo_id == ngo_id)
    assigned_result = await db.execute(assigned_query)
    assigned_total = int(assigned_result.scalar() or 0)

    active_tasks_query = select(func.count(Task.id)).where(Task.status.in_(["pending", "processing", "allocated"]))
    if ngo_id:
        active_tasks_query = active_tasks_query.where(Task.ngo_id == ngo_id)
    active_tasks_result = await db.execute(active_tasks_query)
    total_active_tasks = int(active_tasks_result.scalar() or 0)

    completed_tasks_query = select(func.count(Task.id)).where(Task.status == "completed")
    if ngo_id:
        completed_tasks_query = completed_tasks_query.where(Task.ngo_id == ngo_id)
    completed_tasks_result = await db.execute(completed_tasks_query)
    completed_tasks = int(completed_tasks_result.scalar() or 0)

    volunteers_available_query = select(func.count(Volunteer.id)).where(
        Volunteer.is_active == True,  # noqa: E712
        Volunteer.status == "available",
    )
    if ngo_id:
        volunteers_available_query = volunteers_available_query.where(Volunteer.ngo_id == ngo_id)
    volunteers_available_result = await db.execute(volunteers_available_query)
    volunteers_available = int(volunteers_available_result.scalar() or 0)

    assignments_in_progress_query = select(func.count(Assignment.id)).where(Assignment.status.in_(["assigned", "active"]))
    if ngo_id:
        assignments_in_progress_query = assignments_in_progress_query.join(Task, Task.id == Assignment.task_id).where(Task.ngo_id == ngo_id)
    assignments_in_progress_result = await db.execute(assignments_in_progress_query)
    assignments_in_progress = int(assignments_in_progress_result.scalar() or 0)

    completed_or_allocated_query = select(func.count(Task.id)).where(Task.status.in_(["allocated", "completed"]))
    if ngo_id:
        completed_or_allocated_query = completed_or_allocated_query.where(Task.ngo_id == ngo_id)
    completed_or_allocated_result = await db.execute(completed_or_allocated_query)
    successful_tasks = int(completed_or_allocated_result.scalar() or 0)
    assignment_success_rate = round((successful_tasks / total_tasks), 4) if total_tasks > 0 else 0.0

    workload_query = select(Assignment.volunteer_id, func.count(Assignment.id)).group_by(Assignment.volunteer_id)
    if ngo_id:
        workload_query = workload_query.join(Task, Task.id == Assignment.task_id).where(Task.ngo_id == ngo_id)
    workload_result = await db.execute(workload_query)
    workload_rows = workload_result.all()
    tasks_per_volunteer = {vol_id: int(cnt) for vol_id, cnt in workload_rows}
    gini = _gini(list(tasks_per_volunteer.values()))

    burnout_query = select(Volunteer.burnout_score, func.count(Volunteer.id)).group_by(Volunteer.burnout_score)
    if ngo_id:
        burnout_query = burnout_query.where(Volunteer.ngo_id == ngo_id)
    burnout_result = await db.execute(burnout_query)
    burnout_distribution = [
        {"burnout_score": float(score), "count": int(count)}
        for score, count in burnout_result.all()
    ]

    try:
        avg_response_query = select(func.avg(VolunteerMetrics.avg_response_time)).join(Volunteer, Volunteer.id == VolunteerMetrics.volunteer_id)
        if ngo_id:
            avg_response_query = avg_response_query.where(Volunteer.ngo_id == ngo_id)
        avg_response_result = await db.execute(avg_response_query)
        avg_response_time = float(avg_response_result.scalar() or 0.0)
    except Exception:
        await db.rollback()
        avg_response_time = 0.0

    queue_latency_query = select(Assignment.assigned_at, Task.created_at).join(Task, Task.id == Assignment.task_id)
    if ngo_id:
        queue_latency_query = queue_latency_query.where(Task.ngo_id == ngo_id)
    queue_latency_rows = await db.execute(queue_latency_query)
    latencies: list[float] = []
    for assigned_at, created_at in queue_latency_rows.all():
        if assigned_at is None or created_at is None:
            continue
        latencies.append(max((assigned_at - created_at).total_seconds(), 0.0))
    queue_latency_seconds = (sum(latencies) / len(latencies)) if latencies else 0.0

    recent_query = select(AuditLog).join(Task, Task.id == AuditLog.task_id)
    if ngo_id:
        recent_query = recent_query.where(Task.ngo_id == ngo_id)
    recent_result = await db.execute(recent_query.order_by(AuditLog.created_at.desc()).limit(10))
    recent_activity = [
        {
            "id": log.id,
            "type": "assignment_done" if log.chosen_volunteer_id else "task_event",
            "task_id": log.task_id,
            "message": log.reason,
            "created_at": log.created_at.isoformat(),
        }
        for log in recent_result.scalars().all()
    ]

    avg_burnout_query = select(func.avg(Volunteer.burnout_score))
    if ngo_id:
        avg_burnout_query = avg_burnout_query.where(Volunteer.ngo_id == ngo_id)
    avg_burnout_result = await db.execute(avg_burnout_query)
    avg_burnout = float(avg_burnout_result.scalar() or 0.0)
    try:
        avg_engagement_query = select(func.avg(VolunteerMetrics.engagement_score)).join(Volunteer, Volunteer.id == VolunteerMetrics.volunteer_id)
        if ngo_id:
            avg_engagement_query = avg_engagement_query.where(Volunteer.ngo_id == ngo_id)
        avg_engagement_result = await db.execute(avg_engagement_query)
        avg_engagement = float(avg_engagement_result.scalar() or 0.0)
    except Exception:
        await db.rollback()
        avg_engagement = 0.0

    overview = {
        "total_active_tasks": total_active_tasks,
        "volunteers_available": volunteers_available,
        "assignments_in_progress": assignments_in_progress,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "total_assignments": assigned_total,
        "assignment_success_rate": assignment_success_rate,
        "tasks_per_volunteer": tasks_per_volunteer,
        "gini_coefficient": gini,
        "burnout_distribution": burnout_distribution,
        "avg_response_time": round(avg_response_time, 2),
        "queue_latency": round(queue_latency_seconds, 2),
        "recent_activity": recent_activity,
        "volunteer_health": {
            "avg_burnout": round(avg_burnout, 4),
            "engagement_score": round(avg_engagement, 4),
        },
    }

    if redis_client is not None:
        try:
            await redis_client.set(_ANALYTICS_CACHE_KEY, json.dumps(overview), ex=_ANALYTICS_CACHE_TTL_SECONDS)
        except Exception:
            logger.warning("Failed to cache analytics overview")

    return overview
