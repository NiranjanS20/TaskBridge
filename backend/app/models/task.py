"""
VASAE Task Model
----------------
Represents a unit of work that needs volunteer assignment.
Tasks flow through: ingested → processed → allocated → completed.

Key design decisions:
- required_skills stored as JSON array — avoids join table overhead
  for a read-heavy scoring path
- complexity is 1-10 scale, urgency is 1-5 scale (normalized in scoring)
- waiting_time is computed dynamically from created_at, not stored
- team_size > 1 enables multi-volunteer assignment
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, DateTime, JSON, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Task(Base):
    __tablename__ = "tasks"

    # --- Identity ---
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    ngo_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # --- Content ---
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    raw_input: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Original unstructured NGO input before NLP processing",
    )

    # --- Classification ---
    category: Mapped[str] = mapped_column(
        String(100), nullable=False, default="general",
        comment="e.g., medical, logistics, search_rescue, shelter",
    )
    required_skills: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="Skills needed — matched against volunteer.skills",
    )

    # --- Scoring Inputs ---
    urgency: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3,
        comment="1 (low) to 5 (critical)",
    )
    complexity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5,
        comment="1 (trivial) to 10 (extreme)",
    )
    team_size: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
        comment="Number of volunteers needed",
    )

    # --- Geolocation ---
    latitude: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    longitude: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    region: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Named region for prediction engine grouping",
    )

    # --- Status ---
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="pending | processing | allocated | completed | cancelled",
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
        "Assignment", back_populates="task", cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="task", cascade="all, delete-orphan",
    )
    organization: Mapped["Organization | None"] = relationship("Organization", back_populates="tasks")

    @property
    def waiting_time_minutes(self) -> float:
        """Dynamic waiting time since creation (in minutes)."""
        delta = datetime.now(timezone.utc) - self.created_at.replace(
            tzinfo=timezone.utc
        ) if self.created_at.tzinfo is None else datetime.now(timezone.utc) - self.created_at
        return delta.total_seconds() / 60.0

    def __repr__(self) -> str:
        return f"<Task id={self.id[:8]} title='{self.title}' urgency={self.urgency} status={self.status}>"
