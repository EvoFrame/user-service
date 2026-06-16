from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Structured error payload included in API error responses.

    Attributes:
        code: A machine-readable error code (e.g. ``USER_NOT_FOUND``).
        message: A human-readable description of the error.
        request_id: The request correlation ID, if available.
    """

    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    """Top-level envelope for API error responses.

    Attributes:
        error: The detailed error information.
    """

    error: ErrorDetail


class AppError(Exception):
    """Application-level exception that maps directly to an HTTP error response.

    Attributes:
        code: Machine-readable error code.
        message: Human-readable error description.
        status_code: HTTP status code to return to the client.
    """

    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI application.

    Handles :class:`AppError` instances with their declared status code, and
    converts all other unhandled exceptions into a generic 500 response.

    Args:
        app: The FastAPI application instance to register the handlers on.
    """

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )
