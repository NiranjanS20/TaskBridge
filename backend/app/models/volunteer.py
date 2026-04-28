"""
VASAE Volunteer Model
---------------------
Represents a deployable human resource in the system.

Key design decisions:
- skills stored as JSON array (same format as task.required_skills)
  for O(1) intersection checks in the scoring engine
- burnout_score is a float 0.0–1.0, updated by the lifecycle engine
- reliability is a rolling average computed from assignment outcomes
- total_assignments tracks load for Gini fairness computation
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Volunteer(Base):
    __tablename__ = "volunteers"

    # --- Identity ---
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    ngo_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # --- Capabilities ---
    skills: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="e.g., ['medical', 'logistics', 'search_rescue']",
    )

    # --- Geolocation ---
    latitude: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    longitude: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    area: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # --- Scoring Inputs ---
    availability: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0,
        comment="0.0 (unavailable) to 1.0 (fully available)",
    )
    reliability: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.8,
        comment="Rolling average 0.0–1.0 from assignment outcomes",
    )
    burnout_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="0.0 (fresh) to 1.0 (exhausted) — lifecycle engine updates this",
    )

    # --- Workload Tracking ---
    total_assignments: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Cumulative count for Gini fairness coefficient",
    )
    active_assignments: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Currently active assignments",
    )

    # --- Status ---
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="available",
        comment="available | deployed | resting | unavailable",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="Soft delete / deactivation flag",
    )

    # --- Timestamps ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # --- Relationships ---
    assignments: Mapped[list["Assignment"]] = relationship(
        "Assignment", back_populates="volunteer", cascade="all, delete-orphan",
    )
    user: Mapped["User | None"] = relationship("User", back_populates="volunteer_profile")
    organization: Mapped["Organization | None"] = relationship("Organization", back_populates="volunteers")

    @property
    def is_deployable(self) -> bool:
        """Can this volunteer be assigned right now?"""
        return (
            self.is_active
            and self.status == "available"
            and self.availability > 0.0
            and self.burnout_score < 0.70
        )

    def __repr__(self) -> str:
        return (
            f"<Volunteer id={self.id[:8]} name='{self.name}' "
            f"burnout={self.burnout_score:.2f} status={self.status}>"
        )
