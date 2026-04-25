"""
VASAE Adaptive Learning Models
------------------------------
Persistence for override-driven learning signals and dynamic fit weights.

Extensions (Tier-1 Hardening):
- Weight versioning: version_id, source, parent linkage
- WeightVersion: append-only audit trail for every weight mutation
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LearningLog(Base):
    __tablename__ = "learning_logs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    original_volunteer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("volunteers.id", ondelete="CASCADE"),
        nullable=False,
    )
    overridden_volunteer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("volunteers.id", ondelete="CASCADE"),
        nullable=False,
    )

    original_score: Mapped[float] = mapped_column(Float, nullable=False)
    new_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Required by spec: overridden - original per feature.
    feature_diff: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Extra explainability context for post-hoc analysis.
    original_features: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    overridden_features: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class AdaptiveWeight(Base):
    """
    Active weight profile used by the scoring engine.

    Supports hybrid model: global + per-category + per-region profiles.
    Profile key format:
      - "global"               → system-wide baseline
      - "category:medical"     → category-specific context
      - "region:sector_4"      → region-specific context
    """
    __tablename__ = "adaptive_weights"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    profile: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, default="global")
    weights: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # --- Versioning ---
    version_id: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
        comment="Monotonically increasing version counter",
    )
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="default",
        comment="Origin of this weight update: default | override_feedback | manual | rollback",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class WeightVersion(Base):
    """
    Append-only audit trail for weight mutations.

    Every time AdaptiveWeight is updated, a snapshot is appended here
    for full reproducibility and rollback support.
    """
    __tablename__ = "weight_versions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    profile: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="Weight profile key (e.g., global, category:medical)",
    )
    version_id: Mapped[int] = mapped_column(Integer, nullable=False)
    weights: Mapped[dict] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="What caused this version: override_feedback | manual | rollback",
    )
    parent_version_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Previous version this was derived from",
    )
    delta_applied: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict,
        comment="The delta that produced this version from its parent",
    )
    feedback_count_at_update: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Total feedback count when this version was created",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
