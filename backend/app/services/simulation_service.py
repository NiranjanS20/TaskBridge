"""
Simulation orchestration service with in-memory state and SSE streaming support.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.allocation import allocation_cycle
from app.core.scoring import ScoringWeights, VolunteerScoreInput
from app.core.simulation import blueprint_to_score_input, generate_synthetic_tasks
from app.models.task import Task
from app.schemas.task_schema import TaskCreateRequest
from app.services import learning_service
from app.services.lifecycle_service import get_available_volunteers, get_metrics_map
from app.services.prediction_service import predict_region_async
from app.services.ingestion_service import create_task_from_structured
from app.events.event_dispatcher import EVENT_NEW_TASK, publish
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

_SIM_RATE_WINDOW_SECONDS = 60
_SIM_RATE_LIMIT = 5


@dataclass
class SimulationRun:
    id: str
    region: str
    scenario_type: str
    task_count: int
    duration_seconds: int
    sandbox: bool
    status: str = "queued"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    progress: dict[str, Any] = field(default_factory=dict)
    results: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    subscribers: list[asyncio.Queue] = field(default_factory=list)


_simulations: dict[str, SimulationRun] = {}
_sim_rate_window: deque[float] = deque()
_sim_lock = asyncio.Lock()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _volunteer_to_score_input(vol, lifecycle_metrics: dict | None = None) -> VolunteerScoreInput:
    metrics = lifecycle_metrics or {}
    return VolunteerScoreInput(
        id=vol.id,
        name=vol.name,
        skills=vol.skills or [],
        latitude=vol.latitude,
        longitude=vol.longitude,
        availability=vol.availability,
        reliability=vol.reliability,
        burnout_score=vol.burnout_score,
        engagement_score=float(metrics.get("engagement_score", 0.5)),
        burnout_risk=float(metrics.get("burnout_risk", 0.0)),
        total_assignments=vol.total_assignments,
        active_assignments=vol.active_assignments,
    )


async def _emit(sim: SimulationRun, payload: dict[str, Any]) -> None:
    sim.progress.update(payload)
    for queue in list(sim.subscribers):
        try:
            await queue.put(payload)
        except Exception:
            continue


async def _enforce_rate_limit() -> None:
    now = time.monotonic()
    while _sim_rate_window and now - _sim_rate_window[0] > _SIM_RATE_WINDOW_SECONDS:
        _sim_rate_window.popleft()
    if len(_sim_rate_window) >= _SIM_RATE_LIMIT:
        raise ValueError("Simulation rate limit exceeded. Please retry shortly.")
    _sim_rate_window.append(now)


async def start_simulation(
    *,
    db: AsyncSession,
    region: str,
    scenario_type: str,
    task_count: int,
    duration_seconds: int,
    sandbox: bool = True,
) -> str:
    async with _sim_lock:
        await _enforce_rate_limit()
        sim_id = str(uuid.uuid4())
        _simulations[sim_id] = SimulationRun(
            id=sim_id,
            region=region,
            scenario_type=scenario_type,
            task_count=task_count,
            duration_seconds=duration_seconds,
            sandbox=sandbox,
            progress={
                "tasks_generated": 0,
                "assignments_done": 0,
                "queue_depth": 0,
                "avg_latency": 0.0,
            },
        )

    asyncio.create_task(_run_simulation(sim_id))
    return sim_id


async def _run_simulation(sim_id: str) -> None:
    from app.db.session import async_session_factory

    sim = _simulations[sim_id]
    sim.status = "running"
    sim.started_at = _utc_now()
    started = time.monotonic()

    try:
        # Give request/commit cycle a short head start before DB-intensive simulation.
        await asyncio.sleep(0.05)
        async with async_session_factory() as db:
            prediction_bias = 0.0
            try:
                metrics = await predict_region_async(db, sim.region)
                prediction_bias = max(0.0, min(1.0, metrics.risk_score))
            except Exception:
                prediction_bias = 0.0

            blueprints = generate_synthetic_tasks(
                region=sim.region,
                scenario_type=sim.scenario_type,
                task_count=sim.task_count,
                duration_seconds=sim.duration_seconds,
                base_latitude=28.6139,
                base_longitude=77.2090,
                prediction_bias=prediction_bias,
            )
            await _emit(sim, {"tasks_generated": len(blueprints)})

            available_vols = await get_available_volunteers(db)
            metrics_map = await get_metrics_map(db, [v.id for v in available_vols])
            vol_inputs = [
                _volunteer_to_score_input(
                    v,
                    {
                        "engagement_score": metrics_map.get(v.id).engagement_score if metrics_map.get(v.id) else 0.5,
                        "burnout_risk": metrics_map.get(v.id).burnout_risk if metrics_map.get(v.id) else 0.0,
                    },
                )
                for v in available_vols
            ]

            task_inputs = [blueprint_to_score_input(b) for b in blueprints]

            base_weights = ScoringWeights(
                k1=settings.VAS_K1,
                k2=settings.VAS_K2,
                k3=settings.VAS_K3,
                k4=settings.VAS_K4,
                fit_skill=settings.FIT_SKILL_WEIGHT,
                fit_proximity=settings.FIT_PROXIMITY_WEIGHT,
                fit_reliability=settings.FIT_RELIABILITY_WEIGHT,
                fit_availability=settings.FIT_AVAILABILITY_WEIGHT,
                max_radius_km=settings.MAX_SEARCH_RADIUS_KM,
            )
            weights = await learning_service.get_effective_scoring_weights(db, base_weights)

            if sim.sandbox:
                cycle_result = await allocation_cycle(
                    tasks=task_inputs,
                    volunteers=vol_inputs,
                    weights=weights,
                )
                assignments_done = len(cycle_result.decisions)
                failures = len(cycle_result.unmatched_task_ids) + len(cycle_result.escalated_task_ids)
            else:
                created = 0
                for blueprint in blueprints:
                    created_task = await create_task_from_structured(
                        db,
                        TaskCreateRequest(
                            title=f"[sim:{sim.id[:8]}] {blueprint.title}",
                            description=blueprint.description,
                            category=blueprint.category,
                            required_skills=blueprint.required_skills,
                            urgency=blueprint.urgency,
                            complexity=blueprint.complexity,
                            team_size=blueprint.team_size,
                            latitude=blueprint.latitude,
                            longitude=blueprint.longitude,
                            region=blueprint.region,
                        ),
                    )
                    created += 1
                    await publish(EVENT_NEW_TASK, {"task_id": created_task.id, "type": "simulation"})
                    if created % 5 == 0 or created == len(blueprints):
                        await _emit(sim, {"tasks_generated": created})
                await db.commit()

                assignments_done = 0
                failures = 0
                result = await db.execute(
                    select(Task.id, Task.status).where(Task.title.like(f"[sim:{sim.id[:8]}]%"))
                )
                rows = result.all()
                for _task_id, status in rows:
                    if status in {"allocated", "completed"}:
                        assignments_done += 1
                    else:
                        failures += 1

            elapsed_ms = (time.monotonic() - started) * 1000.0
            avg_latency = (elapsed_ms / max(sim.task_count, 1)) if sim.task_count > 0 else 0.0
            sim.results = {
                "simulation_id": sim.id,
                "region": sim.region,
                "scenario_type": sim.scenario_type,
                "sandbox": sim.sandbox,
                "tasks_generated": len(blueprints),
                "assignments_done": assignments_done,
                "failures": failures,
                "queue_depth": max(len(blueprints) - assignments_done, 0),
                "avg_latency": round(avg_latency, 2),
                "prediction_bias": round(prediction_bias, 4),
                "duration_ms": round(elapsed_ms, 2),
            }
            sim.status = "completed"
            sim.finished_at = _utc_now()
            await _emit(
                sim,
                {
                    "assignments_done": assignments_done,
                    "queue_depth": sim.results["queue_depth"],
                    "avg_latency": sim.results["avg_latency"],
                    "status": "completed",
                },
            )
    except Exception as exc:
        logger.exception("Simulation failed [%s]", sim.id)
        sim.status = "failed"
        sim.error = str(exc)
        sim.finished_at = _utc_now()
        await _emit(sim, {"status": "failed", "error": sim.error})
    finally:
        # signal subscribers to close stream
        for queue in list(sim.subscribers):
            try:
                await queue.put({"event": "close"})
            except Exception:
                continue


def get_simulation_status(sim_id: str) -> dict[str, Any] | None:
    sim = _simulations.get(sim_id)
    if sim is None:
        return None
    return {
        "simulation_id": sim.id,
        "status": sim.status,
        "started_at": sim.started_at.isoformat() if sim.started_at else None,
        "finished_at": sim.finished_at.isoformat() if sim.finished_at else None,
        "progress": sim.progress,
        "error": sim.error,
    }


def get_simulation_results(sim_id: str) -> dict[str, Any] | None:
    sim = _simulations.get(sim_id)
    if sim is None:
        return None
    return {
        "simulation_id": sim.id,
        "status": sim.status,
        "results": sim.results,
        "error": sim.error,
    }


async def stream_simulation(sim_id: str) -> AsyncIterator[str]:
    sim = _simulations.get(sim_id)
    if sim is None:
        yield "event: error\ndata: {\"error\":\"simulation_not_found\"}\n\n"
        return

    queue: asyncio.Queue = asyncio.Queue()
    sim.subscribers.append(queue)
    # send snapshot first
    initial = {
        "simulation_id": sim.id,
        "status": sim.status,
        **sim.progress,
    }
    yield f"data: {json.dumps(initial)}\n\n"

    try:
        while True:
            update = await queue.get()
            if update.get("event") == "close":
                break
            payload = {"simulation_id": sim.id, "status": sim.status, **update}
            yield f"data: {json.dumps(payload)}\n\n"
    finally:
        if queue in sim.subscribers:
            sim.subscribers.remove(queue)
