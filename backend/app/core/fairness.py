"""
VASAE Fairness Engine
---------------------
PURE FUNCTIONS — no DB calls, no side effects.

Implements:
1. Gini coefficient — measures task distribution equality
2. Conflict resolution — urgency > waiting_time > cluster_size
3. Graceful degradation — relax constraints when no match found
4. Burnout checks — auto-rest recommendation
"""

from dataclasses import dataclass
from app.utils.logger import get_logger

logger = get_logger(__name__)


# =====================================================================
# GINI COEFFICIENT — Fairness metric for task distribution
# =====================================================================

def gini_coefficient(assignment_counts: list[int]) -> float:
    """
    Compute the Gini coefficient for task distribution across volunteers.

    0.0 = perfectly equal distribution
    1.0 = maximally unequal (one volunteer has all tasks)

    Args:
        assignment_counts: List of total_assignments per volunteer

    Returns:
        Gini coefficient [0.0, 1.0]
    """
    if not assignment_counts or len(assignment_counts) < 2:
        return 0.0

    sorted_counts = sorted(assignment_counts)
    n = len(sorted_counts)
    total = sum(sorted_counts)

    if total == 0:
        return 0.0

    # Gini formula using sorted array
    cumulative = 0.0
    for i, count in enumerate(sorted_counts):
        cumulative += (2 * (i + 1) - n - 1) * count

    return cumulative / (n * total)


# =====================================================================
# CONFLICT RESOLUTION — Deterministic tiebreaking
# =====================================================================

@dataclass(frozen=True)
class ConflictInput:
    """Data needed for conflict resolution."""
    task_id: str
    urgency: int
    waiting_time_minutes: float
    cluster_size: int  # Number of nearby tasks (density)


def resolve_conflict(tasks: list[ConflictInput]) -> list[ConflictInput]:
    """
    Sort tasks by allocation priority.

    Resolution order (strict):
    1. Urgency (higher = first)
    2. Waiting time (longer = first)
    3. Cluster size (larger = first, more people affected)

    Args:
        tasks: List of conflicting tasks competing for same volunteer

    Returns:
        Tasks sorted by priority (highest priority first)
    """
    return sorted(
        tasks,
        key=lambda t: (t.urgency, t.waiting_time_minutes, t.cluster_size),
        reverse=True,
    )


# =====================================================================
# GRACEFUL DEGRADATION — Relaxing constraints when no match
# =====================================================================

@dataclass
class DegradationState:
    """Tracks how far constraints have been relaxed."""
    skill_relaxed: bool = False
    radius_expanded_km: float = 0.0
    escalated: bool = False
    mode: str = "standard"  # standard | degraded_skill | degraded_radius | escalated


def compute_degradation(
    match_found: bool,
    current_state: DegradationState,
    radius_step_km: float = 10.0,
    max_radius_km: float = 100.0,
) -> DegradationState:
    """
    Determine next degradation step when no match is found.

    Degradation ladder:
    1. Standard (full constraints)
    2. Relax skill requirements
    3. Expand search radius (in steps)
    4. Escalate to admin

    Args:
        match_found: Whether a match was found in current state
        current_state: Current degradation state
        radius_step_km: How much to expand radius each step
        max_radius_km: Maximum expanded radius before escalation

    Returns:
        Updated DegradationState
    """
    if match_found:
        return current_state

    # Step 1: Relax skills
    if not current_state.skill_relaxed:
        logger.info("Degradation: relaxing skill constraints")
        return DegradationState(
            skill_relaxed=True,
            mode="degraded_skill",
        )

    # Step 2: Expand radius
    new_radius = current_state.radius_expanded_km + radius_step_km
    if new_radius <= max_radius_km:
        logger.info(f"Degradation: expanding radius to {new_radius}km")
        return DegradationState(
            skill_relaxed=True,
            radius_expanded_km=new_radius,
            mode="degraded_radius",
        )

    # Step 3: Escalate
    logger.warning("Degradation: escalating to admin — all constraints exhausted")
    return DegradationState(
        skill_relaxed=True,
        radius_expanded_km=new_radius,
        escalated=True,
        mode="escalated",
    )


# =====================================================================
# BURNOUT CHECKS
# =====================================================================

def should_rest(burnout_score: float, threshold: float = 0.70) -> bool:
    """
    Determine if a volunteer should be auto-rested.

    Args:
        burnout_score: Current burnout level 0.0–1.0
        threshold: Cutoff above which rest is mandatory

    Returns:
        True if volunteer should be marked unavailable
    """
    return burnout_score >= threshold


def compute_burnout_increment(
    current_burnout: float,
    task_complexity: int,
    hours_since_last_rest: float = 0.0,
) -> float:
    """
    Compute burnout increase from completing a task.

    Burnout increases based on:
    - Task complexity (harder tasks = more burnout)
    - Time since last rest (fatigue accumulation)

    Args:
        current_burnout: Current burnout score
        task_complexity: 1–10
        hours_since_last_rest: Hours of continuous work

    Returns:
        New burnout score clamped to [0.0, 1.0]
    """
    # Base increment: 1-5% per task depending on complexity
    base_increment = (task_complexity / 10.0) * 0.05

    # Fatigue multiplier: increases after 8 hours
    fatigue_mult = 1.0 + max(0, hours_since_last_rest - 8.0) * 0.1

    increment = base_increment * fatigue_mult
    new_burnout = min(1.0, current_burnout + increment)

    logger.debug(
        f"Burnout: {current_burnout:.2f} + {increment:.4f} = {new_burnout:.2f} "
        f"(complexity={task_complexity}, hours={hours_since_last_rest:.1f})"
    )

    return round(new_burnout, 4)
