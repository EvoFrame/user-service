import uuid

from fastapi import Header

from src.libs.errors import AppError


class UserContext:
    """Holds identity and role information for an authenticated user.

    Attributes:
        user_id: The authenticated user's UUID.
        roles: The set of roles assigned to the user.
    """

    def __init__(self, user_id: uuid.UUID, roles: set[str]):
        self.user_id = user_id
        self.roles = roles

    @property
    def is_admin(self) -> bool:
        """Return True if the user has the ``admin`` role."""
        return "admin" in self.roles


async def get_user_context(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_roles: str | None = Header(default="", alias="X-User-Roles"),
) -> UserContext:
    """FastAPI dependency that extracts user identity from gateway-injected headers.

    Args:
        x_user_id: Value of the ``X-User-Id`` header, expected to be a valid UUID.
        x_user_roles: Value of the ``X-User-Roles`` header, comma-separated role names.

    Returns:
        A UserContext populated with the parsed user ID and roles.

    Raises:
        AppError: If the ``X-User-Id`` header is absent or not a valid UUID.
    """
    if not x_user_id:
        raise AppError("MISSING_USER_CONTEXT", "Missing gateway identity headers.", status_code=401)
    try:
        user_id = uuid.UUID(x_user_id)
    except ValueError as exc:
        raise AppError("INVALID_USER_ID", "Invalid user id header.", status_code=401) from exc

    roles = {role.strip() for role in x_user_roles.split(",") if role.strip()}
    return UserContext(user_id=user_id, roles=roles)
