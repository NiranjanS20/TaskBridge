"""
VASAE Prediction API Routes
----------------------------
Regional crisis velocity, trend analysis, hotspot detection,
and forecasting endpoints.

Endpoints:
- GET /predict/{region}       — Full prediction for a single region
- GET /predict/all            — Analyze all active regions
- GET /predict/hotspots       — High-risk regions above threshold
- GET /predict/diagnostics    — Prediction subsystem health
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.task import Task
from app.services.prediction_service import (
    predict_region,
    predict_region_async,
    predict_all_regions,
    get_hotspots,
    get_prediction_diagnostics,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/predict", tags=["Prediction"])


@router.get("/all")
async def get_all_predictions(
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze all active regions in the system.

    Returns velocity, trend, risk score, and forecast for every
    region that has tasks in the database.
    """
    metrics = await predict_all_regions(db)

    return {
        "total_regions": len(metrics),
        "regions": [
            {
                "region": m.region,
                "velocity": m.velocity,
                "trend": m.trend,
                "growth_rate": m.growth_rate,
                "rolling_average": m.rolling_average,
                "task_density": m.task_density,
                "risk_score": m.risk_score,
                "predicted_tasks_24h": m.predicted_tasks_24h,
                "confidence": m.confidence,
                "is_hotspot": m.is_hotspot,
            }
            for m in metrics
        ],
    }


@router.get("/hotspots")
async def get_hotspot_regions(
    threshold: float = Query(default=0.65, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    """
    Identify high-risk regions above the hotspot threshold.

    Returns regions sorted by risk_score descending.
    These regions should receive priority allocation and
    pre-positioning of volunteers.
    """
    hotspots = await get_hotspots(db, threshold)

    return {
        "threshold": threshold,
        "hotspot_count": len(hotspots),
        "hotspots": [
            {
                "region": m.region,
                "risk_score": m.risk_score,
                "velocity": m.velocity,
                "trend": m.trend,
                "predicted_tasks_24h": m.predicted_tasks_24h,
                "task_density": m.task_density,
                "confidence": m.confidence,
            }
            for m in hotspots
        ],
    }


@router.get("/diagnostics")
async def prediction_diagnostics(
    db: AsyncSession = Depends(get_db),
):
    """Prediction subsystem health and cache status."""
    return await get_prediction_diagnostics(db)


@router.get("/heat")
async def prediction_heatmap(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Region heat layer payload for map visualization.
    """
    region_query = select(Task.region).where(Task.region.isnot(None))
    if current_user.ngo_id:
        region_query = region_query.where(Task.ngo_id == current_user.ngo_id)
    region_query = region_query.distinct()
    region_result = await db.execute(region_query)
    regions = [row[0] for row in region_result.all() if row[0]]
    metrics = [await predict_region_async(db, region) for region in regions]
    coords_query = (
        select(
            Task.region,
            func.avg(Task.latitude).label("lat"),
            func.avg(Task.longitude).label("lon"),
        )
        .where(Task.region.isnot(None))
        .group_by(Task.region)
    )
    if current_user.ngo_id:
        coords_query = coords_query.where(Task.ngo_id == current_user.ngo_id)
    coords_result = await db.execute(coords_query)
    coord_map = {
        row[0]: {"latitude": float(row[1] or 0.0), "longitude": float(row[2] or 0.0)}
        for row in coords_result.all()
        if row[0]
    }
    points = []
    for m in metrics:
        coords = coord_map.get(m.region)
        if not coords:
            continue
        points.append(
            {
                "region": m.region,
                "latitude": coords["latitude"],
                "longitude": coords["longitude"],
                "risk_score": m.risk_score,
                "predicted_tasks_24h": m.predicted_tasks_24h,
                "trend": m.trend,
            }
        )
    return {"points": points}


@router.get("/{region}")
async def get_prediction(
    region: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Full prediction for a single region.

    Returns:
    - velocity: task arrival rate (tasks/hour)
    - trend: increasing | stable | decreasing
    - growth_rate: percentage change over window
    - risk_score: composite risk [0.0 - 1.0]
    - predicted_tasks_24h: forecasted new tasks
    - is_hotspot: whether region exceeds risk threshold
    """
    try:
        metrics = await predict_region_async(db, region)
    except Exception:
        logger.exception("Prediction failed for region '%s'", region)
        return {
            "region": region,
            "predicted_tasks": 0,
            "risk_score": 0,
            "trend": "unknown",
        }

    return {
        "region": metrics.region,
        "velocity": metrics.velocity,
        "trend": metrics.trend,
        "growth_rate": metrics.growth_rate,
        "rolling_average": metrics.rolling_average,
        "task_density": metrics.task_density,
        "risk_score": metrics.risk_score,
        "predicted_tasks_24h": metrics.predicted_tasks_24h,
        "confidence": metrics.confidence,
        "is_hotspot": metrics.is_hotspot,
    }
