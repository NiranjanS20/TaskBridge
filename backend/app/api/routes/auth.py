from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.organization import Organization
from app.models.user import User
from app.models.volunteer import Volunteer
from app.schemas.auth_schema import (
    AdminSignupRequest,
    AuthTokenResponse,
    AuthUserResponse,
    LoginRequest,
    ProfileUpdateRequest,
    VolunteerSignupRequest,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register/admin", response_model=AuthTokenResponse)
async def register_admin(
    data: AdminSignupRequest,
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.register_admin(db, data)


@router.post("/register/volunteer", response_model=AuthTokenResponse)
async def register_volunteer(
    data: VolunteerSignupRequest,
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.register_volunteer(db, data)


@router.post("/login", response_model=AuthTokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.login(db, data)


@router.get("/me", response_model=AuthUserResponse)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.get_user_response(db, current_user.id)


@router.patch("/me", response_model=AuthUserResponse)
async def update_me(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)

    if "full_name" in update_data:
        current_user.full_name = update_data["full_name"].strip()

    if current_user.role == auth_service.ROLE_VOLUNTEER:
        result = await db.execute(select(Volunteer).where(Volunteer.user_id == current_user.id))
        volunteer = result.scalar_one_or_none()
        if volunteer is not None:
            if "latitude" in update_data:
                volunteer.latitude = update_data["latitude"]
            if "longitude" in update_data:
                volunteer.longitude = update_data["longitude"]
            if "area" in update_data:
                volunteer.area = update_data["area"]
    elif current_user.ngo_id:
        result = await db.execute(select(Organization).where(Organization.id == current_user.ngo_id))
        org = result.scalar_one_or_none()
        if org is not None:
            if "latitude" in update_data:
                org.latitude = update_data["latitude"]
            if "longitude" in update_data:
                org.longitude = update_data["longitude"]
            if "area" in update_data:
                org.area = update_data["area"]
            if "ngo_description" in update_data:
                org.description = update_data["ngo_description"]

    await db.flush()
    return await auth_service.get_user_response(db, current_user.id)
