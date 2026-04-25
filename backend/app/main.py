"""
VASAE Backend — FastAPI Application Entrypoint
----------------------------------------------
Initializes the application, registers routes, sets up CORS,
and bootstraps the database and event system on startup.

Tier-1/2 Extensions:
- Health diagnostics for learning, queue, prediction, and lock subsystems
- EVENT_WEIGHTS_UPDATED handler for downstream reallocation
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import init_db, get_db
from app.api.router import api_router
from app.events.event_dispatcher import (
    subscribe,
    EVENT_NEW_TASK,
    EVENT_VOLUNTEER_UPDATE,
    EVENT_WEIGHTS_UPDATED,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


# =====================================================================
# APPLICATION LIFECYCLE
# =====================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    # --- Startup ---
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Initialize database tables
    await init_db()

    logger.info("Event handlers registered via event_dispatcher defaults")
    logger.info(f"CORS origins: {settings.CORS_ORIGINS}")
    logger.info("Application startup complete")

    yield

    # --- Shutdown ---
    logger.info("Application shutdown complete")


# =====================================================================
# APPLICATION FACTORY
# =====================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "VASAE — Volunteer Allocation System with AI Engine. "
        "Real-time, event-driven decision engine with adaptive learning, "
        "predictive crisis intelligence, fairness, and explainability."
    ),
    lifespan=lifespan,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
app.include_router(api_router)


# =====================================================================
# HEALTH & DIAGNOSTICS ENDPOINTS
# =====================================================================

@app.get("/health", tags=["System"])
async def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/health/learning", tags=["System"])
async def health_learning(db: AsyncSession = Depends(get_db)):
    """Adaptive learning subsystem diagnostics."""
    from app.services.learning_service import get_learning_metrics

    metrics = await get_learning_metrics(db)
    return {
        "status": "healthy",
        "subsystem": "adaptive_learning",
        "global_weights": metrics.get("global_weights"),
        "feedback_stats": metrics.get("feedback_stats"),
        "profiles_count": len(metrics.get("all_profiles", [])),
    }


@app.get("/health/queue", tags=["System"])
async def health_queue():
    """Priority queue subsystem diagnostics."""
    from app.core.priority_queue import TaskPriorityQueue

    queue = TaskPriorityQueue()
    diag = await queue.diagnostics()
    return {
        "status": "healthy",
        "subsystem": "priority_queue",
        **diag,
    }


@app.get("/health/locks", tags=["System"])
async def health_locks():
    """Volunteer lock manager diagnostics."""
    from app.utils.locks import VolunteerLockManager

    lock_mgr = VolunteerLockManager()
    diag = await lock_mgr.diagnostics()
    return {
        "status": "healthy",
        "subsystem": "lock_manager",
        **diag,
    }


@app.get("/health/prediction", tags=["System"])
async def health_prediction(db: AsyncSession = Depends(get_db)):
    """Prediction engine diagnostics."""
    from app.services.prediction_service import get_prediction_diagnostics

    diag = await get_prediction_diagnostics(db)
    return {
        "status": "healthy",
        "subsystem": "prediction_engine",
        **diag,
    }


@app.get("/health/events", tags=["System"])
async def health_events():
    """Event aggregator diagnostics."""
    from app.events.event_dispatcher import get_aggregator

    aggregator = get_aggregator()
    diag = await aggregator.diagnostics()
    return {
        "status": "healthy",
        "subsystem": "event_aggregator",
        **diag,
    }


@app.get("/health/full", tags=["System"])
async def health_full(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive system health across all subsystems.

    Single call to check everything.
    """
    from app.services.learning_service import get_learning_metrics
    from app.core.priority_queue import TaskPriorityQueue
    from app.utils.locks import VolunteerLockManager
    from app.events.event_dispatcher import get_aggregator
    from app.services.prediction_service import get_prediction_diagnostics

    learning_metrics = await get_learning_metrics(db)
    queue_diag = await TaskPriorityQueue().diagnostics()
    lock_diag = await VolunteerLockManager().diagnostics()
    event_diag = await get_aggregator().diagnostics()
    pred_diag = await get_prediction_diagnostics(db)

    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "subsystems": {
            "adaptive_learning": {
                "global_version": learning_metrics.get("global_weights", {}).get("version_id", 0),
                "total_overrides": learning_metrics.get("feedback_stats", {}).get("total_overrides", 0),
                "confidence_factor": learning_metrics.get("feedback_stats", {}).get("confidence_factor", 0),
            },
            "priority_queue": queue_diag,
            "lock_manager": lock_diag,
            "event_aggregator": event_diag,
            "prediction_engine": {
                "total_regions": pred_diag.get("total_regions", 0),
                "hotspots": pred_diag.get("hotspots", 0),
                "cache_entries": pred_diag.get("cache_entries", 0),
            },
        },
    }
