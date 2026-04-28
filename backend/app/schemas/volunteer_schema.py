"""
VASAE Volunteer Schemas
-----------------------
Pydantic v2 request/response contracts for the Volunteer domain.
Also includes assignment and explainability response schemas.
"""

from pydantic import BaseModel, Field
from datetime import datetime


# ===== VOLUNTEER REQUEST SCHEMAS =====

class VolunteerCreateRequest(BaseModel):
    """Register a new volunteer."""
    name: str = Field(..., min_length=2, max_length=255)
    email: str | None = Field(default=None)
    skills: list[str] = Field(default_factory=list)
    latitude: float = Field(default=0.0, ge=-90, le=90)
    longitude: float = Field(default=0.0, ge=-180, le=180)
    area: str | None = None
    availability: float = Field(default=1.0, ge=0.0, le=1.0)
    reliability: float = Field(default=0.8, ge=0.0, le=1.0)


class VolunteerUpdateRequest(BaseModel):
    """Partial update for existing volunteers."""
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    availability: float | None = Field(default=None, ge=0.0, le=1.0)
    skills: list[str] | None = None
    area: str | None = None
    status: str | None = Field(
        default=None,
        pattern="^(available|deployed|resting|unavailable)$",
    )


# ===== VOLUNTEER RESPONSE SCHEMAS =====

class VolunteerResponse(BaseModel):
    """Full volunteer response returned by API."""
    id: str
    name: str
    email: str | None
    skills: list[str]
    latitude: float
    longitude: float
    area: str | None
    availability: float
    reliability: float
    burnout_score: float
    total_assignments: int
    active_assignments: int
    status: str
    is_active: bool
    is_deployable: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VolunteerListResponse(BaseModel):
    """Paginated list of volunteers."""
    volunteers: list[VolunteerResponse]
    total: int
    page: int
    page_size: int


# ===== ASSIGNMENT SCHEMAS =====

class AssignmentResponse(BaseModel):
    """Assignment binding returned by API."""
    id: str
    task_id: str
    volunteer_id: str
    vas_score: float
    status: str
    assigned_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class AllocationResult(BaseModel):
    """Result of a full allocation cycle."""
    assignments_created: int
    assignments_reassigned: int
    tasks_unmatched: int
    cycle_duration_ms: float
    details: list[AssignmentResponse]


# ===== EXPLAINABILITY SCHEMAS =====

class ExplainabilityFactors(BaseModel):
    """Sub-scores that contributed to the allocation decision."""
    skill_match: float = Field(ge=0.0, le=1.0)
    proximity: float = Field(ge=0.0, le=1.0)
    reliability: float = Field(ge=0.0, le=1.0)
    availability: float = Field(ge=0.0, le=1.0)
    burnout_adjustment: float = Field(ge=0.0, le=1.0)
    volunteer_fit: float
    final_vas_score: float


class AlternativeCandidate(BaseModel):
    """Runner-up volunteer that was considered."""
    volunteer_id: str
    volunteer_name: str
    vas_score: float
    rejection_reason: str


class ExplainabilityResponse(BaseModel):
    """Full explainability report for a task allocation."""
    task_id: str
    chosen_volunteer_id: str | None
    chosen_volunteer_name: str | None
    reason: str
    factors: ExplainabilityFactors | None
    alternatives: list[AlternativeCandidate]
    allocation_mode: str
    override_flag: bool
    confidence: float = 0.0
    created_at: datetime

    model_config = {"from_attributes": True}
