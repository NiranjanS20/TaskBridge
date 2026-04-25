"""
VASAE Adaptive Learning Service
-------------------------------
Service-layer orchestration for feedback-driven weight tuning.

Responsibilities:
- Persist override feedback to learning_logs
- Load/store dynamic fit weights (Redis preferred, DB fallback)
- Build effective scoring weights for allocation engine
- Hybrid weight model: global + context-specific blending
- Weight versioning with append-only audit trail
- Fire EVENT_WEIGHTS_UPDATED for downstream recomputation

Tier-1 Hardening Extensions:
- Hybrid weight model (global + category/region context)
- Confidence-scaled learning rate
- Weight versioning (version_id, source, parent linkage)
- Delta magnitude gating (skip trivial overrides)
- Event emission on weight change
- Learning metrics aggregation
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.learning import (
    FIT_FEATURE_KEYS,
    blend_hybrid_weights,
    compute_feature_delta,
    delta_magnitude,
    extract_feature_vector,
    normalize_weights,
    update_weights,
    validate_feature_vector,
)
from app.core.scoring import DEFAULT_WEIGHTS, ScoringWeights
from app.models.learning_log import AdaptiveWeight, LearningLog, WeightVersion
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

_GLOBAL_PROFILE = "global"
_REDIS_WEIGHT_PREFIX = "vasae:adaptive:fit_weights"

_redis_client = None
_redis_init_failed = False


# =====================================================================
# INTERNAL: Redis helpers
# =====================================================================

def _redis_key(profile: str) -> str:
    return f"{_REDIS_WEIGHT_PREFIX}:{profile}"


def _fit_weights_from_scoring(weights: ScoringWeights) -> dict[str, float]:
    return {
        "skill": float(weights.fit_skill),
        "proximity": float(weights.fit_proximity),
        "reliability": float(weights.fit_reliability),
        "availability": float(weights.fit_availability),
    }


def _apply_fit_weights(base: ScoringWeights, fit_weights: dict[str, float]) -> ScoringWeights:
    normalized = normalize_weights(fit_weights)
    return replace(
        base,
        fit_skill=normalized["skill"],
        fit_proximity=normalized["proximity"],
        fit_reliability=normalized["reliability"],
        fit_availability=normalized["availability"],
    )


async def _get_redis_client() -> Any | None:
    global _redis_client, _redis_init_failed

    if _redis_init_failed:
        return None
    if _redis_client is not None:
        return _redis_client

    try:
        import redis.asyncio as redis

        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        _redis_client = client
        return _redis_client
    except Exception as exc:
        _redis_init_failed = True
        logger.warning(f"Adaptive learning Redis unavailable, using DB fallback: {exc}")
        return None


# =====================================================================
# WEIGHT LOADING — Redis-first, DB fallback, profile-aware
# =====================================================================

async def _load_fit_weights_from_redis(profile: str) -> dict[str, float] | None:
    client = await _get_redis_client()
    if client is None:
        return None

    try:
        raw = await client.get(_redis_key(profile))
        if not raw:
            return None
        payload = json.loads(raw)
        if isinstance(payload, dict):
            return normalize_weights(payload)
    except Exception as exc:
        logger.warning(f"Failed to load adaptive weights from Redis [{profile}]: {exc}")

    return None


async def _store_fit_weights_in_redis(profile: str, weights: dict[str, float]) -> None:
    client = await _get_redis_client()
    if client is None:
        return

    try:
        await client.set(_redis_key(profile), json.dumps(weights))
    except Exception as exc:
        logger.warning(f"Failed to store adaptive weights in Redis [{profile}]: {exc}")


async def _load_fit_weights_from_db(
    db: AsyncSession,
    profile: str,
) -> tuple[dict[str, float] | None, int]:
    """Load weights and current version_id from DB."""
    result = await db.execute(
        select(AdaptiveWeight).where(AdaptiveWeight.profile == profile)
    )
    row = result.scalar_one_or_none()
    if not row or not isinstance(row.weights, dict):
        return None, 0

    return normalize_weights(row.weights), row.version_id


async def _store_fit_weights_in_db(
    db: AsyncSession,
    profile: str,
    weights: dict[str, float],
    source: str = "override_feedback",
    delta_applied: dict[str, float] | None = None,
    feedback_count: int = 0,
) -> int:
    """
    Persist weights with versioning.

    Returns the new version_id.
    """
    result = await db.execute(
        select(AdaptiveWeight).where(AdaptiveWeight.profile == profile)
    )
    row = result.scalar_one_or_none()

    if row is None:
        row = AdaptiveWeight(
            profile=profile,
            weights=weights,
            version_id=1,
            source=source,
        )
        db.add(row)
        new_version = 1
        parent_version = None
    else:
        parent_version = row.version_id
        new_version = parent_version + 1
        row.weights = weights
        row.version_id = new_version
        row.source = source

    # Append-only version audit trail
    version_log = WeightVersion(
        profile=profile,
        version_id=new_version,
        weights=weights,
        source=source,
        parent_version_id=parent_version,
        delta_applied=delta_applied or {},
        feedback_count_at_update=feedback_count,
    )
    db.add(version_log)

    await db.flush()
    return new_version


# =====================================================================
# FEEDBACK COUNTING
# =====================================================================

async def _get_feedback_count(db: AsyncSession) -> int:
    """Count total override feedbacks for confidence scaling."""
    result = await db.execute(select(func.count(LearningLog.id)))
    return result.scalar() or 0


async def _get_feedback_count_for_context(
    db: AsyncSession,
    category: str | None = None,
    region: str | None = None,
) -> int:
    """Count feedbacks relevant to a specific context."""
    # For now, global count. Could be extended with JOINs to task table.
    return await _get_feedback_count(db)


# =====================================================================
# PUBLIC API — Weight loading with hybrid blending
# =====================================================================

async def get_dynamic_fit_weights(
    db: AsyncSession,
    base_weights: ScoringWeights = DEFAULT_WEIGHTS,
    profile: str = _GLOBAL_PROFILE,
) -> dict[str, float]:
    """Load the latest adaptive fit weights with Redis-first strategy."""
    redis_weights = await _load_fit_weights_from_redis(profile)
    if redis_weights is not None:
        return redis_weights

    db_weights, _version = await _load_fit_weights_from_db(db, profile)
    if db_weights is not None:
        await _store_fit_weights_in_redis(profile, db_weights)
        return db_weights

    return normalize_weights(_fit_weights_from_scoring(base_weights))


async def get_effective_scoring_weights(
    db: AsyncSession,
    base_weights: ScoringWeights,
    category: str | None = None,
    region: str | None = None,
) -> ScoringWeights:
    """
    Build effective scoring weights with hybrid blending.

    Blending strategy:
    1. Load global weights
    2. Load context weights (category:X or region:Y) if available
    3. Blend: final = global_blend * global + context_blend * context
    4. Apply blended fit weights to base VAS weights

    If no context weights exist, global weights are used unchanged.
    """
    # Load global
    global_fit = await get_dynamic_fit_weights(db, base_weights, _GLOBAL_PROFILE)

    # Determine context profile key
    context_profile: str | None = None
    if category:
        context_profile = f"category:{category}"
    elif region:
        context_profile = f"region:{region}"

    # Load context weights (if context exists)
    context_fit: dict[str, float] | None = None
    if context_profile:
        context_fit = await get_dynamic_fit_weights(db, base_weights, context_profile)
        # Check if context weights are just the default (no override learned)
        default_fit = normalize_weights(_fit_weights_from_scoring(base_weights))
        if context_fit == default_fit:
            context_fit = None  # No learned context — use global only

    # Blend
    blended = blend_hybrid_weights(
        global_weights=global_fit,
        context_weights=context_fit,
        global_blend=settings.HYBRID_GLOBAL_WEIGHT,
        context_blend=settings.HYBRID_CONTEXT_WEIGHT,
    )

    return _apply_fit_weights(base_weights, blended)


async def persist_dynamic_fit_weights(
    db: AsyncSession,
    weights: dict[str, float],
    profile: str = _GLOBAL_PROFILE,
    source: str = "override_feedback",
    delta_applied: dict[str, float] | None = None,
    feedback_count: int = 0,
) -> tuple[dict[str, float], int]:
    """
    Persist dynamic fit weights with Redis preferred and DB fallback.

    Returns (normalized_weights, version_id).
    """
    normalized = normalize_weights(weights)
    await _store_fit_weights_in_redis(profile, normalized)
    version_id = await _store_fit_weights_in_db(
        db, profile, normalized, source, delta_applied, feedback_count,
    )
    return normalized, version_id


# =====================================================================
# PUBLIC API — Override feedback processing
# =====================================================================

async def record_override_feedback(
    db: AsyncSession,
    task_input,
    original_volunteer_input,
    overridden_volunteer_input,
    original_score: float,
    new_score: float,
    base_weights: ScoringWeights,
    task_category: str | None = None,
    task_region: str | None = None,
) -> dict[str, float]:
    """
    Persist override feedback and update adaptive fit weights.

    Hardened pipeline:
    1. Extract feature vectors for both assignments
    2. Validate vectors
    3. Compute delta and check magnitude gate
    4. Get feedback count for confidence scaling
    5. Apply hardened weight update (clamp + decay + confidence)
    6. Persist updated weights (global + context) with versioning
    7. Fire EVENT_WEIGHTS_UPDATED event

    Returns:
        Updated normalized fit weights (global profile).
    """
    effective_weights = await get_effective_scoring_weights(
        db, base_weights, task_category, task_region,
    )

    original_features = extract_feature_vector(
        task_input, original_volunteer_input, effective_weights,
    )
    overridden_features = extract_feature_vector(
        task_input, overridden_volunteer_input, effective_weights,
    )

    # Validate feature vectors
    if not validate_feature_vector(original_features) or not validate_feature_vector(overridden_features):
        logger.warning(
            "Skipping weight update: invalid feature vectors for task=%s",
            task_input.id[:8],
        )
        return normalize_weights(_fit_weights_from_scoring(effective_weights))

    feature_delta = compute_feature_delta(original_features, overridden_features)

    # Persist feedback log
    feedback_log = LearningLog(
        task_id=task_input.id,
        original_volunteer_id=original_volunteer_input.id,
        overridden_volunteer_id=overridden_volunteer_input.id,
        original_score=round(float(original_score), 6),
        new_score=round(float(new_score), 6),
        feature_diff=feature_delta,
        original_features=original_features,
        overridden_features=overridden_features,
    )
    db.add(feedback_log)

    # Check delta magnitude gate
    magnitude = delta_magnitude(feature_delta)
    if magnitude < settings.LEARNING_MIN_DELTA_MAGNITUDE:
        logger.info(
            "Skipping weight update: delta magnitude %.6f below threshold %.4f for task=%s",
            magnitude, settings.LEARNING_MIN_DELTA_MAGNITUDE, task_input.id[:8],
        )
        return normalize_weights(_fit_weights_from_scoring(effective_weights))

    # Get feedback count for confidence scaling
    feedback_count = await _get_feedback_count(db)

    # Update global weights
    global_fit = await get_dynamic_fit_weights(db, base_weights, _GLOBAL_PROFILE)
    updated_global = update_weights(
        current_weights=global_fit,
        delta=feature_delta,
        learning_rate=settings.LEARNING_RATE,
        max_delta_per_update=settings.LEARNING_MAX_DELTA_PER_UPDATE,
        feedback_count=feedback_count,
        decay_rate=settings.LEARNING_DECAY_RATE,
        confidence_threshold=settings.LEARNING_CONFIDENCE_THRESHOLD,
    )
    updated_global, global_version = await persist_dynamic_fit_weights(
        db, updated_global, _GLOBAL_PROFILE, "override_feedback", feature_delta, feedback_count,
    )

    # Update context weights if category or region available
    context_profile: str | None = None
    if task_category:
        context_profile = f"category:{task_category}"
    elif task_region:
        context_profile = f"region:{task_region}"

    if context_profile:
        context_fit = await get_dynamic_fit_weights(db, base_weights, context_profile)
        updated_context = update_weights(
            current_weights=context_fit,
            delta=feature_delta,
            learning_rate=settings.LEARNING_RATE,
            max_delta_per_update=settings.LEARNING_MAX_DELTA_PER_UPDATE,
            feedback_count=feedback_count,
            decay_rate=settings.LEARNING_DECAY_RATE,
            confidence_threshold=settings.LEARNING_CONFIDENCE_THRESHOLD,
        )
        await persist_dynamic_fit_weights(
            db, updated_context, context_profile, "override_feedback", feature_delta, feedback_count,
        )

    logger.info(
        "Adaptive learning update: task=%s original=%s overridden=%s "
        "delta_magnitude=%.6f feedback_count=%d global_version=%d "
        "updated_fit=%s context=%s",
        task_input.id[:8],
        original_volunteer_input.id[:8],
        overridden_volunteer_input.id[:8],
        magnitude,
        feedback_count,
        global_version,
        updated_global,
        context_profile,
    )

    # Fire weight update event for downstream reallocation
    try:
        from app.events.event_dispatcher import publish, EVENT_WEIGHTS_UPDATED
        await publish(EVENT_WEIGHTS_UPDATED, {
            "profile": _GLOBAL_PROFILE,
            "version_id": global_version,
            "context_profile": context_profile,
            "source": "override_feedback",
        })
    except Exception as exc:
        logger.warning(f"Failed to emit EVENT_WEIGHTS_UPDATED: {exc}")

    return updated_global


# =====================================================================
# PUBLIC API — Learning metrics
# =====================================================================

async def get_learning_metrics(db: AsyncSession) -> dict:
    """
    Aggregate learning system metrics for observability.

    Returns:
        Dict with current weights, versions, feedback stats, and health info.
    """
    # Global weights
    global_result = await db.execute(
        select(AdaptiveWeight).where(AdaptiveWeight.profile == _GLOBAL_PROFILE)
    )
    global_row = global_result.scalar_one_or_none()

    # All profiles
    all_profiles_result = await db.execute(select(AdaptiveWeight))
    all_profiles = list(all_profiles_result.scalars().all())

    # Feedback count
    feedback_count = await _get_feedback_count(db)

    # Recent weight versions
    recent_versions_result = await db.execute(
        select(WeightVersion)
        .order_by(WeightVersion.created_at.desc())
        .limit(10)
    )
    recent_versions = list(recent_versions_result.scalars().all())

    # Recent learning logs
    recent_logs_result = await db.execute(
        select(LearningLog)
        .order_by(LearningLog.timestamp.desc())
        .limit(5)
    )
    recent_logs = list(recent_logs_result.scalars().all())

    from app.core.learning import compute_confidence_factor
    confidence = compute_confidence_factor(
        feedback_count, settings.LEARNING_CONFIDENCE_THRESHOLD,
    )

    return {
        "global_weights": {
            "weights": global_row.weights if global_row else None,
            "version_id": global_row.version_id if global_row else 0,
            "source": global_row.source if global_row else "default",
            "updated_at": str(global_row.updated_at) if global_row else None,
        },
        "all_profiles": [
            {
                "profile": p.profile,
                "weights": p.weights,
                "version_id": p.version_id,
                "source": p.source,
            }
            for p in all_profiles
        ],
        "feedback_stats": {
            "total_overrides": feedback_count,
            "confidence_factor": round(confidence, 4),
            "learning_rate": settings.LEARNING_RATE,
            "effective_learning_rate": round(settings.LEARNING_RATE * confidence, 6),
            "decay_rate": settings.LEARNING_DECAY_RATE,
        },
        "recent_versions": [
            {
                "profile": v.profile,
                "version_id": v.version_id,
                "source": v.source,
                "parent_version_id": v.parent_version_id,
                "feedback_count_at_update": v.feedback_count_at_update,
                "delta_applied": v.delta_applied,
                "created_at": str(v.created_at),
            }
            for v in recent_versions
        ],
        "recent_overrides": [
            {
                "task_id": log.task_id,
                "original_volunteer_id": log.original_volunteer_id,
                "overridden_volunteer_id": log.overridden_volunteer_id,
                "score_delta": round(log.new_score - log.original_score, 6),
                "feature_diff": log.feature_diff,
                "timestamp": str(log.timestamp),
            }
            for log in recent_logs
        ],
    }
