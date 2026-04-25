from __future__ import annotations
import logging

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash, verify_password, MAX_PASSWORD_BYTES
from app.models.organization import Organization
from app.models.user import User
from app.models.volunteer import Volunteer
from app.schemas.auth_schema import (
    AdminSignupRequest,
    AuthTokenResponse,
    AuthUserResponse,
    LoginRequest,
    VolunteerSignupRequest,
)

logger = logging.getLogger(__name__)

ROLE_NGO_ADMIN = "NGO_ADMIN"
ROLE_NGO_MANAGER = "NGO_MANAGER"
ROLE_VOLUNTEER = "VOLUNTEER"


def normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def normalize_email(value: str) -> str:
    return value.strip().lower()


def _validate_password(password: str) -> None:
    """Validate password before hashing."""
    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot be empty"
        )
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password too long (max {MAX_PASSWORD_BYTES} bytes for security constraints)"
        )


async def _get_org_by_mapping(db: AsyncSession, ngo_name: str, ngo_email: str) -> Organization | None:
    normalized_name = normalize_text(ngo_name)
    normalized_email = normalize_email(ngo_email)
    result = await db.execute(
        select(Organization).where(
            and_(
                Organization.normalized_name == normalized_name,
                Organization.normalized_email == normalized_email,
            )
        )
    )
    return result.scalar_one_or_none()


async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == normalize_email(email)))
    return result.scalar_one_or_none()


async def _build_user_response(db: AsyncSession, user: User) -> AuthUserResponse:
    ngo = None
    if user.ngo_id:
        ngo_result = await db.execute(select(Organization).where(Organization.id == user.ngo_id))
        ngo = ngo_result.scalar_one_or_none()

    skills: list[str] = []
    latitude = ngo.latitude if ngo else None
    longitude = ngo.longitude if ngo else None
    area = ngo.area if ngo else None

    if user.role == ROLE_VOLUNTEER:
        result = await db.execute(select(Volunteer).where(Volunteer.user_id == user.id))
        volunteer = result.scalar_one_or_none()
        if volunteer is not None:
            skills = volunteer.skills or []
            latitude = volunteer.latitude
            longitude = volunteer.longitude
            area = volunteer.area

    return AuthUserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        ngo_id=user.ngo_id,
        ngo_name=ngo.name if ngo else None,
        ngo_email=ngo.email if ngo else None,
        ngo_description=ngo.description if ngo else None,
        latitude=latitude,
        longitude=longitude,
        area=area,
        skills=skills,
        created_at=user.created_at,
    )


async def register_admin(db: AsyncSession, data: AdminSignupRequest) -> AuthTokenResponse:
    _validate_password(data.password)
    
    existing = await _get_user_by_email(db, data.ngo_email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    org = await _get_org_by_mapping(db, data.ngo_name, data.ngo_email)
    if org is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="NGO mapping already exists. Please login or use manager onboarding.",
        )

    org = Organization(
        name=data.ngo_name.strip(),
        normalized_name=normalize_text(data.ngo_name),
        email=normalize_email(data.ngo_email),
        normalized_email=normalize_email(data.ngo_email),
        description=(data.ngo_description or None),
        latitude=data.latitude,
        longitude=data.longitude,
        area=(data.area or None),
    )
    db.add(org)
    await db.flush()

    try:
        password_hash = get_password_hash(data.password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Password hashing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password"
        )

    user = User(
        full_name=data.full_name.strip(),
        email=normalize_email(data.ngo_email),
        password_hash=password_hash,
        role=ROLE_NGO_ADMIN,
        ngo_id=org.id,
    )
    db.add(user)
    await db.flush()

    token = create_access_token(subject=user.id, role=user.role, ngo_id=user.ngo_id)
    return AuthTokenResponse(access_token=token, user=await _build_user_response(db, user))


async def register_volunteer(db: AsyncSession, data: VolunteerSignupRequest) -> AuthTokenResponse:
    _validate_password(data.password)
    
    existing = await _get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    org = await _get_org_by_mapping(db, data.ngo_name, data.ngo_email)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid NGO mapping. NGO name/email does not match any registered NGO.",
        )

    try:
        password_hash = get_password_hash(data.password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Password hashing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password"
        )

    user = User(
        full_name=data.full_name.strip(),
        email=normalize_email(data.email),
        password_hash=password_hash,
        role=ROLE_VOLUNTEER,
        ngo_id=org.id,
    )
    db.add(user)
    await db.flush()

    volunteer = Volunteer(
        user_id=user.id,
        ngo_id=org.id,
        name=data.full_name.strip(),
        email=normalize_email(data.email),
        skills=[normalize_text(skill) for skill in data.skills if skill and skill.strip()],
        latitude=data.latitude if data.latitude is not None else org.latitude or 0.0,
        longitude=data.longitude if data.longitude is not None else org.longitude or 0.0,
        area=(data.area or org.area),
        availability=1.0,
        reliability=0.8,
        status="available",
    )
    db.add(volunteer)
    await db.flush()

    token = create_access_token(subject=user.id, role=user.role, ngo_id=user.ngo_id)
    return AuthTokenResponse(access_token=token, user=await _build_user_response(db, user))


async def login(db: AsyncSession, data: LoginRequest) -> AuthTokenResponse:
    user = await _get_user_by_email(db, data.email)
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(subject=user.id, role=user.role, ngo_id=user.ngo_id)
    return AuthTokenResponse(access_token=token, user=await _build_user_response(db, user))


async def get_user_response(db: AsyncSession, user_id: str) -> AuthUserResponse:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return await _build_user_response(db, user)
