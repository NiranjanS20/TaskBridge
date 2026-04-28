"""
VASAE Real-Time Task Priority Queue
-----------------------------------
Redis sorted-set first, in-memory heap fallback.

Tier-1 Hardening Extensions:
- clear() — flush queue between cycles
- peek() — non-destructive inspection for diagnostics
- drain_stale() — remove entries for non-pending tasks
- diagnostics() — structured health info
"""

from __future__ import annotations

import asyncio
import heapq
from dataclasses import dataclass

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass(frozen=True)
class QueuePopResult:
    task_id: str
    priority: float


class TaskPriorityQueue:
    """Priority queue abstraction used by the real-time allocation engine."""

    def __init__(
        self,
        redis_url: str | None = None,
        queue_key: str | None = None,
    ) -> None:
        self.redis_url = redis_url or settings.REDIS_URL
        self.queue_key = queue_key or settings.REALTIME_QUEUE_KEY

        self._redis = None
        self._redis_available = True

        self._heap: list[tuple[float, int, str]] = []
        self._heap_priorities: dict[str, float] = {}
        self._heap_counter = 0
        self._heap_lock = asyncio.Lock()

    @staticmethod
    def compute_priority(task) -> float:
        """
        Compute task priority score.

        Preferred strategy from spec:
        urgency + waiting_time (higher is more urgent).
        """
        urgency = float(getattr(task, "urgency", 0.0) or 0.0)
        waiting = float(getattr(task, "waiting_time_minutes", 0.0) or 0.0)
        return round((urgency * 1000.0) + waiting, 6)

    async def _get_redis(self):
        if not self._redis_available:
            return None
        if self._redis is not None:
            return self._redis

        try:
            import redis.asyncio as redis

            client = redis.from_url(self.redis_url, decode_responses=True)
            await client.ping()
            self._redis = client
            return self._redis
        except Exception as exc:
            self._redis_available = False
            logger.warning(f"Priority queue Redis unavailable, using in-memory heap: {exc}")
            return None

    async def push_task(self, task, priority: float | None = None) -> float:
        task_id = str(getattr(task, "id"))
        resolved_priority = priority if priority is not None else self.compute_priority(task)

        redis_client = await self._get_redis()
        if redis_client is not None:
            try:
                await redis_client.zadd(self.queue_key, {task_id: resolved_priority})
                return resolved_priority
            except Exception as exc:
                logger.warning(f"Redis queue push failed for task {task_id[:8]}: {exc}")

        async with self._heap_lock:
            self._heap_counter += 1
            self._heap_priorities[task_id] = resolved_priority
            heapq.heappush(self._heap, (-resolved_priority, self._heap_counter, task_id))
        return resolved_priority

    async def bulk_push(self, tasks: list) -> None:
        for task in tasks:
            await self.push_task(task)

    async def pop_task(self) -> QueuePopResult | None:
        redis_client = await self._get_redis()
        if redis_client is not None:
            try:
                popped = await redis_client.zpopmax(self.queue_key, count=1)
                if not popped:
                    return None
                task_id, priority = popped[0]
                return QueuePopResult(task_id=str(task_id), priority=float(priority))
            except Exception as exc:
                logger.warning(f"Redis queue pop failed: {exc}")

        async with self._heap_lock:
            while self._heap:
                neg_priority, _counter, task_id = heapq.heappop(self._heap)
                expected = self._heap_priorities.get(task_id)
                current = -neg_priority
                if expected is None:
                    continue
                if abs(expected - current) > 1e-9:
                    continue

                del self._heap_priorities[task_id]
                return QueuePopResult(task_id=task_id, priority=current)

        return None

    async def peek(self) -> QueuePopResult | None:
        """Non-destructive inspection of the highest-priority task."""
        redis_client = await self._get_redis()
        if redis_client is not None:
            try:
                # ZRANGE with REV and LIMIT gives top element without removing
                result = await redis_client.zrange(
                    self.queue_key, 0, 0, desc=True, withscores=True,
                )
                if not result:
                    return None
                task_id, priority = result[0]
                return QueuePopResult(task_id=str(task_id), priority=float(priority))
            except Exception as exc:
                logger.warning(f"Redis queue peek failed: {exc}")

        async with self._heap_lock:
            for neg_priority, _counter, task_id in sorted(self._heap):
                expected = self._heap_priorities.get(task_id)
                if expected is None:
                    continue
                current = -neg_priority
                if abs(expected - current) > 1e-9:
                    continue
                return QueuePopResult(task_id=task_id, priority=current)

        return None

    async def remove_task(self, task_id: str) -> None:
        redis_client = await self._get_redis()
        if redis_client is not None:
            try:
                await redis_client.zrem(self.queue_key, task_id)
            except Exception as exc:
                logger.warning(f"Redis queue remove failed for task {task_id[:8]}: {exc}")

        async with self._heap_lock:
            self._heap_priorities.pop(task_id, None)

    async def update_task_priority(self, task) -> float:
        """Recompute and replace an existing task's priority."""
        return await self.push_task(task, priority=self.compute_priority(task))

    async def clear(self) -> int:
        """
        Flush the entire queue. Returns number of entries cleared.

        Used between allocation cycles to prevent stale entries.
        """
        count = 0
        redis_client = await self._get_redis()
        if redis_client is not None:
            try:
                count = await redis_client.zcard(self.queue_key)
                await redis_client.delete(self.queue_key)
                logger.info(f"Priority queue flushed: {count} entries (Redis)")
                return int(count)
            except Exception as exc:
                logger.warning(f"Redis queue clear failed: {exc}")

        async with self._heap_lock:
            count = len(self._heap_priorities)
            self._heap.clear()
            self._heap_priorities.clear()
            self._heap_counter = 0
            logger.info(f"Priority queue flushed: {count} entries (in-memory)")

        return count

    async def size(self) -> int:
        redis_client = await self._get_redis()
        if redis_client is not None:
            try:
                size = await redis_client.zcard(self.queue_key)
                return int(size)
            except Exception as exc:
                logger.warning(f"Redis queue size lookup failed: {exc}")

        async with self._heap_lock:
            return len(self._heap_priorities)

    async def diagnostics(self) -> dict:
        """
        Structured health info for the /health/queue endpoint.
        """
        current_size = await self.size()
        top = await self.peek()
        return {
            "size": current_size,
            "backend": "redis" if self._redis_available and self._redis else "in-memory",
            "top_task_id": top.task_id[:8] if top else None,
            "top_priority": top.priority if top else None,
        }
