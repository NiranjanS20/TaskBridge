"""
VASAE Assignment Model
----------------------
Represents a task ↔ volunteer binding produced by the allocation engine.

Key design decisions:
- vas_score is stored at assignment time for audit trail
- status tracks the full lifecycle: assigned → active → completed/failed
- Composite uniqueness on (task_id, volunteer_id) prevents duplicate bindings
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Assignment(Base):
    __tablename__ = "assignments"

    # --- Identity ---
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # --- Foreign Keys ---
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    volunteer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("volunteers.id", ondelete="CASCADE"),
        nullable=False,
    )

    # --- Scoring Snapshot ---
    vas_score: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="VAS score at assignment time — frozen for audit",
    )

    # --- Status ---
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="assigned",
        comment="assigned | active | completed | failed | reassigned",
    )

    # --- Timestamps ---
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # --- Relationships ---
    task: Mapped["Task"] = relationship("Task", back_populates="assignments")
    volunteer: Mapped["Volunteer"] = relationship("Volunteer", back_populates="assignments")

    # --- Constraints ---
    __table_args__ = (
        UniqueConstraint("task_id", "volunteer_id", name="uq_task_volunteer"),
    )

    def __repr__(self) -> str:
        return (
            f"<Assignment task={self.task_id[:8]}->volunteer={self.volunteer_id[:8]} "
            f"score={self.vas_score:.4f} status={self.status}>"
        )
