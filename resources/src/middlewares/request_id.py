import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns a unique request ID to every incoming request.

    Reads the ``X-Request-ID`` header if present; otherwise generates a new
    UUID. Stores the value on ``request.state.request_id`` and echoes it back
    in the response headers.
    """

    async def dispatch(self, request: Request, call_next):
        """Attach a request ID to the request state and response headers.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler in the chain.

        Returns:
            The response with the ``X-Request-ID`` header set.
        """
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
