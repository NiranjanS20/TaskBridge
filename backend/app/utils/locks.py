"""
VASAE Volunteer Lock Manager
----------------------------
Concurrency-safe volunteer reservation for allocation workers.

Redis SETNX lock is preferred; in-memory lock map is used as fallback.

Tier-1 Hardening Extensions:
- Lock metrics tracking (acquire/release/contention counts)
- Expired lock cleanup for in-memory mode
- diagnostics() for health endpoint
"""

from __future__ import annotations

import asyncio
import time
import uuid

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class LockMetrics:
    """Thread-safe counters for lock observability."""

    def __init__(self) -> None:
        self.acquires: int = 0
        self.releases: int = 0
        self.contentions: int = 0
        self.expirations_cleaned: int = 0

    def snapshot(self) -> dict:
        return {
            "acquires": self.acquires,
            "releases": self.releases,
            "contentions": self.contentions,
            "expirations_cleaned": self.expirations_cleaned,
            "contention_rate": round(
                self.contentions / max(self.acquires, 1), 4,
            ),
        }


class VolunteerLockManager:
    def __init__(
        self,
        redis_url: str | None = None,
        lock_ttl_seconds: int | None = None,
    ) -> None:
        self.redis_url = redis_url or settings.REDIS_URL
        self.lock_ttl_seconds = lock_ttl_seconds or settings.VOLUNTEER_LOCK_TTL_SECONDS

        self._redis = None
        self._redis_available = True

        self._memory_guard = asyncio.Lock()
        self._memory_locks: dict[str, tuple[str, float]] = {}
        self.metrics = LockMetrics()

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
            logger.warning(f"Volunteer lock Redis unavailable, using in-memory locks: {exc}")
            return None

    @staticmethod
    def _key(volunteer_id: str) -> str:
        return f"vasae:lock:volunteer:{volunteer_id}"

    async def acquire_lock(self, volunteer_id: str) -> str | None:
        """
        Acquire an exclusive lock for volunteer assignment.

        Returns lock token if acquired, else None.
        """
        self.metrics.acquires += 1
        token = str(uuid.uuid4())
        redis_client = await self._get_redis()

        if redis_client is not None:
            try:
                ok = await redis_client.set(
                    self._key(volunteer_id),
                    token,
                    ex=self.lock_ttl_seconds,
                    nx=True,
                )
                if ok:
                    return token
                self.metrics.contentions += 1
                return None
            except Exception as exc:
                logger.warning(f"Redis lock acquire failed for {volunteer_id[:8]}: {exc}")

        expiry = time.monotonic() + float(self.lock_ttl_seconds)
        async with self._memory_guard:
            # Cleanup expired locks opportunistically
            await self._cleanup_expired_locked()

            current = self._memory_locks.get(volunteer_id)
            if current is not None:
                _current_token, current_expiry = current
                if current_expiry > time.monotonic():
                    self.metrics.contentions += 1
                    return None
            self._memory_locks[volunteer_id] = (token, expiry)
            return token

    async def release_lock(self, volunteer_id: str, token: str) -> bool:
        """Release lock only when token matches current owner."""
        self.metrics.releases += 1
        redis_client = await self._get_redis()

        if redis_client is not None:
            try:
                script = """
                if redis.call('GET', KEYS[1]) == ARGV[1] then
                    return redis.call('DEL', KEYS[1])
                else
                    return 0
                end
                """
                released = await redis_client.eval(script, 1, self._key(volunteer_id), token)
                return bool(released)
            except Exception as exc:
                logger.warning(f"Redis lock release failed for {volunteer_id[:8]}: {exc}")

        async with self._memory_guard:
            current = self._memory_locks.get(volunteer_id)
            if current is None:
                return False
            current_token, _expiry = current
            if current_token != token:
                return False
            del self._memory_locks[volunteer_id]
            return True

    async def _cleanup_expired_locked(self) -> int:
        """
        Remove expired in-memory locks.

        Called inside _memory_guard — do NOT acquire it here.
        Returns number of locks cleaned.
        """
        now = time.monotonic()
        expired_keys = [
            k for k, (_, exp) in self._memory_locks.items()
            if exp <= now
        ]
        for k in expired_keys:
            del self._memory_locks[k]

        if expired_keys:
            self.metrics.expirations_cleaned += len(expired_keys)
            logger.debug(f"Cleaned {len(expired_keys)} expired in-memory locks")

        return len(expired_keys)

    async def cleanup_expired(self) -> int:
        """Public cleanup for background sweep tasks."""
        async with self._memory_guard:
            return await self._cleanup_expired_locked()

    async def diagnostics(self) -> dict:
        """Structured health info for observability."""
        async with self._memory_guard:
            active_locks = sum(
                1 for _, (_, exp) in self._memory_locks.items()
                if exp > time.monotonic()
            )

        return {
            "backend": "redis" if self._redis_available and self._redis else "in-memory",
            "active_locks": active_locks,
            "metrics": self.metrics.snapshot(),
        }
