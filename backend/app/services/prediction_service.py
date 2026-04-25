"""
VASAE Prediction Service
------------------------
Service-layer orchestration for crisis prediction.

Bridges the pure prediction core (app/core/prediction.py) with
DB-backed historical data and the allocation engine.

Responsibilities:
- Collect task snapshots from DB for trend analysis
- Cache velocity factors in Redis for hot-path scoring
- Provide real-time region analytics
- Detect and surface hotspots
- Feed urgency modifiers into scoring/allocation pipeline
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.prediction import (
    DEFAULT_PREDICTION_CONFIG,
    PredictionConfig,
    RegionMetrics,
    TaskSnapshot,
    analyze_region,
    compute_urgency_modifier,
    detect_hotspots,
)
from app.models.task import Task
from app.utils.logger import get_logger

logger = get_logger(__name__)

# In-memory velocity cache — refreshed per prediction cycle
_velocity_cache: dict[str, float] = {}
_cache_expiry: float = 0.0
_CACHE_TTL_SECONDS = 120.0  # 2 minutes


# =====================================================================
# LEGACY API — Backward compatible with existing scoring pipeline
# =====================================================================

def get_velocity_factor(region: str) -> float:
    """
    Get cached crisis velocity factor for a region.

    Used by scoring engine in the hot path — must be fast.
    Falls back to 0.0 if no prediction data available.
    """
    if not region:
        return 0.0

    now = time.monotonic()
    if now > _cache_expiry and _velocity_cache:
        # Cache still valid — return from it
        pass

    factor = _velocity_cache.get(region.lower(), 0.0)
    return factor


@dataclass
class RegionPrediction:
    """Legacy prediction output — backward compatible."""
    region: str
    velocity_factor: float
    trend: str
    predicted_tasks_24h: int
    confidence: float


def predict_region(region: str) -> RegionPrediction:
    """
    Synchronous prediction fallback using cached data.

    For full DB-backed prediction, use predict_region_async.
    """
    factor = get_velocity_factor(region)

    if factor > 0.2:
        trend, predicted, confidence = "increasing", 25, 0.7
    elif factor > 0:
        trend, predicted, confidence = "increasing", 15, 0.6
    elif factor == 0:
        trend, predicted, confidence = "stable", 8, 0.8
    else:
        trend, predicted, confidence = "decreasing", 4, 0.75

    return RegionPrediction(
        region=region,
        velocity_factor=factor,
        trend=trend,
        predicted_tasks_24h=predicted,
        confidence=confidence,
    )


# =====================================================================
# ASYNC API — DB-backed full prediction
# =====================================================================

async def _collect_snapshots(
    db: AsyncSession,
    region: str,
    window_hours: float = 6.0,
) -> list[TaskSnapshot]:
    """
    Collect historical task count snapshots for a region.

    Groups tasks by creation hour to build a time series.
    """
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

    # Count tasks per hour bucket for this region
    hour_bucket = func.date_trunc("hour", Task.created_at)
    result = await db.execute(
        select(
            hour_bucket.label("hour_bucket"),
            func.count(Task.id).label("task_count"),
        )
        .where(Task.region == region)
        .where(Task.created_at >= cutoff)
        .group_by(hour_bucket)
        .order_by(hour_bucket)
    )

    snapshots = []
    for row in result.all():
        try:
            bucket_dt = row[0]
            count = int(row[1])
            # date_trunc returns a datetime; normalize to UTC if naive.
            if bucket_dt is None:
                continue
            if bucket_dt.tzinfo is None:
                dt = bucket_dt.replace(tzinfo=timezone.utc)
            else:
                dt = bucket_dt.astimezone(timezone.utc)
            snapshots.append(TaskSnapshot(
                region=region,
                count=count,
                timestamp_epoch=dt.timestamp(),
            ))
        except (ValueError, TypeError, AttributeError):
            continue

    return snapshots


async def _get_current_density(db: AsyncSession, region: str) -> int:
    """Count currently active (pending/processing) tasks in a region."""
    result = await db.execute(
        select(func.count(Task.id))
        .where(Task.region == region)
        .where(Task.status.in_(["pending", "processing", "allocated"]))
    )
    return result.scalar() or 0


async def predict_region_async(
    db: AsyncSession,
    region: str,
    config: PredictionConfig = DEFAULT_PREDICTION_CONFIG,
) -> RegionMetrics:
    """
    Full DB-backed prediction for a single region.

    1. Collects historical snapshots from DB
    2. Computes velocity, trend, risk via pure core functions
    3. Updates velocity cache for hot-path scoring
    """
    snapshots = await _collect_snapshots(db, region, config.window_hours)
    density = await _get_current_density(db, region)

    metrics = analyze_region(snapshots, density, config)

    # Update velocity cache
    urgency_mod = compute_urgency_modifier(metrics.risk_score)
    _velocity_cache[region.lower()] = urgency_mod

    logger.info(
        "Prediction for '%s': velocity=%.4f trend=%s risk=%.4f "
        "predicted_24h=%d density=%d hotspot=%s",
        region, metrics.velocity, metrics.trend, metrics.risk_score,
        metrics.predicted_tasks_24h, density, metrics.is_hotspot,
    )

    return metrics


async def predict_all_regions(
    db: AsyncSession,
    config: PredictionConfig = DEFAULT_PREDICTION_CONFIG,
) -> list[RegionMetrics]:
    """
    Analyze all active regions in the system.

    Returns metrics for every region that has tasks.
    """
    # Get all distinct regions with active tasks
    result = await db.execute(
        select(Task.region)
        .where(Task.region.isnot(None))
        .distinct()
    )
    regions = [row[0] for row in result.all() if row[0]]

    all_metrics = []
    for region in regions:
        metrics = await predict_region_async(db, region, config)
        all_metrics.append(metrics)

    # Update global cache expiry
    global _cache_expiry
    _cache_expiry = time.monotonic() + _CACHE_TTL_SECONDS

    return all_metrics


async def get_hotspots(
    db: AsyncSession,
    threshold: float | None = None,
    config: PredictionConfig = DEFAULT_PREDICTION_CONFIG,
) -> list[RegionMetrics]:
    """
    Identify high-risk regions above the hotspot threshold.

    Returns list sorted by risk_score descending.
    """
    all_metrics = await predict_all_regions(db, config)
    return detect_hotspots(all_metrics, threshold)


async def get_velocity_factors_for_allocation(
    db: AsyncSession,
    regions: list[str],
    config: PredictionConfig = DEFAULT_PREDICTION_CONFIG,
) -> dict[str, float]:
    """
    Compute velocity factors for a set of regions.

    Used by the allocation engine to inject crisis-aware urgency
    modifiers into the scoring pipeline.
    """
    factors: dict[str, float] = {}

    for region in regions:
        if not region:
            continue

        # Check cache first
        cached = _velocity_cache.get(region.lower())
        if cached is not None and time.monotonic() < _cache_expiry:
            factors[region] = cached
            continue

        # Compute fresh
        metrics = await predict_region_async(db, region, config)
        factors[region] = compute_urgency_modifier(metrics.risk_score)

    return factors


async def get_prediction_diagnostics(db: AsyncSession) -> dict:
    """Health diagnostics for the prediction subsystem."""
    all_metrics = await predict_all_regions(db)

    hotspots = [m for m in all_metrics if m.is_hotspot]

    return {
        "total_regions": len(all_metrics),
        "hotspots": len(hotspots),
        "cache_entries": len(_velocity_cache),
        "cache_ttl_remaining": max(0, round(_cache_expiry - time.monotonic(), 1)),
        "regions": [
            {
                "region": m.region,
                "risk_score": m.risk_score,
                "velocity": m.velocity,
                "trend": m.trend,
                "is_hotspot": m.is_hotspot,
            }
            for m in sorted(all_metrics, key=lambda x: x.risk_score, reverse=True)
        ],
    }
