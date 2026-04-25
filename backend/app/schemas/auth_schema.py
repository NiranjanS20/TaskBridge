from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class AdminSignupRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    ngo_name: str = Field(..., min_length=2, max_length=255)
    ngo_email: EmailStr
    password: str = Field(..., min_length=8, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    area: str | None = Field(default=None, max_length=255)
    ngo_description: str | None = Field(default=None, max_length=4000)


class VolunteerSignupRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    ngo_name: str = Field(..., min_length=2, max_length=255)
    ngo_email: EmailStr
    skills: list[str] = Field(default_factory=list)
    password: str = Field(..., min_length=8, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    area: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=255)


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    area: str | None = Field(default=None, max_length=255)
    ngo_description: str | None = Field(default=None, max_length=4000)


class AuthUserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    role: str
    ngo_id: str | None
    ngo_name: str | None
    ngo_email: str | None
    ngo_description: str | None
    latitude: float | None
    longitude: float | None
    area: str | None
    skills: list[str]
    created_at: datetime


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse
