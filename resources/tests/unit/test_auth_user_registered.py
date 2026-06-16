"""Unit tests for the auth.user.registered consumer handler."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlmodel import select

from src.events.consumers.auth_user_registered import handle
from src.models.user_profile import UserPreference, UserProfile

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_handle_creates_profile_and_prefs_from_email(db_engine: AsyncEngine):
    """A registered event with an email creates a profile and default preferences."""
    user_id = uuid.uuid4()
    data = {"user_id": str(user_id), "email": "alice@example.com"}

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        await handle(data, session)

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        profile = (await session.execute(select(UserProfile).where(UserProfile.id == user_id))).scalar_one()
        prefs = (await session.execute(select(UserPreference).where(UserPreference.user_id == user_id))).scalar_one()

    assert profile.display_name == "alice"
    assert prefs.email_notifs is True
    assert prefs.inapp_notifs is True
    assert prefs.theme == "system"


async def test_handle_creates_profile_with_fallback_display_name(db_engine: AsyncEngine):
    """A registered event without an email uses a user-id-derived display_name."""
    user_id = uuid.uuid4()
    data = {"user_id": str(user_id)}

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        await handle(data, session)

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        profile = (await session.execute(select(UserProfile).where(UserProfile.id == user_id))).scalar_one()

    assert profile.display_name == f"user-{str(user_id)[:8]}"


async def test_handle_is_idempotent(db_engine: AsyncEngine):
    """Processing the same event twice does not create duplicate records."""
    user_id = uuid.uuid4()
    data = {"user_id": str(user_id), "email": "bob@example.com"}

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        await handle(data, session)
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        await handle(data, session)

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        profiles = (await session.execute(select(UserProfile).where(UserProfile.id == user_id))).all()

    assert len(profiles) == 1
