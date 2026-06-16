import asyncio
import time

import httpx
from redis.asyncio import Redis

from src.config.settings import settings

CACHE_KEY = "svc_token:{service_id}"
LOCK_KEY = "svc_token_lock:{service_id}"
LOCK_TTL = 15
BUFFER = 60


class ServiceTokenCache:
    """Two-level cache for a service-to-service JWT.

    Tokens are cached first in Redis (shared across instances) and then in a
    local in-process variable to avoid hitting Redis on every request. A
    distributed lock prevents thundering-herd refreshes when the token expires.
    """

    def __init__(self, redis: Redis):
        self._redis = redis
        self._local_token: str | None = None
        self._local_expires_at: float = 0.0

    async def get(self) -> str:
        """Return a valid service token, refreshing if necessary.

        Checks the in-process cache first, then the Redis cache, and finally
        fetches a new token from the auth service.

        Returns:
            A valid service JWT string.
        """
        if self._local_token and time.time() < self._local_expires_at - BUFFER:
            return self._local_token

        cache_key = CACHE_KEY.format(service_id=settings.SERVICE_ID)
        cached = await self._redis.get(cache_key)
        if cached:
            ttl = await self._redis.ttl(cache_key)
            self._local_token = cached
            self._local_expires_at = time.time() + max(ttl, 0) + BUFFER
            return self._local_token

        return await self._refresh()

    async def _refresh(self) -> str:
        """Acquire a distributed lock and fetch a fresh service token.

        Uses a Redis-based lock to prevent multiple instances from requesting a
        new token simultaneously. If the lock cannot be acquired, waits briefly
        and retries from the cache.

        Returns:
            A freshly fetched service JWT string.
        """
        cache_key = CACHE_KEY.format(service_id=settings.SERVICE_ID)
        lock_key = LOCK_KEY.format(service_id=settings.SERVICE_ID)
        acquired = await self._redis.set(lock_key, "1", nx=True, ex=LOCK_TTL)

        if not acquired:
            await asyncio.sleep(0.5)
            cached = await self._redis.get(cache_key)
            if cached:
                ttl = await self._redis.ttl(cache_key)
                self._local_token = cached
                self._local_expires_at = time.time() + max(ttl, 0) + BUFFER
                return self._local_token
            return await self.get()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.AUTH_SERVICE_URL}/api/v1/service-clients/token",
                    json={"service_id": settings.SERVICE_ID, "service_secret": settings.SERVICE_SECRET},
                )
                response.raise_for_status()
                data = response.json()

            token = data["access_token"]
            expires_in = int(data["expires_in"])
            await self._redis.setex(cache_key, max(expires_in - BUFFER, 1), token)
            self._local_token = token
            self._local_expires_at = time.time() + expires_in
            return token
        finally:
            await self._redis.delete(lock_key)
