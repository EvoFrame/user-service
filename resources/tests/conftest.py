import os
import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import select
from src.db.base import Base
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer


@pytest_asyncio.fixture(scope="session")
async def pg_url() -> str:
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg.get_connection_url().replace("psycopg2", "asyncpg")


@pytest_asyncio.fixture(scope="session")
async def redis_url() -> str:
    with RedisContainer("redis:7-alpine") as redis:
        yield f"redis://{redis.get_container_host_ip()}:{redis.get_exposed_port(6379)}/0"


@pytest_asyncio.fixture(scope="function")
async def client(pg_url: str, redis_url: str, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("SERVICE_SECRET", "test-secret")
    monkeypatch.setenv("RS256_PUBLIC_KEY", "-----BEGIN PUBLIC KEY-----\\nTEST\\n-----END PUBLIC KEY-----")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("SKIP_SERVICE_AUTH", "true")

    engine = create_async_engine(pg_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        from src.models.user_profile import UserPreference, UserProfile

        user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        existing_profile = (
            await session.execute(select(UserProfile).where(UserProfile.id == user_id))
        ).scalar_one_or_none()
        if existing_profile is None:
            session.add(UserProfile(id=user_id, display_name="tester"))
            await session.flush()

        existing_prefs = (
            await session.execute(select(UserPreference).where(UserPreference.user_id == user_id))
        ).scalar_one_or_none()
        if existing_prefs is None:
            session.add(UserPreference(user_id=user_id))
        await session.commit()

    from server import create_app

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    async with engine.begin() as conn:
        await conn.run_sync(Base.drop_all)
    await engine.dispose()

    os.environ.pop("DEBUG", None)
