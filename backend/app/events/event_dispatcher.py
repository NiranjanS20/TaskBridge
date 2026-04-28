"""
VASAE Event Dispatcher
----------------------
In-process event bus with optional Redis Pub/Sub upgrade path.

Events trigger allocation cycles reactively.
Falls back to synchronous dispatch if Redis is unavailable.

Tier-1 Hardening Extensions:
- EVENT_WEIGHTS_UPDATED for downstream reallocation
- EventAggregator: batches similar events instead of dropping
- Adaptive debounce: 300ms-1s based on current event rate
- Event storm detection with structured logging
"""

import asyncio
import time
from typing import Callable, Any
from collections import defaultdict
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


# Event types
EVENT_NEW_TASK = "new_task"
EVENT_VOLUNTEER_UPDATE = "volunteer_update"
EVENT_CANCELLATION = "cancellation"
EVENT_URGENCY_CHANGE = "urgency_change"
EVENT_ALLOCATION_COMPLETE = "allocation_complete"
EVENT_WEIGHTS_UPDATED = "weights_updated"
EVENT_TASK_ASSIGNED = "task_assigned"
EVENT_TASK_ACCEPTED = "task_accepted"

# Global subscriber registry
_subscribers: dict[str, list[Callable]] = defaultdict(list)
_default_handlers_registered = False


def subscribe(event_type: str, handler: Callable) -> None:
    """
    Register a handler for an event type.

    Args:
        event_type: One of the EVENT_* constants
        handler: Async callable that receives (event_type, payload)
    """
    _subscribers[event_type].append(handler)
    logger.info(f"Event subscriber registered: {event_type} -> {handler.__name__}")


async def publish(event_type: str, payload: dict[str, Any] | None = None) -> None:
    """
    Publish an event to all subscribers.

    In-process dispatch — runs handlers concurrently.
    In production, publish to Redis Pub/Sub and let workers consume.

    Args:
        event_type: Event type string
        payload: Event data
    """
    if payload is None:
        payload = {}

    _ensure_default_handlers()

    handlers = _subscribers.get(event_type, [])

    if not handlers:
        logger.debug(f"Event '{event_type}' published — no subscribers")
        return

    logger.info(f"Event '{event_type}' dispatched to {len(handlers)} handler(s)")

    # Push event to websocket rooms for realtime UI updates.
    try:
        from app.core.websocket_manager import websocket_manager

        await websocket_manager.dispatch_system_event(event_type, payload)
    except Exception as exc:
        logger.warning(f"WebSocket dispatch failed for event '{event_type}': {exc}")

    for handler in handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event_type, payload)
            else:
                handler(event_type, payload)
        except Exception as e:
            logger.error(f"Event handler error [{event_type}]: {e}")


def clear_subscribers() -> None:
    """Clear all subscribers (useful for testing)."""
    global _default_handlers_registered
    _subscribers.clear()
    _default_handlers_registered = False


def _ensure_default_handlers() -> None:
    """Register default realtime handlers once."""
    global _default_handlers_registered
    if _default_handlers_registered:
        return

    subscribe(EVENT_NEW_TASK, _aggregated_allocation_handler)
    subscribe(EVENT_VOLUNTEER_UPDATE, _aggregated_allocation_handler)
    subscribe(EVENT_CANCELLATION, _aggregated_allocation_handler)
    subscribe(EVENT_URGENCY_CHANGE, _aggregated_allocation_handler)
    subscribe(EVENT_WEIGHTS_UPDATED, _on_weights_updated)

    _default_handlers_registered = True


# =====================================================================
# EVENT AGGREGATOR — Batches similar events with adaptive debounce
# =====================================================================

class EventAggregator:
    """
    Accumulates rapid events and dispatches a single batched allocation
    trigger after an adaptive quiet period.

    Instead of dropping duplicate events (simple debounce), this aggregator
    COLLECTS all event payloads and passes the full batch to the handler.

    Adaptive debounce logic:
    - Low load (< threshold): use min debounce (300ms) — fast response
    - High load (≥ threshold): ramp up to max debounce (1s) — prevent storms
    """

    def __init__(
        self,
        min_debounce: float | None = None,
        max_debounce: float | None = None,
        load_threshold: int | None = None,
    ) -> None:
        self._min_debounce = min_debounce or settings.DEBOUNCE_MIN_SECONDS
        self._max_debounce = max_debounce or settings.DEBOUNCE_MAX_SECONDS
        self._load_threshold = load_threshold or settings.DEBOUNCE_LOAD_THRESHOLD
        self._pending_events: list[tuple[str, dict]] = []
        self._timer_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._event_timestamps: list[float] = []

    def _compute_debounce(self) -> float:
        """Adaptive debounce based on recent event rate."""
        now = time.monotonic()
        # Keep only events from last 5 seconds for rate calculation
        self._event_timestamps = [t for t in self._event_timestamps if now - t < 5.0]
        rate = len(self._event_timestamps) / 5.0  # events/sec

        if rate >= self._load_threshold:
            return self._max_debounce
        elif rate <= 1.0:
            return self._min_debounce
        else:
            # Linear interpolation between min and max
            ratio = (rate - 1.0) / (self._load_threshold - 1.0)
            return self._min_debounce + ratio * (self._max_debounce - self._min_debounce)

    async def push_event(self, event_type: str, payload: dict) -> None:
        """
        Push an event into the aggregation buffer.

        If no timer is running, starts one. If a timer is already pending,
        the event is batched and the timer is NOT reset — this ensures
        maximum latency = debounce_duration even under continuous load.
        """
        async with self._lock:
            self._event_timestamps.append(time.monotonic())
            self._pending_events.append((event_type, payload))

            if self._timer_task is None or self._timer_task.done():
                debounce = self._compute_debounce()
                self._timer_task = asyncio.create_task(self._flush_after(debounce))
                logger.debug(
                    f"Aggregator: timer started ({debounce:.2f}s), "
                    f"buffer size={len(self._pending_events)}"
                )

    async def _flush_after(self, delay: float) -> None:
        """Wait for debounce period, then flush all accumulated events."""
        await asyncio.sleep(delay)

        async with self._lock:
            if not self._pending_events:
                return

            batch = list(self._pending_events)
            self._pending_events.clear()

        # Extract unique task IDs from all batched events
        task_ids = list({
            p.get("task_id") for _, p in batch if p.get("task_id")
        })
        ngo_ids = list({
            p.get("ngo_id") for _, p in batch if p.get("ngo_id")
        })
        event_types = list({et for et, _ in batch})

        logger.info(
            f"Aggregator: flushing {len(batch)} events "
            f"(types={event_types}, tasks={len(task_ids)})"
        )

        try:
            from app.workers.tasks import trigger_realtime_allocation

            mode = "batch" if len(task_ids) > 1 else "streaming"
            focus_task_id = task_ids[0] if len(task_ids) == 1 else None

            await trigger_realtime_allocation(
                event_type=",".join(event_types),
                payload={
                    "batch_size": len(batch),
                    "task_ids": task_ids,
                    "task_id": focus_task_id,
                    "ngo_id": ngo_ids[0] if len(ngo_ids) == 1 else None,
                },
                mode=mode,
            )
        except Exception as exc:
            logger.error(f"Aggregator: flush failed: {exc}")

    async def diagnostics(self) -> dict:
        """Diagnostic info for health endpoint."""
        async with self._lock:
            now = time.monotonic()
            recent = [t for t in self._event_timestamps if now - t < 5.0]
            return {
                "pending_events": len(self._pending_events),
                "event_rate_5s": round(len(recent) / 5.0, 2),
                "current_debounce_ms": round(self._compute_debounce() * 1000, 0),
                "timer_active": self._timer_task is not None and not self._timer_task.done(),
            }


# Module-level aggregator singleton
_aggregator = EventAggregator()


def get_aggregator() -> EventAggregator:
    """Access the module-level event aggregator."""
    return _aggregator


# =====================================================================
# HANDLERS
# =====================================================================

async def _update_priority_queue_for_event(event_type: str, payload: dict[str, Any]) -> None:
    """Keep queue ordering aligned with task events."""
    task_id = payload.get("task_id")
    if not task_id or event_type not in {EVENT_NEW_TASK, EVENT_CANCELLATION, EVENT_URGENCY_CHANGE}:
        return

    try:
        from sqlalchemy import select

        from app.core.priority_queue import TaskPriorityQueue
        from app.db.session import async_session_factory
        from app.models.task import Task

        queue = TaskPriorityQueue()

        async with async_session_factory() as db:
            result = await db.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()
            if task is None:
                return

            if event_type == EVENT_NEW_TASK:
                await queue.push_task(task)
            elif event_type == EVENT_URGENCY_CHANGE:
                await queue.update_task_priority(task)
            elif event_type == EVENT_CANCELLATION:
                # Requeue cancelled assignment tasks for immediate reassignment.
                await queue.push_task(task)
    except Exception as exc:
        logger.warning(f"Failed to update priority queue for event {event_type}: {exc}")


async def _aggregated_allocation_handler(event_type: str, payload: dict[str, Any]) -> None:
    """
    Bridge app events into the event aggregator instead of triggering
    immediate allocation. This prevents event storms from causing
    redundant allocation cycles.
    """
    await _update_priority_queue_for_event(event_type, payload)
    await _aggregator.push_event(event_type, payload)


async def _on_weights_updated(event_type: str, payload: dict[str, Any]) -> None:
    """
    Handle weight update events — trigger partial reallocation.

    When weights change, recently allocated tasks with low confidence
    scores may now have a better volunteer match. We trigger a
    re-evaluation via the aggregator.
    """
    logger.info(
        "Weights updated event received: profile=%s version=%s source=%s",
        payload.get("profile", "unknown"),
        payload.get("version_id", "?"),
        payload.get("source", "unknown"),
    )

    # Push a synthetic reallocation event into the aggregator
    await _aggregator.push_event("weights_reallocation", {
        "trigger": "weights_updated",
        "profile": payload.get("profile"),
        "version_id": payload.get("version_id"),
    })
