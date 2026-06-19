# Copilot Instructions — user-service

## Project overview

`user-service` is the **user profile and preferences service** for the EvoFrame platform.
It is a Python/FastAPI application that handles:

- User profile storage (`display_name`, `bio`, avatar URL, locale, timezone)
- User preference management (notifications, UI theme)
- Avatar upload delegation to `file-service`
- Consuming `auth.user.registered` events to provision profiles on signup
- Publishing `user.profile.updated` and `user.account.deleted` events to Redis Streams

## Tech stack

| Concern | Choice |
|---|---|
| Framework | FastAPI + Uvicorn/Gunicorn |
| ORM / models | SQLModel (SQLAlchemy async) |
| Database | PostgreSQL (asyncpg driver) |
| Cache / events | Redis (redis-py async) |
| Migrations | Alembic |
| JWT validation | PyJWT (RS256 public key only — no private key) |
| Settings | pydantic-settings (`.env` + `.env.local`) |
| Logging | structlog (structured JSON) |
| Metrics | prometheus-fastapi-instrumentator (`/metrics`) |
| Task runner | mise (tasks) |
| Package manager | uv |
| Dev environment | mise |
| Linter/formatter | Ruff |
| Tests | pytest-asyncio + testcontainers (Postgres + Redis) |

## Repository layout

```
resources/
  server.py               # App factory — create_app(), lifespan
  src/
    config/
      settings.py         # Pydantic-settings Settings singleton
      logging.py          # structlog configuration
    controllers/          # Business logic (no HTTP concerns)
      user_profile.py     # Profile CRUD, preference updates, avatar delegation
    routers/              # FastAPI route handlers (thin; delegate to controllers)
      users.py
    schemas/              # Pydantic request/response schemas
      user_profile.py
    models/               # SQLModel table models
      user_profile.py     # UserProfile, UserPreference
    libs/
      auth_context.py     # UserContext + get_user_context() FastAPI dep (gateway headers)
      errors.py           # AppError exception + register_exception_handlers()
      health.py           # /health router
      s2s_client.py       # HTTP client for outbound service-to-service calls
      service_token_cache.py  # Redis-backed service token cache
    middlewares/
      service_auth.py     # Validates X-Service-Token on every non-exempt route
      logging.py          # Structured request/response logging
      request_id.py       # Injects X-Request-ID into request state
    db/
      session.py          # get_session() async dependency
      base.py             # SQLAlchemy engine setup
    redis/
      client.py           # get_redis() async dependency
    events/
      publisher.py        # EventPublisher — publishes to Redis Streams
      consumers/          # Redis Stream consumers (started at lifespan)
        auth_user_registered.py  # Provisions UserProfile + UserPreference on signup
    tasks/                # Background tasks (APScheduler hooks, reserved)
  tests/
    conftest.py           # Session-scoped testcontainers (Postgres + Redis), async client
    integration/          # End-to-end HTTP tests via ASGI client
    unit/                 # Pure logic tests
resources/migrations/     # Alembic migration scripts
```

## Key architecture rules

1. **Routers are thin** — all logic lives in `controllers/`. Routers validate input,
   call the controller, and return the response.

2. **AppError everywhere** — raise `AppError(code, message, status_code)` for all
   expected error conditions. Never raise `HTTPException` directly.

3. **Identity comes from gateway headers** — user identity is extracted from
   `X-User-Id` and `X-User-Roles` headers injected by the API gateway after JWT
   validation. `user-service` never validates JWTs on behalf of end users.

4. **Service auth is enforced by middleware** — all routes except
   `/health`, `/docs`, `/openapi`, `/metrics`, and `/redoc` require a valid
   `X-Service-Token: Bearer <jwt>` header. In tests this is bypassed via
   `SKIP_SERVICE_AUTH=true`.

5. **RS256 public key only** — `user-service` never holds the private key.
   It uses `RS256_PUBLIC_KEY` solely for service token validation in
   `ServiceAuthMiddleware`.

6. **Audit columns last** — all SQLModel table classes end with
   `created_at`, `updated_at`, and optionally `deleted_at`.

7. **Soft deletes on profiles** — `UserProfile.is_deleted` / `deleted_at` is set
   instead of hard-deleting rows.

8. **Event consumer is idempotent** — `auth_user_registered` checks for an existing
   profile before inserting to handle duplicate deliveries safely.

## Common patterns

### Add a new endpoint

1. Add schema(s) in `schemas/user_profile.py`
2. Add business logic in `controllers/user_profile.py`
3. Add route in `routers/users.py` using `Depends(get_user_context)` for auth

### Raise an error

```python
from src.libs.errors import AppError

raise AppError("SOME_CODE", "Human-readable message.", status_code=404)
```

### Access the database

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_session

async def my_endpoint(session: AsyncSession = Depends(get_session)):
    ...
```

### Publish an event

```python
from src.events.publisher import EventPublisher

publisher = EventPublisher(request.app.state.redis)
await publisher.publish("user.some.event", {"key": "value"})
```

### Make a service-to-service call

```python
from src.libs.s2s_client import S2SClient

s2s = S2SClient(base_url=settings.FILE_SERVICE_URL, token_cache=request.app.state.service_token)
response = await s2s.post("/api/v1/some/path", json={...})
```

## Running the project

```bash
# One-time setup
mise run setup                      # init env files + generate local RSA public key
mise run setup:init-env             # copy *.example env files only
mise run setup:generate-public-key  # (re)generate local key pair → RS256_PUBLIC_KEY injected into .env

# Daily dev
mise run dev                # start infra (db + redis) + migrate + dev server

# Stack management
mise run stack:up               # start infra only (db + redis)
mise run stack:up --services    # start infra + app container
mise run stack:up --ui          # + pgAdmin + RedisInsight
mise run stack:up --monitoring  # + Prometheus + Grafana + Loki
mise run stack:down             # stop and remove all containers

# Testing
mise run test:run               # full suite with coverage
mise run test:unit              # unit tests only
mise run test:integration       # integration tests only

# Database
mise run db:migrate             # apply pending Alembic migrations
mise run db:new                 # generate a new migration (pass name as arg)
mise run db:rollback            # rollback one step
mise run db:seed                # seed default data

# Linting
mise run lint:check             # ruff check (report only)
mise run lint:fix               # auto-fix lint issues
mise run lint:format            # fix imports + reformat

# Dependencies
mise run deps:sync              # sync from uv.lock
mise run deps:add               # add a runtime dep
mise run deps:add-dev           # add a dev dep
mise run deps:update            # upgrade all deps

# Docker helpers
mise run docker:logs [service]  # follow logs (all containers or one)
mise run docker:ps              # list container status
mise run docker:build           # rebuild app image
mise run docker:clean           # ⚠ remove all containers + volumes
```

## Environment variables (required)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | asyncpg PostgreSQL URL |
| `REDIS_URL` | Redis URL |
| `RS256_PUBLIC_KEY` | PEM public key (for service token validation) |
| `SERVICE_SECRET` | Shared secret for obtaining service tokens from auth-service |

Optional: `AUTH_SERVICE_URL`, `FILE_SERVICE_URL`, `DEBUG`, `SKIP_SERVICE_AUTH`, `LOG_LEVEL`

## Testing conventions

- All tests use a **session-scoped** ASGI `AsyncClient` (no real HTTP server).
- Testcontainers spin up real Postgres + Redis containers — no mocking of DB/Redis.
- Containers are started **before any `src.*` import** in `conftest.py` so
  `pydantic-settings` picks up the correct env vars.
- `SKIP_SERVICE_AUTH=true` bypasses `X-Service-Token` validation in tests.
- Test files mirror the source structure: `tests/integration/test_<feature>.py`.
- Fixtures are defined in `tests/conftest.py` (session scope by default).

## Code style

- Formatter: Ruff (`line-length = 120`, `quote-style = "double"`)
- Linting rules: `E`, `F`, `I` (isort), `UP` (pyupgrade)
- Python ≥ 3.13; use modern typing (`str | None`, `list[str]`, etc.)
- Docstrings: Google-style, on all public functions and classes
