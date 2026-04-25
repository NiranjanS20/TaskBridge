"""
VASAE Scoring Engine
--------------------
PURE FUNCTIONS — no DB calls, no side effects.

Implements the VAS (Volunteer Allocation Score) formula:

    VAS = (K1 / complexity) + (K2 * waiting_time_norm) + (K3 * urgency_norm) + (K4 * volunteer_fit)

    VolunteerFit = 0.35 * SkillMatch
                 + 0.25 * Proximity
                 + 0.25 * Reliability
                 + 0.15 * Availability

Modifiers:
    - Burnout:  fit * (1 - burnout_score)
    - Crisis:   urgency * (1 + velocity_factor)

All inputs are pre-normalized to [0, 1] before entering these functions.
"""

from dataclasses import dataclass, replace
from app.core.skill_matching import compute_skill_similarity
from app.utils.geo import haversine_distance, proximity_score
from app.utils.logger import get_logger

logger = get_logger(__name__)


# =====================================================================
# DATA CONTRACTS — Pure input/output structures for the scoring engine
# =====================================================================

@dataclass(frozen=True)
class TaskScoreInput:
    """Immutable task data needed for scoring."""
    id: str
    required_skills: list[str]
    urgency: int           # 1–5
    complexity: int        # 1–10
    latitude: float
    longitude: float
    waiting_time_minutes: float
    team_size: int = 1
    region: str | None = None


@dataclass(frozen=True)
class VolunteerScoreInput:
    """Immutable volunteer data needed for scoring."""
    id: str
    name: str
    skills: list[str]
    latitude: float
    longitude: float
    availability: float    # 0.0–1.0
    reliability: float     # 0.0–1.0
    burnout_score: float   # 0.0–1.0
    engagement_score: float = 0.5
    burnout_risk: float = 0.0
    total_assignments: int = 0
    active_assignments: int = 0


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of all scoring factors."""
    skill_match: float
    proximity: float
    reliability: float
    availability: float
    engagement_score: float
    burnout_risk: float
    volunteer_fit_raw: float
    burnout_adjustment: float
    volunteer_fit_adjusted: float
    complexity_component: float
    waiting_time_component: float
    urgency_component: float
    fit_component: float
    final_vas_score: float


# =====================================================================
# WEIGHTS — configurable, injected from settings
# =====================================================================

@dataclass(frozen=True)
class ScoringWeights:
    """All tunable weights for the VAS formula."""
    k1: float = 0.20
    k2: float = 0.25
    k3: float = 0.30
    k4: float = 0.25
    fit_skill: float = 0.35
    fit_proximity: float = 0.25
    fit_reliability: float = 0.25
    fit_availability: float = 0.15
    max_radius_km: float = 50.0
    max_waiting_minutes: float = 480.0  # 8 hours normalization ceiling


DEFAULT_WEIGHTS = ScoringWeights()
FIT_COMPONENT_KEYS = ("skill", "proximity", "reliability", "availability")


def get_fit_weight_vector(weights: ScoringWeights) -> dict[str, float]:
    """Return fit-subweight vector in adaptive-learning key format."""
    return {
        "skill": float(weights.fit_skill),
        "proximity": float(weights.fit_proximity),
        "reliability": float(weights.fit_reliability),
        "availability": float(weights.fit_availability),
    }


def normalize_fit_weight_vector(vector: dict[str, float]) -> dict[str, float]:
    """Normalize fit-subweights to sum to 1.0 with equal fallback."""
    bounded = {k: max(0.0, float(vector.get(k, 0.0))) for k in FIT_COMPONENT_KEYS}
    total = sum(bounded.values())
    if total <= 0.0:
        equal = 1.0 / len(FIT_COMPONENT_KEYS)
        return {k: equal for k in FIT_COMPONENT_KEYS}
    return {k: bounded[k] / total for k in FIT_COMPONENT_KEYS}


def apply_dynamic_fit_weights(
    base_weights: ScoringWeights,
    dynamic_fit_weights: dict[str, float] | None,
) -> ScoringWeights:
    """
    Merge dynamic fit-subweights into a scoring profile.

    If no learned profile exists, returns base_weights unchanged.
    """
    if not dynamic_fit_weights:
        return base_weights

    normalized = normalize_fit_weight_vector(dynamic_fit_weights)
    return replace(
        base_weights,
        fit_skill=normalized["skill"],
        fit_proximity=normalized["proximity"],
        fit_reliability=normalized["reliability"],
        fit_availability=normalized["availability"],
    )


# =====================================================================
# CORE FUNCTIONS — Pure, deterministic, no IO
# =====================================================================

def compute_skill_match(
    required: list[str],
    available: list[str],
) -> float:
    """
    Jaccard-style skill overlap normalized to [0, 1].

    If no skills required, any volunteer gets 1.0 (universal match).
    """
    if not required:
        return 1.0
    if not available:
        return 0.0

    return compute_skill_similarity(" ".join(required), available)


def compute_volunteer_fit(
    task: TaskScoreInput,
    volunteer: VolunteerScoreInput,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
) -> tuple[float, dict[str, float]]:
    """
    Compute the multi-dimensional volunteer fit score.

    VolunteerFit = w_skill * SkillMatch
                 + w_prox  * Proximity
                 + w_rel   * Reliability
                 + w_avail * Availability

    Then apply burnout modifier: fit * (1 - burnout_score)

    Args:
        task: Immutable task data
        volunteer: Immutable volunteer data
        weights: Tunable scoring weights

    Returns:
        (adjusted_fit, factor_dict) where factor_dict has all sub-scores
    """
    # --- Sub-scores ---
    skill = compute_skill_match(task.required_skills, volunteer.skills)

    distance_km = haversine_distance(
        task.latitude, task.longitude,
        volunteer.latitude, volunteer.longitude,
    )
    prox = proximity_score(distance_km, weights.max_radius_km)

    rel = max(0.0, min(1.0, volunteer.reliability))
    avail = max(0.0, min(1.0, volunteer.availability))
    engagement = max(0.0, min(1.0, volunteer.engagement_score))
    burnout_risk = max(0.0, min(1.0, volunteer.burnout_risk))

    # --- Weighted combination ---
    fit_raw = (
        weights.fit_skill * skill
        + weights.fit_proximity * prox
        + weights.fit_reliability * rel
        + weights.fit_availability * avail
    )
    # Lifecycle intelligence adjustments:
    # positive engagement weight, negative burnout-risk weight.
    fit_raw += 0.10 * engagement
    fit_raw -= 0.10 * burnout_risk
    fit_raw = max(0.0, min(1.0, fit_raw))

    # --- Burnout modifier ---
    burnout_adj = 1.0 - max(volunteer.burnout_score, burnout_risk)
    fit_adjusted = fit_raw * burnout_adj

    factors = {
        "skill_match": round(skill, 4),
        "proximity": round(prox, 4),
        "reliability": round(rel, 4),
        "availability": round(avail, 4),
        "engagement_score": round(engagement, 4),
        "burnout_risk": round(burnout_risk, 4),
        "volunteer_fit_raw": round(fit_raw, 4),
        "burnout_adjustment": round(burnout_adj, 4),
        "volunteer_fit_adjusted": round(fit_adjusted, 4),
        "distance_km": round(distance_km, 2),
    }

    return fit_adjusted, factors


def compute_vas(
    task: TaskScoreInput,
    volunteer: VolunteerScoreInput,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
    velocity_factor: float = 0.0,
) -> ScoreBreakdown:
    """
    Compute the full VAS (Volunteer Allocation Score).

    VAS = (K1 / complexity_norm) + (K2 * waiting_norm) + (K3 * urgency_norm) + (K4 * fit)

    Modifiers:
        - Crisis velocity applied to urgency component
        - Burnout already applied inside volunteer_fit

    Args:
        task: Immutable task data
        volunteer: Immutable volunteer data
        weights: Tunable scoring weights
        velocity_factor: Crisis velocity modifier (0.0 = normal)

    Returns:
        Full ScoreBreakdown with all intermediate values
    """
    # --- Volunteer Fit (includes burnout) ---
    fit_adjusted, factors = compute_volunteer_fit(task, volunteer, weights)

    # --- Normalize inputs to [0, 1] ---
    # Complexity: inverted — lower complexity = higher score
    complexity_norm = max(task.complexity, 1) / 10.0
    complexity_component = weights.k1 * (1.0 / complexity_norm) / 10.0  # scale to ~0.02-0.2

    # Waiting time: capped at max_waiting_minutes
    waiting_norm = min(task.waiting_time_minutes, weights.max_waiting_minutes) / weights.max_waiting_minutes
    waiting_component = weights.k2 * waiting_norm

    # Urgency: normalized 1-5 → 0.2-1.0, with crisis velocity
    urgency_norm = task.urgency / 5.0
    urgency_with_velocity = urgency_norm * (1.0 + velocity_factor)
    urgency_component = weights.k3 * min(urgency_with_velocity, 1.0)

    # Fit component
    fit_component = weights.k4 * fit_adjusted

    # --- Final VAS ---
    final_score = (
        complexity_component
        + waiting_component
        + urgency_component
        + fit_component
    )

    return ScoreBreakdown(
        skill_match=factors["skill_match"],
        proximity=factors["proximity"],
        reliability=factors["reliability"],
        availability=factors["availability"],
        engagement_score=factors["engagement_score"],
        burnout_risk=factors["burnout_risk"],
        volunteer_fit_raw=factors["volunteer_fit_raw"],
        burnout_adjustment=factors["burnout_adjustment"],
        volunteer_fit_adjusted=factors["volunteer_fit_adjusted"],
        complexity_component=round(complexity_component, 6),
        waiting_time_component=round(waiting_component, 6),
        urgency_component=round(urgency_component, 6),
        fit_component=round(fit_component, 6),
        final_vas_score=round(final_score, 6),
    )
