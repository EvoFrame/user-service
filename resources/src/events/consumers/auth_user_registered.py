import socket
import uuid

import structlog
from redis.asyncio import Redis
from redis.exceptions import ResponseError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.config.settings import settings
from src.db.session import AsyncSessionLocal
from src.models.user_profile import UserPreference, UserProfile

STREAM = "auth.user.registered"
GROUP = settings.SERVICE_ID
WORKER = f"{settings.SERVICE_ID}-{socket.gethostname()}"
BLOCK_MS = 5_000

logger = structlog.get_logger()


async def bootstrap(redis: Redis) -> None:
    """Create the consumer group for the auth.user.registered stream if absent.

    Args:
        redis: The Redis client to use for stream group creation.
    """
    try:
        await redis.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except ResponseError:
        pass


async def handle(data: dict[str, str], session: AsyncSession) -> None:
    """Process a single auth.user.registered event.

    Creates a new UserProfile and a default UserPreference row for the
    registered user. Skips processing if a profile already exists (idempotent).

    Args:
        data: The raw message data from the Redis stream, expected to contain
            at least ``user_id`` and optionally ``email``.
        session: The database session to use for writes.
    """
    user_id = uuid.UUID(data["user_id"])
    existing = (await session.execute(select(UserProfile).where(UserProfile.id == user_id))).scalar_one_or_none()
    if existing:
        return

    email = data.get("email", "")
    display_name = email.split("@")[0] if "@" in email else f"user-{str(user_id)[:8]}"
    profile = UserProfile(id=user_id, display_name=display_name)
    session.add(profile)
    await session.flush()
    prefs = UserPreference(user_id=user_id)
    session.add(prefs)
    await session.commit()


async def run(redis: Redis) -> None:
    """Continuously consume messages from the auth.user.registered stream.

    Bootstraps the consumer group on first run, then enters an infinite loop
    reading batches of up to 10 messages. Acknowledges each message after
    successful processing and logs failures without stopping the loop.

    Args:
        redis: The Redis client used for stream reads and acknowledgements.
    """
    await bootstrap(redis)
    while True:
        results = await redis.xreadgroup(GROUP, WORKER, {STREAM: ">"}, count=10, block=BLOCK_MS)
        for _, messages in results or []:
            for msg_id, data in messages:
                try:
                    async with AsyncSessionLocal() as session:
                        await handle(data, session)
                    await redis.xack(STREAM, GROUP, msg_id)
                except Exception:
                    logger.exception("auth_user_registered_consume_failed", msg_id=msg_id)
