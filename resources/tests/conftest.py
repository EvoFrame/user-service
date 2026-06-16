"""Test fixtures: containerised Postgres + Redis, FastAPI test client.

Containers are started at conftest import time so that os.environ is
populated BEFORE any src.* module is imported — pydantic-settings reads
env vars when Settings() is first instantiated.
"""

import atexit
import os
import uuid

import pytest_asyncio
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import select
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

# ── Start containers eagerly — BEFORE any src.* import ───────────────────────
_pg_ctr = PostgresContainer("postgres:16-alpine")
_redis_ctr = RedisContainer("redis:7-alpine")
_pg_ctr.start()
_redis_ctr.start()
atexit.register(_pg_ctr.stop)
atexit.register(_redis_ctr.stop)

os.environ.update(
    {
        "DATABASE_URL": _pg_ctr.get_connection_url().replace("psycopg2", "asyncpg"),
        "REDIS_URL": f"redis://{_redis_ctr.get_container_host_ip()}:{_redis_ctr.get_exposed_port(6379)}/0",
        "SERVICE_SECRET": "test-secret",
        "RS256_PUBLIC_KEY": "-----BEGIN PUBLIC KEY-----\\nTEST\\n-----END PUBLIC KEY-----",
        "DEBUG": "true",
        "SKIP_SERVICE_AUTH": "true",
    }
)

# Safe to import src.* now
from src.db.base import Base  # noqa: E402
from src.models.user_profile import UserPreference, UserProfile  # noqa: E402

_TEST_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest_asyncio.fixture(scope="session")
async def db_engine() -> AsyncEngine:
    """Session-scoped Postgres engine with all tables created."""
    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def redis_client() -> Redis:
    """Session-scoped Redis client connected to the test container."""
    client = aioredis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture(scope="session")
async def client(db_engine: AsyncEngine, redis_client: Redis) -> AsyncClient:
    """Session-scoped ASGI test client with seeded test user."""
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        existing = (
            await session.execute(select(UserProfile).where(UserProfile.id == _TEST_USER_ID))
        ).scalar_one_or_none()
        if existing is None:
            session.add(UserProfile(id=_TEST_USER_ID, display_name="tester"))
            await session.flush()
        existing_prefs = (
            await session.execute(select(UserPreference).where(UserPreference.user_id == _TEST_USER_ID))
        ).scalar_one_or_none()
        if existing_prefs is None:
            session.add(UserPreference(user_id=_TEST_USER_ID))
        await session.commit()

    from server import create_app

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
