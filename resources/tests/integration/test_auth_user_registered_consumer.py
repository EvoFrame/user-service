"""Integration tests for the auth.user.registered consumer (end-to-end)."""

import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlmodel import select

from src.events.consumers.auth_user_registered import run
from src.models.user_profile import UserPreference, UserProfile

pytestmark = pytest.mark.asyncio(loop_scope="session")

STREAM = "auth.user.registered"
_PROCESSING_TIME = 1.5  # seconds to allow one consumer iteration to complete


async def _publish_and_consume(redis_client: Redis, payload: dict) -> None:
    """Write a message to the stream, run the consumer briefly, then cancel it."""
    await redis_client.xadd(STREAM, payload)
    task = asyncio.create_task(run(redis_client))
    await asyncio.sleep(_PROCESSING_TIME)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def test_consumer_creates_profile_from_stream_event(db_engine: AsyncEngine, redis_client: Redis):
    """The run loop picks up an auth.user.registered message and creates a UserProfile."""
    user_id = uuid.uuid4()
    await _publish_and_consume(
        redis_client,
        {
            "user_id": str(user_id),
            "email": "integration@example.com",
            "source_service": "auth-service",
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        profile = (await session.execute(select(UserProfile).where(UserProfile.id == user_id))).scalar_one_or_none()

    assert profile is not None
    assert profile.display_name == "integration"


async def test_consumer_creates_prefs_alongside_profile(db_engine: AsyncEngine, redis_client: Redis):
    """The run loop also creates a default UserPreference row for the new user."""
    user_id = uuid.uuid4()
    await _publish_and_consume(
        redis_client,
        {
            "user_id": str(user_id),
            "email": "prefs.test@example.com",
            "source_service": "auth-service",
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        prefs = (
            await session.execute(select(UserPreference).where(UserPreference.user_id == user_id))
        ).scalar_one_or_none()

    assert prefs is not None
    assert prefs.email_notifs is True
    assert prefs.inapp_notifs is True
    assert prefs.theme == "system"
