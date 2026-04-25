"""
VASAE Learning API Routes
--------------------------
Observability endpoints for the adaptive learning system.

Provides:
- GET /learning/metrics — Current weights, versions, feedback stats
- GET /learning/weights — Active weight profiles
- GET /learning/history — Weight version audit trail
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import learning_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/learning", tags=["Learning"])


@router.get("/metrics")
async def get_learning_metrics(
    db: AsyncSession = Depends(get_db),
):
    """
    Comprehensive adaptive learning system metrics.

    Returns:
    - Current global and context-specific weight profiles
    - Weight version history (last 10)
    - Feedback statistics (count, confidence, effective learning rate)
    - Recent override logs (last 5)
    """
    metrics = await learning_service.get_learning_metrics(db)
    return metrics


@router.get("/weights")
async def get_active_weights(
    db: AsyncSession = Depends(get_db),
):
    """Return all active weight profiles."""
    from sqlalchemy import select
    from app.models.learning_log import AdaptiveWeight

    result = await db.execute(select(AdaptiveWeight))
    profiles = list(result.scalars().all())

    return {
        "profiles": [
            {
                "profile": p.profile,
                "weights": p.weights,
                "version_id": p.version_id,
                "source": p.source,
                "updated_at": str(p.updated_at),
            }
            for p in profiles
        ],
        "total": len(profiles),
    }


@router.get("/history")
async def get_weight_history(
    profile: str = "global",
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Return weight version audit trail for a given profile."""
    from sqlalchemy import select
    from app.models.learning_log import WeightVersion

    result = await db.execute(
        select(WeightVersion)
        .where(WeightVersion.profile == profile)
        .order_by(WeightVersion.created_at.desc())
        .limit(min(limit, 100))
    )
    versions = list(result.scalars().all())

    return {
        "profile": profile,
        "versions": [
            {
                "version_id": v.version_id,
                "weights": v.weights,
                "source": v.source,
                "parent_version_id": v.parent_version_id,
                "delta_applied": v.delta_applied,
                "feedback_count_at_update": v.feedback_count_at_update,
                "created_at": str(v.created_at),
            }
            for v in versions
        ],
        "total": len(versions),
    }
