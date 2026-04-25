"""
VASAE Audit Log Model
---------------------
Every allocation decision generates an audit record.
This is the explainability backbone of the system.

Key design decisions:
- factors stored as JSON dict with exact sub-scores
- alternatives stored as JSON array of runner-up volunteer objects
- override_flag marks human-overridden allocations
- This table is append-only — never updated, only inserted
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

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
    chosen_volunteer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("volunteers.id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL if no match found (graceful degradation)",
    )
    original_volunteer_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("volunteers.id", ondelete="SET NULL"),
        nullable=True,
        comment="Original AI-chosen volunteer before human override",
    )
    overridden_volunteer_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("volunteers.id", ondelete="SET NULL"),
        nullable=True,
        comment="Human-selected volunteer for override decisions",
    )

    # --- Explainability ---
    reason: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Human-readable explanation of the decision",
    )
    vas_score: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Final VAS score of the chosen volunteer",
    )
    factors: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict,
        comment='{"skill_match": 0.9, "proximity": 0.7, "reliability": 0.85, "burnout": 0.1}',
    )
    alternatives: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment='[{"volunteer_id": "...", "vas_score": 0.72, "reason": "..."}]',
    )
    original_feature_vector: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment='{"skill": 0.7, "proximity": 0.5, "reliability": 0.9, "availability": 0.8}',
    )
    overridden_feature_vector: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment='{"skill": 0.9, "proximity": 0.4, "reliability": 0.95, "availability": 0.7}',
    )

    # --- Metadata ---
    override_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True if a human admin overrode the AI decision",
    )
    allocation_mode: Mapped[str] = mapped_column(
        String(30), nullable=False, default="standard",
        comment="standard | degraded_skill | degraded_radius | escalated",
    )

    # --- Reproducibility (Tier-1 Hardening) ---
    weight_snapshot: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict,
        comment="Scoring weights active at decision time for full reproducibility",
    )
    cycle_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True,
        comment="Groups audit logs from the same allocation cycle",
    )
    confidence_score: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Difference between top-2 VAS scores — higher = more confident",
    )

    # --- Timestamp ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # --- Relationships ---
    task: Mapped["Task"] = relationship("Task", back_populates="audit_logs")

    def __repr__(self) -> str:
        return (
            f"<AuditLog task={self.task_id[:8]} "
            f"volunteer={self.chosen_volunteer_id[:8] if self.chosen_volunteer_id else 'NONE'} "
            f"mode={self.allocation_mode}>"
        )
