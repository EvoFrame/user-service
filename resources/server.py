from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from prometheus_fastapi_instrumentator import Instrumentator
from src.config.logging import configure_logging
from src.config.settings import settings
from src.events.consumers import start_all_consumers
from src.libs.errors import register_exception_handlers
from src.libs.health import health_router
from src.libs.service_token_cache import ServiceTokenCache
from src.middlewares.logging import LoggingMiddleware
from src.middlewares.request_id import RequestIdMiddleware
from src.middlewares.service_auth import ServiceAuthMiddleware
from src.redis.client import get_redis
from src.routers import router

configure_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events.

    On startup: initialises Redis, warms the service token cache, and starts
    background event consumers.
    On shutdown: closes the Redis connection.

    Args:
        app: The FastAPI application instance.

    Yields:
        Control to the running application.
    """
    redis = await get_redis()
    app.state.redis = redis
    app.state.service_token = ServiceTokenCache(redis)
    await start_all_consumers(redis)
    try:
        await app.state.service_token.get()
    except Exception as exc:
        logger.warning("service_token_warm_cache_failed", error=str(exc))
    yield
    await redis.aclose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Registers all middleware, exception handlers, routers, and Prometheus
    instrumentation. In debug mode, Swagger UI, ReDoc, and a custom OpenAPI
    schema with service token security are also enabled.

    Returns:
        A fully configured FastAPI application instance.
    """
    app = FastAPI(
        title=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(ServiceAuthMiddleware)

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(router, prefix="/api/v1")
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", tags=["Metrics"])

    def custom_openapi():
        """Return a cached OpenAPI schema with the X-Service-Token security scheme."""
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        schema.setdefault("components", {})["securitySchemes"] = {
            "ServiceTokenAuth": {"type": "apiKey", "in": "header", "name": "X-Service-Token"}
        }
        app.openapi_schema = schema
        return schema

    if settings.DEBUG:
        app.openapi = custom_openapi  # type: ignore[method-assign]

    return app


app = create_app()
