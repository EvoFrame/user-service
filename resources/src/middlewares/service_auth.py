from datetime import timedelta

import jwt
import structlog
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.config.settings import settings

logger = structlog.get_logger()


class ServiceAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that validates inbound service-to-service JWT tokens.

    Exempt paths (health, docs, metrics, etc.) bypass validation. In debug
    mode the check can be skipped entirely with ``SKIP_SERVICE_AUTH=true``.
    Valid tokens must carry ``type=service`` and ``scope=internal`` claims.
    """

    _EXEMPT_PREFIXES = (
        "/health",
        "/docs",
        "/openapi",
        "/metrics",
        "/redoc",
    )

    async def dispatch(self, request: Request, call_next):
        """Validate the X-Service-Token bearer JWT before passing the request downstream.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler in the chain.

        Returns:
            The downstream response for authorized requests, or a 403 JSON
            response for unauthorized or invalid tokens.
        """
        if any(request.url.path.startswith(prefix) for prefix in self._EXEMPT_PREFIXES):
            return await call_next(request)

        if settings.DEBUG and settings.SKIP_SERVICE_AUTH:
            logger.warning("service_auth_bypassed", path=request.url.path)
            return await call_next(request)

        header = request.headers.get("X-Service-Token", "")
        if not header.startswith("Bearer "):
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})

        raw_token = header.removeprefix("Bearer ")
        try:
            payload = jwt.decode(
                raw_token,
                settings.RS256_PUBLIC_KEY,
                algorithms=["RS256"],
                leeway=timedelta(seconds=10),
            )
        except jwt.ExpiredSignatureError:
            return JSONResponse(status_code=403, content={"detail": "Service token expired"})
        except jwt.InvalidTokenError:
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})

        if payload.get("type") != "service" or payload.get("scope") != "internal":
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})

        request.state.caller_service = payload["sub"]
        return await call_next(request)
