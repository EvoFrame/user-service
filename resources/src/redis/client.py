from redis.asyncio import Redis, from_url

from src.config.settings import settings

_client: Redis | None = None


async def get_redis() -> Redis:
    """Return the singleton Redis client, initialising it on first call.

    Returns:
        A connected Redis client with response decoding enabled.
    """
    global _client
    if _client is None:
        _client = await from_url(settings.REDIS_URL, decode_responses=True)
    return _client
