"""
VASAE Matching Engine
---------------------
PURE FUNCTIONS — no DB calls, no side effects.

Takes a task and a pool of volunteers, scores every pair,
and returns a ranked list of candidates.

Supports:
- Single-volunteer matching (team_size=1)
- Multi-volunteer matching (team_size>1)
- Filtering by deployability
"""

from dataclasses import dataclass
from app.core.scoring import (
    TaskScoreInput,
    VolunteerScoreInput,
    ScoreBreakdown,
    ScoringWeights,
    DEFAULT_WEIGHTS,
    compute_vas,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MatchCandidate:
    """A scored volunteer candidate for a specific task."""
    volunteer: VolunteerScoreInput
    breakdown: ScoreBreakdown
    rank: int = 0


@dataclass
class MatchResult:
    """Complete matching result for a single task."""
    task: TaskScoreInput
    chosen: list[MatchCandidate]       # Top N (where N = team_size)
    alternatives: list[MatchCandidate]  # Runner-ups for explainability
    total_candidates: int
    match_found: bool


def rank_volunteers(
    task: TaskScoreInput,
    volunteers: list[VolunteerScoreInput],
    weights: ScoringWeights = DEFAULT_WEIGHTS,
    velocity_factor: float = 0.0,
) -> list[MatchCandidate]:
    """
    Score and rank ALL volunteers for a given task.

    Returns sorted list (highest VAS first) with full breakdowns.
    This is the raw ranking — no filtering or selection applied.

    Args:
        task: The task to match against
        volunteers: Pool of candidate volunteers
        weights: Tunable scoring weights
        velocity_factor: Crisis velocity modifier

    Returns:
        Sorted list of MatchCandidates (descending VAS score)
    """
    candidates: list[MatchCandidate] = []

    for vol in volunteers:
        breakdown = compute_vas(task, vol, weights, velocity_factor)
        candidates.append(MatchCandidate(volunteer=vol, breakdown=breakdown))

    # Sort by final VAS score descending
    candidates.sort(key=lambda c: c.breakdown.final_vas_score, reverse=True)

    # Assign ranks
    for i, candidate in enumerate(candidates):
        candidate.rank = i + 1

    return candidates


def match_task(
    task: TaskScoreInput,
    volunteers: list[VolunteerScoreInput],
    weights: ScoringWeights = DEFAULT_WEIGHTS,
    velocity_factor: float = 0.0,
    max_alternatives: int = 3,
) -> MatchResult:
    """
    Find the best volunteer(s) for a task.

    For multi-volunteer tasks (team_size > 1), selects the top N
    non-overlapping volunteers.

    Args:
        task: The task to match
        volunteers: Available volunteer pool
        weights: Scoring weights
        velocity_factor: Crisis velocity
        max_alternatives: Number of alternatives to keep for explainability

    Returns:
        MatchResult with chosen volunteers and alternatives
    """
    if not volunteers:
        logger.warning(f"No volunteers available for task {task.id[:8]}")
        return MatchResult(
            task=task,
            chosen=[],
            alternatives=[],
            total_candidates=0,
            match_found=False,
        )

    ranked = rank_volunteers(task, volunteers, weights, velocity_factor)

    # Select top N for team_size
    chosen = ranked[:task.team_size]
    remaining = ranked[task.team_size:]

    # Keep top alternatives for explainability
    alternatives = remaining[:max_alternatives]

    match_found = len(chosen) > 0

    if match_found:
        logger.info(
            f"Task {task.id[:8]}: matched {len(chosen)} volunteer(s), "
            f"top VAS={chosen[0].breakdown.final_vas_score:.4f}"
        )
    else:
        logger.warning(f"Task {task.id[:8]}: no match found from {len(volunteers)} candidates")

    return MatchResult(
        task=task,
        chosen=chosen,
        alternatives=alternatives,
        total_candidates=len(ranked),
        match_found=match_found,
    )
