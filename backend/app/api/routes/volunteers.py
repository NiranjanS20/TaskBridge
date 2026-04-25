"""
VASAE Volunteers API Routes
----------------------------
Thin controllers for volunteer management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.dependencies import get_current_user, require_roles
from app.models.user import User
from app.services.auth_service import ROLE_NGO_ADMIN, ROLE_NGO_MANAGER, ROLE_VOLUNTEER
from app.schemas.volunteer_schema import (
    VolunteerCreateRequest,
    VolunteerUpdateRequest,
    VolunteerResponse,
    VolunteerListResponse,
)
from app.services import lifecycle_service
from app.events.event_dispatcher import publish, EVENT_VOLUNTEER_UPDATE
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/volunteers", tags=["Volunteers"])


@router.post("/add", response_model=VolunteerResponse, status_code=status.HTTP_201_CREATED)
async def add_volunteer(
    data: VolunteerCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_NGO_ADMIN, ROLE_NGO_MANAGER)),
):
    """Register a new volunteer."""
    volunteer = await lifecycle_service.create_volunteer(db, data, ngo_id=current_user.ngo_id)
    await db.commit()

    await publish(EVENT_VOLUNTEER_UPDATE, {"volunteer_id": volunteer.id, "action": "created", "ngo_id": current_user.ngo_id})

    return VolunteerResponse.model_validate(volunteer)


@router.get("", response_model=VolunteerListResponse)
async def list_volunteers(
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_NGO_ADMIN, ROLE_NGO_MANAGER)),
):
    """List all volunteers with pagination."""
    volunteers, total = await lifecycle_service.get_all_volunteers(db, page, page_size, ngo_id=current_user.ngo_id)
    return VolunteerListResponse(
        volunteers=[VolunteerResponse.model_validate(v) for v in volunteers],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/fairness")
async def get_fairness_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_NGO_ADMIN, ROLE_NGO_MANAGER)),
):
    """Get current fairness metrics (Gini coefficient)."""
    metrics = await lifecycle_service.compute_fairness_metrics(db, ngo_id=current_user.ngo_id)
    return metrics


@router.get("/{volunteer_id}/metrics")
async def get_volunteer_metrics(
    volunteer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return lifecycle engagement and burnout metrics for one volunteer."""
    volunteer = await lifecycle_service.get_volunteer_by_id(db, volunteer_id)
    if not volunteer:
        raise HTTPException(status_code=404, detail=f"Volunteer {volunteer_id} not found")
    if current_user.role == ROLE_VOLUNTEER and volunteer.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if current_user.role != ROLE_VOLUNTEER and current_user.ngo_id and volunteer.ngo_id != current_user.ngo_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    metrics = await lifecycle_service.get_metrics_for_volunteer(db, volunteer_id)
    return {
        "volunteer_id": volunteer_id,
        "tasks_assigned": metrics.tasks_assigned,
        "tasks_accepted": metrics.tasks_accepted,
        "tasks_rejected": metrics.tasks_rejected,
        "avg_response_time": round(metrics.avg_response_time, 4),
        "last_active": metrics.last_active.isoformat() if metrics.last_active else None,
        "engagement_score": metrics.engagement_score,
        "burnout_risk": metrics.burnout_risk,
    }


@router.get("/{volunteer_id}", response_model=VolunteerResponse)
async def get_volunteer(
    volunteer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single volunteer."""
    volunteer = await lifecycle_service.get_volunteer_by_id(db, volunteer_id)
    if not volunteer:
        raise HTTPException(status_code=404, detail=f"Volunteer {volunteer_id} not found")
    if current_user.role == ROLE_VOLUNTEER and volunteer.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if current_user.role != ROLE_VOLUNTEER and current_user.ngo_id and volunteer.ngo_id != current_user.ngo_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return VolunteerResponse.model_validate(volunteer)


@router.patch("/{volunteer_id}", response_model=VolunteerResponse)
async def update_volunteer(
    volunteer_id: str,
    data: VolunteerUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a volunteer. Fires volunteer_update event."""
    existing = await lifecycle_service.get_volunteer_by_id(db, volunteer_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Volunteer {volunteer_id} not found")
    if current_user.role == ROLE_VOLUNTEER and existing.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if current_user.role != ROLE_VOLUNTEER and current_user.ngo_id and existing.ngo_id != current_user.ngo_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    ngo_scope = current_user.ngo_id if current_user.role != ROLE_VOLUNTEER else None
    volunteer = await lifecycle_service.update_volunteer(db, volunteer_id, data, ngo_id=ngo_scope)
    if not volunteer:
        raise HTTPException(status_code=404, detail=f"Volunteer {volunteer_id} not found")
    await db.commit()

    await publish(EVENT_VOLUNTEER_UPDATE, {
        "volunteer_id": volunteer_id,
        "action": "updated",
        "fields": list(data.model_dump(exclude_unset=True).keys()),
        "ngo_id": volunteer.ngo_id,
    })

    return VolunteerResponse.model_validate(volunteer)
