"""
VASAE Database Session
----------------------
Async engine + session factory.
Provides the get_db dependency for FastAPI route injection.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from typing import AsyncGenerator

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# --- Engine ---
# echo=True in debug mode for SQL tracing
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

# --- Session Factory ---
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async DB session.
    Automatically commits on success, rolls back on exception.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Create all tables. Called once at startup.
    In production, use Alembic migrations instead.
    """
    from app.db.base import Base
    # Import all models so they register with Base.metadata
    import app.models.task       # noqa: F401
    import app.models.volunteer  # noqa: F401
    import app.models.assignment # noqa: F401
    import app.models.audit      # noqa: F401
    import app.models.learning_log  # noqa: F401 — LearningLog, AdaptiveWeight, WeightVersion
    import app.models.volunteer_metrics  # noqa: F401
    import app.models.organization  # noqa: F401
    import app.models.user  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
