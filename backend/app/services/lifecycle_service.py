"""
VASAE Lifecycle Service
-----------------------
Manages volunteer lifecycle:
- Burnout tracking and auto-rest
- Workload balancing
- Status transitions
"""

from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.volunteer_metrics import VolunteerMetrics
from app.models.volunteer import Volunteer
from app.schemas.volunteer_schema import VolunteerCreateRequest, VolunteerUpdateRequest
from app.core.fairness import should_rest, compute_burnout_increment, gini_coefficient
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def create_volunteer(
    db: AsyncSession,
    data: VolunteerCreateRequest,
    ngo_id: str | None = None,
    user_id: str | None = None,
) -> Volunteer:
    """Register a new volunteer."""
    volunteer = Volunteer(
        ngo_id=ngo_id,
        user_id=user_id,
        name=data.name,
        email=data.email,
        skills=data.skills,
        latitude=data.latitude,
        longitude=data.longitude,
        availability=data.availability,
        reliability=data.reliability,
    )
    db.add(volunteer)
    await db.flush()

    logger.info(f"Volunteer registered: {volunteer.id[:8]} - '{volunteer.name}' skills={volunteer.skills}")
    return volunteer


async def get_volunteer_by_id(db: AsyncSession, volunteer_id: str) -> Volunteer | None:
    """Fetch a single volunteer."""
    result = await db.execute(select(Volunteer).where(Volunteer.id == volunteer_id))
    return result.scalar_one_or_none()


async def get_available_volunteers(db: AsyncSession, ngo_id: str | None = None) -> list[Volunteer]:
    """Fetch all deployable volunteers."""
    query = select(Volunteer).where(
        Volunteer.is_active == True,  # noqa: E712
        Volunteer.status == "available",
        Volunteer.availability > 0.0,
        Volunteer.burnout_score < settings.BURNOUT_THRESHOLD,
    )
    if ngo_id:
        query = query.where(Volunteer.ngo_id == ngo_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_all_volunteers(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    ngo_id: str | None = None,
) -> tuple[list[Volunteer], int]:
    """Paginated volunteer list."""
    from sqlalchemy import func
    count_query = select(func.count(Volunteer.id))
    if ngo_id:
        count_query = count_query.where(Volunteer.ngo_id == ngo_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    query = select(Volunteer)
    if ngo_id:
        query = query.where(Volunteer.ngo_id == ngo_id)
    result = await db.execute(
        query.order_by(Volunteer.created_at.desc()).offset(offset).limit(page_size)
    )
    volunteers = list(result.scalars().all())
    return volunteers, total


async def update_volunteer(
    db: AsyncSession,
    volunteer_id: str,
    data: VolunteerUpdateRequest,
    ngo_id: str | None = None,
) -> Volunteer | None:
    """Partially update a volunteer."""
    volunteer = await get_volunteer_by_id(db, volunteer_id)
    if volunteer and ngo_id and volunteer.ngo_id != ngo_id:
        return None
    if not volunteer:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(volunteer, field, value)

    await db.flush()
    logger.info(f"Volunteer {volunteer_id[:8]} updated: {list(update_data.keys())}")
    return volunteer


async def update_burnout_after_assignment(
    db: AsyncSession,
    volunteer: Volunteer,
    task_complexity: int,
) -> float:
    """
    Update volunteer burnout after completing/receiving a task.

    If burnout exceeds threshold, auto-rests the volunteer.

    Returns:
        New burnout score
    """
    new_burnout = compute_burnout_increment(
        current_burnout=volunteer.burnout_score,
        task_complexity=task_complexity,
    )
    volunteer.burnout_score = new_burnout
    volunteer.total_assignments += 1
    volunteer.active_assignments += 1

    # Auto-rest check
    if should_rest(new_burnout, settings.BURNOUT_THRESHOLD):
        volunteer.status = "resting"
        logger.warning(
            f"Volunteer {volunteer.id[:8]} '{volunteer.name}' auto-rested: "
            f"burnout={new_burnout:.2f} > threshold={settings.BURNOUT_THRESHOLD}"
        )

    await db.flush()
    return new_burnout


async def compute_fairness_metrics(db: AsyncSession, ngo_id: str | None = None) -> dict:
    """Compute current Gini coefficient across all volunteers."""
    query = select(Volunteer.total_assignments).where(Volunteer.is_active == True)  # noqa: E712
    if ngo_id:
        query = query.where(Volunteer.ngo_id == ngo_id)
    result = await db.execute(query)
    counts = [row[0] for row in result.all()]
    gini = gini_coefficient(counts)

    return {
        "gini_coefficient": round(gini, 4),
        "total_volunteers": len(counts),
        "min_assignments": min(counts) if counts else 0,
        "max_assignments": max(counts) if counts else 0,
        "mean_assignments": round(sum(counts) / len(counts), 2) if counts else 0,
    }


def _normalize(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _compute_engagement_score(
    tasks_assigned: int,
    tasks_accepted: int,
    avg_response_time: float,
    last_active: datetime | None,
) -> float:
    acceptance_rate = (tasks_accepted / tasks_assigned) if tasks_assigned > 0 else 0.0
    response_speed = 1.0 / (1.0 + max(avg_response_time, 0.0) / 300.0)
    activity_frequency = 0.0
    active_ts = _as_utc(last_active)
    if active_ts is not None:
        hours_since_active = (_utc_now() - active_ts).total_seconds() / 3600.0
        activity_frequency = 1.0 / (1.0 + max(hours_since_active, 0.0) / 24.0)

    engagement = (
        0.5 * acceptance_rate
        + 0.3 * response_speed
        + 0.2 * activity_frequency
    )
    return round(_normalize(engagement), 4)


def _compute_burnout_risk(
    tasks_assigned: int,
    engagement_score: float,
    last_active: datetime | None,
) -> float:
    workload_risk = min(tasks_assigned / 30.0, 1.0)
    inactivity_risk = 0.0
    active_ts = _as_utc(last_active)
    if active_ts is not None:
        inactivity_hours = (_utc_now() - active_ts).total_seconds() / 3600.0
        inactivity_risk = min(max(inactivity_hours / (24.0 * 7.0), 0.0), 1.0)
    disengagement_risk = 1.0 - _normalize(engagement_score)
    burnout = (0.5 * workload_risk) + (0.2 * inactivity_risk) + (0.3 * disengagement_risk)
    return round(_normalize(burnout), 4)


async def _get_or_create_metrics(db: AsyncSession, volunteer_id: str) -> VolunteerMetrics:
    try:
        result = await db.execute(
            select(VolunteerMetrics).where(VolunteerMetrics.volunteer_id == volunteer_id)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            return row

        row = VolunteerMetrics(volunteer_id=volunteer_id)
        db.add(row)
        await db.flush()
        return row
    except Exception:
        logger.warning("volunteer_metrics table unavailable; using ephemeral metrics fallback")
        return SimpleNamespace(
            volunteer_id=volunteer_id,
            tasks_assigned=0,
            tasks_accepted=0,
            tasks_rejected=0,
            avg_response_time=0.0,
            last_active=None,
            engagement_score=0.5,
            burnout_risk=0.0,
        )


async def get_metrics_for_volunteer(db: AsyncSession, volunteer_id: str) -> VolunteerMetrics:
    """Fetch or initialize lifecycle metrics for one volunteer."""
    return await _get_or_create_metrics(db, volunteer_id)


async def get_metrics_map(
    db: AsyncSession,
    volunteer_ids: list[str],
) -> dict[str, VolunteerMetrics]:
    """Batch metrics fetch keyed by volunteer_id, creating missing rows lazily."""
    ids = [v for v in volunteer_ids if v]
    if not ids:
        return {}

    result = await db.execute(
        select(VolunteerMetrics).where(VolunteerMetrics.volunteer_id.in_(ids))
    )
    rows = {m.volunteer_id: m for m in result.scalars().all()}
    for volunteer_id in ids:
        if volunteer_id not in rows:
            rows[volunteer_id] = await _get_or_create_metrics(db, volunteer_id)
    return rows


async def record_assignment_metrics(
    db: AsyncSession,
    volunteer_id: str,
    response_time_seconds: float | None = None,
    accepted: bool | None = None,
) -> VolunteerMetrics:
    """
    Update lifecycle metrics after assignment/response events.
    """
    metrics = await _get_or_create_metrics(db, volunteer_id)
    metrics.tasks_assigned += 1
    if accepted is True:
        metrics.tasks_accepted += 1
    elif accepted is False:
        metrics.tasks_rejected += 1

    if response_time_seconds is not None and response_time_seconds >= 0:
        historical = metrics.tasks_accepted + metrics.tasks_rejected
        if historical <= 1:
            metrics.avg_response_time = float(response_time_seconds)
        else:
            metrics.avg_response_time = (
                (metrics.avg_response_time * (historical - 1)) + float(response_time_seconds)
            ) / historical

    metrics.last_active = _utc_now()
    metrics.engagement_score = _compute_engagement_score(
        tasks_assigned=metrics.tasks_assigned,
        tasks_accepted=metrics.tasks_accepted,
        avg_response_time=metrics.avg_response_time,
        last_active=metrics.last_active,
    )
    metrics.burnout_risk = _compute_burnout_risk(
        tasks_assigned=metrics.tasks_assigned,
        engagement_score=metrics.engagement_score,
        last_active=metrics.last_active,
    )
    await db.flush()
    return metrics


async def record_response_metrics(
    db: AsyncSession,
    volunteer_id: str,
    accepted: bool,
    response_time_seconds: float | None = None,
) -> VolunteerMetrics:
    """
    Update lifecycle metrics when a volunteer accepts/rejects.
    """
    metrics = await _get_or_create_metrics(db, volunteer_id)
    if accepted:
        metrics.tasks_accepted += 1
    else:
        metrics.tasks_rejected += 1

    if response_time_seconds is not None and response_time_seconds >= 0:
        total_responses = metrics.tasks_accepted + metrics.tasks_rejected
        if total_responses <= 1:
            metrics.avg_response_time = float(response_time_seconds)
        else:
            metrics.avg_response_time = (
                (metrics.avg_response_time * (total_responses - 1)) + float(response_time_seconds)
            ) / total_responses

    metrics.last_active = _utc_now()
    metrics.engagement_score = _compute_engagement_score(
        tasks_assigned=metrics.tasks_assigned,
        tasks_accepted=metrics.tasks_accepted,
        avg_response_time=metrics.avg_response_time,
        last_active=metrics.last_active,
    )
    metrics.burnout_risk = _compute_burnout_risk(
        tasks_assigned=metrics.tasks_assigned,
        engagement_score=metrics.engagement_score,
        last_active=metrics.last_active,
    )
    await db.flush()
    return metrics
