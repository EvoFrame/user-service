from datetime import UTC, datetime

from redis.asyncio import Redis

from src.config.settings import settings


class EventPublisher:
    """Publishes domain events to Redis Streams.

    Wraps each payload in a standard envelope that includes the source service
    name and a UTC timestamp before writing to the target stream.
    """

    def __init__(self, redis: Redis):
        self._redis = redis

    async def publish(self, stream: str, payload: dict[str, str], *, maxlen: int = 50_000) -> None:
        """Publish a message to a Redis Stream.

        Wraps ``payload`` in an envelope containing ``source_service`` and
        ``timestamp``, then appends it to ``stream`` with approximate trimming.

        Args:
            stream: The Redis stream key to write to
                (e.g. ``"user.profile.updated"``).
            payload: Domain-specific fields to include in the message.
            maxlen: Maximum number of entries to retain in the stream.
                Defaults to 50 000.
        """
        envelope: dict[str, str] = {
            "source_service": settings.SERVICE_ID,
            "timestamp": datetime.now(UTC).isoformat(),
            **payload,
        }
        await self._redis.xadd(stream, envelope, maxlen=maxlen, approximate=True)
