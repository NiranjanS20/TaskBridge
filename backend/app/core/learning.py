"""
VASAE Adaptive Learning Core
----------------------------
PURE FUNCTIONS — no DB calls, no side effects.

Transforms override feedback into incremental fit-weight updates.

Tier-1 Hardening Extensions:
- Exponential decay for older overrides
- Confidence-scaled learning rate (prevents early overfitting)
- Max delta clamping (prevents weight explosion)
- Hybrid weight blending (global + context profiles)
- Feature vector validation
"""

from __future__ import annotations

import math
from typing import Mapping

from app.core.scoring import (
    DEFAULT_WEIGHTS,
    ScoringWeights,
    TaskScoreInput,
    VolunteerScoreInput,
    compute_skill_match,
)
from app.utils.geo import haversine_distance, proximity_score

# Fit weight keys used by adaptive learning.
FIT_FEATURE_KEYS = ("skill", "proximity", "reliability", "availability")


def extract_feature_vector(
    task: TaskScoreInput,
    volunteer: VolunteerScoreInput,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
) -> dict[str, float]:
    """
    Build a normalized feature vector for a task-volunteer pair.

    Returns keys expected by adaptive learning:
    - skill
    - proximity
    - reliability
    - availability
    """
    skill = compute_skill_match(task.required_skills, volunteer.skills)

    distance_km = haversine_distance(
        task.latitude,
        task.longitude,
        volunteer.latitude,
        volunteer.longitude,
    )
    proximity = proximity_score(distance_km, weights.max_radius_km)

    return {
        "skill": round(max(0.0, min(1.0, skill)), 6),
        "proximity": round(max(0.0, min(1.0, proximity)), 6),
        "reliability": round(max(0.0, min(1.0, volunteer.reliability)), 6),
        "availability": round(max(0.0, min(1.0, volunteer.availability)), 6),
    }


def compute_feature_delta(
    original_vector: Mapping[str, float],
    overridden_vector: Mapping[str, float],
) -> dict[str, float]:
    """
    Compute feature-wise delta for an override decision.

    delta = overridden - original
    """
    delta: dict[str, float] = {}
    for key in FIT_FEATURE_KEYS:
        delta[key] = round(
            float(overridden_vector.get(key, 0.0)) - float(original_vector.get(key, 0.0)),
            6,
        )
    return delta


def delta_magnitude(delta: Mapping[str, float]) -> float:
    """
    Compute L2 norm of a feature delta vector.

    Used as a gate to skip trivial weight updates.
    """
    return math.sqrt(sum(float(delta.get(k, 0.0)) ** 2 for k in FIT_FEATURE_KEYS))


def validate_feature_vector(vector: Mapping[str, float]) -> bool:
    """
    Validate that a feature vector has all expected keys with sane values.

    Returns True if valid, False if missing keys or NaN/Inf values.
    """
    for key in FIT_FEATURE_KEYS:
        val = vector.get(key)
        if val is None:
            return False
        fval = float(val)
        if math.isnan(fval) or math.isinf(fval):
            return False
    return True


def normalize_weights(weights: Mapping[str, float]) -> dict[str, float]:
    """
    Normalize fit weights to sum to 1.0.

    If all weights collapse to zero, falls back to equal distribution.
    """
    bounded = {k: max(0.0, float(v)) for k, v in weights.items() if k in FIT_FEATURE_KEYS}
    total = sum(bounded.values())

    if total <= 0.0:
        equal = 1.0 / len(FIT_FEATURE_KEYS)
        return {k: round(equal, 6) for k in FIT_FEATURE_KEYS}

    return {k: round(bounded[k] / total, 6) for k in FIT_FEATURE_KEYS}


def compute_confidence_factor(
    feedback_count: int,
    confidence_threshold: int = 5,
) -> float:
    """
    Compute a confidence scaling factor based on accumulated feedback.

    Prevents early overfitting by dampening the learning rate when
    feedback_count is low. The factor ramps from ~0.18 at count=1
    to ~0.93 at count=threshold, reaching 1.0 asymptotically.

    Uses: factor = 1 - exp(-feedback_count / (threshold / 3))

    Args:
        feedback_count: Total override feedbacks received so far
        confidence_threshold: Count at which learning rate is ~93% of max

    Returns:
        Scaling factor in (0.0, 1.0]
    """
    if feedback_count <= 0:
        return 0.1  # Minimum: always learn a little
    denominator = max(confidence_threshold / 3.0, 1.0)
    return 1.0 - math.exp(-feedback_count / denominator)


def compute_decayed_delta(
    delta: Mapping[str, float],
    feedback_count: int,
    decay_rate: float = 0.95,
) -> dict[str, float]:
    """
    Apply exponential decay to delta based on total feedback count.

    Earlier overrides (small feedback_count) have full influence.
    Later overrides are progressively dampened so the system
    converges instead of oscillating.

    decay = decay_rate ^ feedback_count
    """
    if feedback_count <= 0:
        decay = 1.0
    else:
        decay = decay_rate ** feedback_count

    return {
        k: round(float(delta.get(k, 0.0)) * decay, 6)
        for k in FIT_FEATURE_KEYS
    }


def clamp_delta(
    delta: Mapping[str, float],
    max_delta_per_update: float = 0.15,
) -> dict[str, float]:
    """
    Clamp per-feature delta to prevent weight explosion from a single override.

    Each feature's delta is bounded to [-max_delta, +max_delta].
    """
    return {
        k: round(max(-max_delta_per_update, min(max_delta_per_update, float(delta.get(k, 0.0)))), 6)
        for k in FIT_FEATURE_KEYS
    }


def update_weights(
    current_weights: Mapping[str, float],
    delta: Mapping[str, float],
    learning_rate: float,
    min_weight: float = 0.01,
    max_delta_per_update: float = 0.15,
    feedback_count: int = 0,
    decay_rate: float = 0.95,
    confidence_threshold: int = 5,
) -> dict[str, float]:
    """
    Apply a hardened online weight update and normalize.

    Pipeline:
    1. Clamp delta to prevent explosion
    2. Apply exponential decay based on feedback count
    3. Scale by confidence factor (prevents early overfitting)
    4. Apply learning rate
    5. Lower-bound each weight by min_weight
    6. Normalize to sum to 1.0

    Args:
        current_weights: Current fit-subweight vector
        delta: Feature-wise delta from override
        learning_rate: Base learning rate
        min_weight: Floor per feature to prevent collapse
        max_delta_per_update: Max swing per feature per update
        feedback_count: Total overrides so far (for decay + confidence)
        decay_rate: Exponential decay rate for convergence
        confidence_threshold: Feedback count for full confidence

    Returns:
        Normalized updated weight vector
    """
    # Step 1: Clamp
    clamped = clamp_delta(delta, max_delta_per_update)

    # Step 2: Decay
    decayed = compute_decayed_delta(clamped, feedback_count, decay_rate)

    # Step 3: Confidence scaling
    confidence = compute_confidence_factor(feedback_count, confidence_threshold)

    # Step 4: Apply
    updated: dict[str, float] = {}
    for key in FIT_FEATURE_KEYS:
        current = float(current_weights.get(key, 0.0))
        change = learning_rate * confidence * float(decayed.get(key, 0.0))
        updated[key] = max(min_weight, current + change)

    # Step 5: Normalize
    return normalize_weights(updated)


def blend_hybrid_weights(
    global_weights: Mapping[str, float],
    context_weights: Mapping[str, float] | None,
    global_blend: float = 0.5,
    context_blend: float = 0.5,
) -> dict[str, float]:
    """
    Blend global and context-specific weight profiles.

    final_weight[f] = global_blend * global[f] + context_blend * context[f]

    If no context weights exist, returns global weights unchanged.

    Args:
        global_weights: System-wide baseline weights
        context_weights: Category or region-specific weights (optional)
        global_blend: Weight of global profile in blend
        context_blend: Weight of context profile in blend

    Returns:
        Normalized blended weight vector
    """
    if not context_weights:
        return normalize_weights(global_weights)

    # Normalize blend ratios
    total_blend = global_blend + context_blend
    if total_blend <= 0.0:
        return normalize_weights(global_weights)

    g_ratio = global_blend / total_blend
    c_ratio = context_blend / total_blend

    blended: dict[str, float] = {}
    for key in FIT_FEATURE_KEYS:
        g_val = float(global_weights.get(key, 0.0))
        c_val = float(context_weights.get(key, 0.0))
        blended[key] = g_ratio * g_val + c_ratio * c_val

    return normalize_weights(blended)
