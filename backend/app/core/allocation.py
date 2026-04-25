"""
VASAE Allocation Engine
-----------------------
CORE ORCHESTRATION — no DB calls, no storage side effects.

Orchestrates a full allocation cycle:
1. Takes pending tasks + available volunteers
2. Pushes tasks to priority queue
3. Pops highest-priority task in real time
4. Matches each task to best volunteer(s)
5. Acquires per-volunteer lock before assignment
6. Retries on lock contention
7. Applies graceful degradation if no match found
8. Returns structured allocation results with explainability data

Tier-1 Hardening Extensions:
- Confidence score: difference between top-2 VAS scores
- Retry fairness boost: exponential priority increase for failed tasks
- Cycle ID: groups all decisions from a single cycle
- Stale task filtering: skip tasks whose status changed since enqueue

This is the CORE LOOP of the entire system.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from app.config import get_settings
from app.core.priority_queue import TaskPriorityQueue
from app.core.scoring import (
    DEFAULT_WEIGHTS,
    ScoreBreakdown,
    ScoringWeights,
    TaskScoreInput,
    VolunteerScoreInput,
)
from app.core.matching import match_task, MatchResult, MatchCandidate
from app.core.fairness import (
    DegradationState,
    compute_degradation,
)
from app.utils.locks import VolunteerLockManager
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class AllocationDecision:
    """A single task-volunteer binding decision."""
    task_id: str
    volunteer_id: str
    volunteer_name: str
    vas_score: float
    breakdown: ScoreBreakdown
    alternatives: list[MatchCandidate]
    degradation_mode: str = "standard"
    confidence_score: float = 0.0
    cycle_id: str = ""


@dataclass
class AllocationCycleResult:
    """Full result of an allocation cycle."""
    cycle_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decisions: list[AllocationDecision] = field(default_factory=list)
    unmatched_task_ids: list[str] = field(default_factory=list)
    escalated_task_ids: list[str] = field(default_factory=list)
    requeued_task_ids: list[str] = field(default_factory=list)
    total_tasks: int = 0
    total_volunteers: int = 0


def compute_confidence(match_result: MatchResult) -> float:
    """
    Compute allocation confidence as the VAS score gap between
    the top candidate and the runner-up.

    Higher confidence = clearer winner. Low confidence = close call.

    Returns 1.0 if only one candidate, 0.0 if no candidates.
    """
    if not match_result.chosen:
        return 0.0

    top_score = match_result.chosen[0].breakdown.final_vas_score

    # Runner-up is first alternative, or second chosen (for team assignments)
    runner_up_score = 0.0
    if match_result.alternatives:
        runner_up_score = match_result.alternatives[0].breakdown.final_vas_score
    elif len(match_result.chosen) > 1:
        runner_up_score = match_result.chosen[1].breakdown.final_vas_score

    if runner_up_score == 0.0:
        return 1.0  # Only one candidate — maximum confidence

    return round(top_score - runner_up_score, 6)


def compute_retry_priority_boost(
    retry_count: int,
    base_boost: float = 1.0,
    boost_factor: float = 1.5,
) -> float:
    """
    Compute exponential priority boost for retried tasks.

    boost = base_boost * (boost_factor ^ retry_count)

    Ensures tasks that fail multiple times get increasingly
    prioritized in the next pop cycle — fairness guarantee.
    """
    if retry_count <= 0:
        return 0.0
    return round(base_boost * (boost_factor ** retry_count), 6)


async def _match_with_degradation(
    task: TaskScoreInput,
    available: list[VolunteerScoreInput],
    weights: ScoringWeights,
    velocity: float,
    max_degradation_radius: float,
    radius_step: float,
) -> tuple[MatchResult | None, DegradationState]:
    degradation = DegradationState()
    match_result: MatchResult | None = None

    for _attempt in range(5):
        if degradation.skill_relaxed:
            task_relaxed = TaskScoreInput(
                id=task.id,
                required_skills=[],
                urgency=task.urgency,
                complexity=task.complexity,
                latitude=task.latitude,
                longitude=task.longitude,
                waiting_time_minutes=task.waiting_time_minutes,
                team_size=task.team_size,
                region=task.region,
            )
            match_result = match_task(task_relaxed, available, weights, velocity)
        else:
            match_result = match_task(task, available, weights, velocity)

        if match_result.match_found:
            return match_result, degradation

        degradation = compute_degradation(
            match_found=False,
            current_state=degradation,
            radius_step_km=radius_step,
            max_radius_km=max_degradation_radius,
        )

        if degradation.escalated:
            break

    return match_result, degradation


async def allocation_cycle(
    tasks: list[TaskScoreInput],
    volunteers: list[VolunteerScoreInput],
    weights: ScoringWeights = DEFAULT_WEIGHTS,
    velocity_factors: dict[str, float] | None = None,
    max_degradation_radius: float = 100.0,
    radius_step: float = 10.0,
    priority_queue: TaskPriorityQueue | None = None,
    lock_manager: VolunteerLockManager | None = None,
    lock_retry_attempts: int | None = None,
    persist_decision_callback: Callable[[AllocationDecision], Awaitable[None]] | None = None,
) -> AllocationCycleResult:
    """
    Execute a real-time allocation cycle.

    Flow:
    1. Push pending tasks into priority queue
    2. Pop highest-priority task
    3. Match volunteers with graceful degradation
    4. Compute confidence score (top-2 VAS gap)
    5. Acquire volunteer lock(s)
    6. Assign + persist callback (if provided)
    7. Release locks
    8. Retry on lock contention with exponential priority boost

    Args:
        tasks: Pending tasks needing allocation
        volunteers: Available volunteer pool
        weights: Scoring weights
        velocity_factors: Per-region crisis velocity {region: factor}
        max_degradation_radius: Max expanded radius before escalation
        radius_step: Radius expansion step in km
        priority_queue: Redis/heap priority queue abstraction
        lock_manager: Volunteer lock manager
        lock_retry_attempts: Number of retries for lock contention
        persist_decision_callback: Optional callback executed while lock is held

    Returns:
        AllocationCycleResult with all decisions and unmatched tasks
    """
    if velocity_factors is None:
        velocity_factors = {}
    if lock_retry_attempts is None:
        lock_retry_attempts = settings.LOCK_RETRY_ATTEMPTS
    if priority_queue is None:
        priority_queue = TaskPriorityQueue()
    if lock_manager is None:
        lock_manager = VolunteerLockManager()

    result = AllocationCycleResult(
        total_tasks=len(tasks),
        total_volunteers=len(volunteers),
    )

    if not tasks:
        logger.info("Allocation cycle: no pending tasks")
        return result

    if not volunteers:
        logger.warning("Allocation cycle: no available volunteers")
        result.unmatched_task_ids = [t.id for t in tasks]
        return result

    # --- Step 1: Queue initialization ---
    task_map = {t.id: t for t in tasks}
    retry_count: dict[str, int] = {t.id: 0 for t in tasks}
    await priority_queue.bulk_push(tasks)

    # --- Step 2: Real-time pop/assign loop ---
    assigned_volunteer_ids: set[str] = set()

    while True:
        popped = await priority_queue.pop_task()
        if popped is None:
            break

        task = task_map.get(popped.task_id)
        if task is None:
            continue

        velocity = velocity_factors.get(task.region or "", 0.0)

        available = [
            v for v in volunteers
            if v.id not in assigned_volunteer_ids
            and v.burnout_risk <= settings.BURNOUT_RISK_ASSIGNMENT_THRESHOLD
        ]
        if not available:
            result.unmatched_task_ids.append(task.id)
            logger.warning(f"Task {task.id[:8]}: no available volunteers")
            continue

        match_result, degradation = await _match_with_degradation(
            task=task,
            available=available,
            weights=weights,
            velocity=velocity,
            max_degradation_radius=max_degradation_radius,
            radius_step=radius_step,
        )

        if not match_result or not match_result.match_found:
            if degradation.escalated:
                result.escalated_task_ids.append(task.id)
                logger.warning(f"Task {task.id[:8]}: ESCALATED — no viable match")
            else:
                result.unmatched_task_ids.append(task.id)
                logger.warning(f"Task {task.id[:8]}: unmatched")
            continue

        # --- Confidence computation ---
        confidence = compute_confidence(match_result)

        fallback_candidates = match_result.chosen + match_result.alternatives
        needed = max(task.team_size, 1)
        locked: list[tuple[MatchCandidate, str]] = []

        try:
            for candidate in fallback_candidates:
                if candidate.volunteer.id in assigned_volunteer_ids:
                    continue

                token = await lock_manager.acquire_lock(candidate.volunteer.id)
                if token is None:
                    continue

                locked.append((candidate, token))
                if len(locked) >= needed:
                    break

            if len(locked) < needed:
                # Partial assignment rollback on lock contention.
                for candidate, token in locked:
                    await lock_manager.release_lock(candidate.volunteer.id, token)

                retry_count[task.id] += 1
                if retry_count[task.id] <= lock_retry_attempts:
                    # Exponential fairness boost for retried tasks
                    boost = compute_retry_priority_boost(
                        retry_count[task.id],
                        base_boost=settings.RETRY_PRIORITY_BOOST_BASE,
                        boost_factor=settings.RETRY_PRIORITY_BOOST_FACTOR,
                    )
                    boosted_priority = popped.priority + boost
                    await priority_queue.push_task(task, priority=boosted_priority)
                    result.requeued_task_ids.append(task.id)
                    logger.info(
                        f"Task {task.id[:8]} requeued with priority boost +{boost:.2f} "
                        f"(attempt {retry_count[task.id]}/{lock_retry_attempts})"
                    )
                else:
                    result.unmatched_task_ids.append(task.id)
                    logger.warning(
                        f"Task {task.id[:8]} unresolved after lock retries "
                        f"({retry_count[task.id]} attempts)"
                    )
                continue

            for chosen, _token in locked[:needed]:
                decision = AllocationDecision(
                    task_id=task.id,
                    volunteer_id=chosen.volunteer.id,
                    volunteer_name=chosen.volunteer.name,
                    vas_score=chosen.breakdown.final_vas_score,
                    breakdown=chosen.breakdown,
                    alternatives=match_result.alternatives,
                    degradation_mode=degradation.mode,
                    confidence_score=confidence,
                    cycle_id=result.cycle_id,
                )

                if persist_decision_callback is not None:
                    await persist_decision_callback(decision)

                result.decisions.append(decision)
                assigned_volunteer_ids.add(chosen.volunteer.id)

            logger.info(
                f"Task {task.id[:8]}: allocated {needed} volunteer(s) "
                f"[mode={degradation.mode}, confidence={confidence:.4f}]"
            )

        finally:
            for candidate, token in locked:
                await lock_manager.release_lock(candidate.volunteer.id, token)

    logger.info(
        f"Allocation cycle {result.cycle_id[:8]} complete: "
        f"{len(result.decisions)} assigned, "
        f"{len(result.unmatched_task_ids)} unmatched, "
        f"{len(result.escalated_task_ids)} escalated, "
        f"{len(result.requeued_task_ids)} requeued"
    )

    return result
