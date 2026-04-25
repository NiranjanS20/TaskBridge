import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VolunteerMetrics(Base):
    __tablename__ = "volunteer_metrics"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    volunteer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("volunteers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    tasks_assigned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tasks_accepted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tasks_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_response_time: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_active: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    engagement_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    burnout_risk: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
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
