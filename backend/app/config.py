"""
VASAE Configuration Module
--------------------------
Centralized settings using pydantic-settings.
Loads from .env with sensible defaults for local dev.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings — loaded from environment variables."""

    # --- Application ---
    APP_NAME: str = "TASKBRIDGE Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-taskbridge-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # --- Database ---
    # Default: PostgreSQL for production.
    DATABASE_URL: str = "postgresql+asyncpg://postgres:Vedant_2405@localhost:5432/resource_alloc_db"

    @field_validator("DATABASE_URL")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """
        Ensure PostgreSQL URLs use the asyncpg driver expected by create_async_engine.
        Accepts postgres:// and postgresql:// in env files for convenience.
        """
        db_url = value.strip()
        if db_url.startswith("postgres://"):
            return db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        if db_url.startswith("postgresql://"):
            return db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if db_url.startswith("postgresql+psycopg2://"):
            return db_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        return db_url

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Celery ---
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # --- VAS Scoring Weights (tunable) ---
    VAS_K1: float = 0.20   # Inverse task complexity weight
    VAS_K2: float = 0.25   # Waiting time weight
    VAS_K3: float = 0.30   # Urgency weight
    VAS_K4: float = 0.25   # Volunteer fit weight

    # --- Volunteer Fit Sub-weights ---
    FIT_SKILL_WEIGHT: float = 0.35
    FIT_PROXIMITY_WEIGHT: float = 0.25
    FIT_RELIABILITY_WEIGHT: float = 0.25
    FIT_AVAILABILITY_WEIGHT: float = 0.15

    # --- Thresholds ---
    BURNOUT_THRESHOLD: float = 0.70    # Auto-rest above this
    BURNOUT_RISK_ASSIGNMENT_THRESHOLD: float = 0.85  # Lifecycle burnout-risk guard
    MAX_SEARCH_RADIUS_KM: float = 50.0 # Max volunteer search radius
    DEGRADATION_RADIUS_STEP_KM: float = 10.0  # Radius expansion step

    # --- Adaptive Learning ---
    LEARNING_RATE: float = 0.08
    LEARNING_MAX_DELTA_PER_UPDATE: float = 0.15       # Clamp per-update weight swing
    LEARNING_DECAY_RATE: float = 0.95                  # Exponential decay for older overrides
    LEARNING_MIN_DELTA_MAGNITUDE: float = 0.01         # Skip trivial deltas
    LEARNING_CONFIDENCE_THRESHOLD: int = 5             # Min overrides before full learning rate

    # --- Hybrid Weight Model ---
    HYBRID_GLOBAL_WEIGHT: float = 0.5                  # Blend ratio: global vs context
    HYBRID_CONTEXT_WEIGHT: float = 0.5                 # Blend ratio: context vs global

    # --- Real-time Allocation ---
    REALTIME_QUEUE_KEY: str = "taskbridge:allocation:priority_queue"
    VOLUNTEER_LOCK_TTL_SECONDS: int = 30
    LOCK_RETRY_ATTEMPTS: int = 2
    RETRY_PRIORITY_BOOST_BASE: float = 1.0             # Base priority boost per retry
    RETRY_PRIORITY_BOOST_FACTOR: float = 1.5           # Exponential factor per retry

    # --- Event Aggregation ---
    DEBOUNCE_MIN_SECONDS: float = 0.3                  # Adaptive debounce floor
    DEBOUNCE_MAX_SECONDS: float = 1.0                  # Adaptive debounce ceiling
    DEBOUNCE_LOAD_THRESHOLD: int = 10                  # Events/sec triggering max debounce
    ALLOCATION_CYCLE_LOCK_TTL: int = 60                # Global cycle lock TTL

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://127.0.0.1:8002"

    def get_cors_origins(self) -> list[str]:
        """Convert CORS_ORIGINS string to list."""
        if not self.CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # --- LLM Integrations ---
    GEMINI_API_KEY: str = "AIzaSyAFZIZFZDlvGv6GitC9KOpWXxPSWoor2G4"
    GROQ_API_KEY: str = "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"
    CHAT_LLM_PROVIDER: str = "gemini"  # gemini | groq

    model_config = {
        "env_file": "app/.env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
