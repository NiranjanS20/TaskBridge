"""
VASAE Celery Worker Configuration
----------------------------------
Celery app with Redis broker.
Falls back gracefully if Redis is unavailable.
"""

from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from celery import Celery
    from app.config import get_settings

    settings = get_settings()

    celery_app = Celery(
        "vasae_worker",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        worker_prefetch_multiplier=1,
    )

    CELERY_AVAILABLE = True
    logger.info("Celery worker configured successfully")

except ImportError:
    celery_app = None
    CELERY_AVAILABLE = False
    logger.warning("Celery not available — running in synchronous mode")
except Exception as e:
    celery_app = None
    CELERY_AVAILABLE = False
    logger.warning(f"Celery initialization failed: {e} — running in synchronous mode")
