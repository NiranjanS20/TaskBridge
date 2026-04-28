"""
VASAE Task Schemas
------------------
Pydantic v2 request/response contracts for the Task domain.
Strict validation — bad data never reaches the scoring engine.
"""

from pydantic import BaseModel, Field
from datetime import datetime


# ===== REQUEST SCHEMAS =====

class TaskUploadRequest(BaseModel):
    """Raw task upload — can be unstructured text from NGO."""
    raw_input: str = Field(
        ...,
        min_length=10,
        description="Unstructured text describing the task/crisis",
    )
    latitude: float = Field(default=0.0, ge=-90, le=90)
    longitude: float = Field(default=0.0, ge=-180, le=180)
    region: str | None = Field(default=None, description="Named region")


class TaskCreateRequest(BaseModel):
    """Structured task creation — bypasses NLP pipeline."""
    title: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    category: str = Field(default="general", max_length=100)
    required_skills: list[str] = Field(default_factory=list)
    urgency: int = Field(default=3, ge=1, le=5)
    complexity: int = Field(default=5, ge=1, le=10)
    team_size: int = Field(default=1, ge=1, le=50)
    latitude: float = Field(default=0.0, ge=-90, le=90)
    longitude: float = Field(default=0.0, ge=-180, le=180)
    region: str | None = None


class TaskUpdateRequest(BaseModel):
    """Partial update for existing tasks."""
    urgency: int | None = Field(default=None, ge=1, le=5)
    complexity: int | None = Field(default=None, ge=1, le=10)
    status: str | None = Field(default=None, pattern="^(pending|processing|allocated|completed|cancelled)$")
    team_size: int | None = Field(default=None, ge=1, le=50)


# ===== RESPONSE SCHEMAS =====

class TaskResponse(BaseModel):
    """Full task response returned by API."""
    id: str
    title: str
    description: str | None
    raw_input: str | None
    category: str
    required_skills: list[str]
    urgency: int
    complexity: int
    team_size: int
    latitude: float
    longitude: float
    region: str | None
    status: str
    waiting_time_minutes: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """Paginated list of tasks."""
    tasks: list[TaskResponse]
    total: int
    page: int
    page_size: int
