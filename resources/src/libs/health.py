from fastapi import APIRouter, Request

health_router = APIRouter(tags=["Health"])


@health_router.get("/health/live")
async def live() -> dict[str, str]:
    """Liveness probe — always returns 200 to indicate the process is running."""
    return {"status": "ok"}


@health_router.get("/health/ready")
async def ready(request: Request) -> dict[str, str]:
    """Readiness probe — verifies the Redis connection before returning 200.

    Args:
        request: The current FastAPI request, used to access app-level state.

    Returns:
        ``{"status": "ok"}`` when Redis is reachable.

    Raises:
        Exception: Propagates any Redis connection error, resulting in a 500 response.
    """
    await request.app.state.redis.ping()
    return {"status": "ok"}
