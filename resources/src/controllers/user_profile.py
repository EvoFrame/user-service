import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.events.publisher import EventPublisher
from src.libs.auth_context import UserContext
from src.libs.errors import AppError
from src.libs.s2s_client import S2SClient
from src.models.user_profile import UserPreference, UserProfile
from src.schemas.user_profile import (
    AvatarDelegationRequest,
    AvatarDelegationResponse,
    PublicUserProfileResponse,
    UserPreferencesResponse,
    UserPreferencesUpdateRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
)


async def get_me(ctx: UserContext, session: AsyncSession) -> UserProfileResponse:
    """Fetch the authenticated user's own profile.

    Args:
        ctx: The authenticated user's context.
        session: The database session.

    Returns:
        The user's profile data.

    Raises:
        AppError: If the profile is not found or has been soft-deleted.
    """
    profile = (await session.execute(select(UserProfile).where(UserProfile.id == ctx.user_id))).scalar_one_or_none()
    if not profile or profile.is_deleted:
        raise AppError("USER_NOT_FOUND", "User profile not found.", status_code=404)
    return UserProfileResponse.model_validate(profile)


async def update_me(
    ctx: UserContext,
    body: UserProfileUpdateRequest,
    session: AsyncSession,
    publisher: EventPublisher,
) -> UserProfileResponse:
    """Update the authenticated user's profile fields.

    Only fields explicitly included in the request body are updated. A
    ``user.profile.updated`` event is published when at least one field changes.

    Args:
        ctx: The authenticated user's context.
        body: Partial profile update payload.
        session: The database session.
        publisher: Event publisher for emitting domain events.

    Returns:
        The updated user profile.

    Raises:
        AppError: If the profile is not found or has been soft-deleted.
    """
    profile = (await session.execute(select(UserProfile).where(UserProfile.id == ctx.user_id))).scalar_one_or_none()
    if not profile or profile.is_deleted:
        raise AppError("USER_NOT_FOUND", "User profile not found.", status_code=404)

    changed_fields: list[str] = []
    payload = body.model_dump(exclude_unset=True)
    for field, value in payload.items():
        if getattr(profile, field) != value:
            setattr(profile, field, value)
            changed_fields.append(field)

    if changed_fields:
        await session.commit()
        await session.refresh(profile)
        await publisher.publish(
            "user.profile.updated",
            {
                "user_id": str(profile.id),
                "fields_changed": ",".join(changed_fields),
            },
        )

    return UserProfileResponse.model_validate(profile)


async def delete_me(ctx: UserContext, session: AsyncSession, publisher: EventPublisher) -> dict[str, str]:
    """Soft-delete the authenticated user's account.

    Sets ``is_deleted`` to ``True`` and records ``deleted_at``, then publishes a
    ``user.account.deleted`` event.

    Args:
        ctx: The authenticated user's context.
        session: The database session.
        publisher: Event publisher for emitting domain events.

    Returns:
        A dict with ``{"status": "deleted"}``.

    Raises:
        AppError: If the profile is not found or is already deleted.
    """
    profile = (await session.execute(select(UserProfile).where(UserProfile.id == ctx.user_id))).scalar_one_or_none()
    if not profile:
        raise AppError("USER_NOT_FOUND", "User profile not found.", status_code=404)
    if profile.is_deleted:
        raise AppError("USER_ALREADY_DELETED", "User profile already deleted.", status_code=409)

    profile.is_deleted = True
    profile.deleted_at = datetime.now(UTC)
    await session.commit()
    await publisher.publish("user.account.deleted", {"user_id": str(profile.id)})
    return {"status": "deleted"}


async def get_public_profile(
    target_user_id: uuid.UUID,
    ctx: UserContext,
    session: AsyncSession,
) -> PublicUserProfileResponse:
    """Fetch a user's public profile by their ID.

    Deleted profiles are only visible to admins or the profile owner.

    Args:
        target_user_id: The UUID of the profile to retrieve.
        ctx: The authenticated requesting user's context.
        session: The database session.

    Returns:
        The public-facing subset of the target user's profile.

    Raises:
        AppError: If the profile is not found or the requesting user is not
            allowed to view a deleted profile.
    """
    profile = (await session.execute(select(UserProfile).where(UserProfile.id == target_user_id))).scalar_one_or_none()
    if not profile:
        raise AppError("USER_NOT_FOUND", "User profile not found.", status_code=404)
    if profile.is_deleted and not ctx.is_admin and target_user_id != ctx.user_id:
        raise AppError("USER_NOT_FOUND", "User profile not found.", status_code=404)

    return PublicUserProfileResponse.model_validate(profile)


async def get_preferences(ctx: UserContext, session: AsyncSession) -> UserPreferencesResponse:
    """Fetch the authenticated user's notification and UI preferences.

    Args:
        ctx: The authenticated user's context.
        session: The database session.

    Returns:
        The user's preference settings.

    Raises:
        AppError: If no preference record is found for the user.
    """
    prefs = (
        await session.execute(select(UserPreference).where(UserPreference.user_id == ctx.user_id))
    ).scalar_one_or_none()
    if not prefs:
        raise AppError("PREFERENCES_NOT_FOUND", "User preferences not found.", status_code=404)
    return UserPreferencesResponse.model_validate(prefs)


async def update_preferences(
    ctx: UserContext,
    body: UserPreferencesUpdateRequest,
    session: AsyncSession,
    publisher: EventPublisher,
) -> UserPreferencesResponse:
    """Update the authenticated user's preferences.

    Only explicitly provided fields are modified. Publishes a
    ``user.profile.updated`` event when at least one preference changes.

    Args:
        ctx: The authenticated user's context.
        body: Partial preferences update payload.
        session: The database session.
        publisher: Event publisher for emitting domain events.

    Returns:
        The updated preference settings.

    Raises:
        AppError: If no preference record is found for the user.
    """
    prefs = (
        await session.execute(select(UserPreference).where(UserPreference.user_id == ctx.user_id))
    ).scalar_one_or_none()
    if not prefs:
        raise AppError("PREFERENCES_NOT_FOUND", "User preferences not found.", status_code=404)

    changed_fields: list[str] = []
    payload = body.model_dump(exclude_unset=True)
    for field, value in payload.items():
        if getattr(prefs, field) != value:
            setattr(prefs, field, value)
            changed_fields.append(f"preferences.{field}")

    if changed_fields:
        await session.commit()
        await session.refresh(prefs)
        await publisher.publish(
            "user.profile.updated",
            {
                "user_id": str(ctx.user_id),
                "fields_changed": ",".join(changed_fields),
            },
        )
    return UserPreferencesResponse.model_validate(prefs)


async def delegate_avatar_upload(
    ctx: UserContext,
    body: AvatarDelegationRequest,
    s2s_client: S2SClient,
    session: AsyncSession,
) -> AvatarDelegationResponse:
    """Delegate an avatar upload request to the file service.

    Requests a pre-signed upload URL from the file service on behalf of the
    authenticated user. If the file service returns a public URL, the profile's
    ``avatar_url`` is updated in place.

    Args:
        ctx: The authenticated user's context.
        body: Avatar upload metadata (content type, file name, size).
        s2s_client: The service-to-service HTTP client.
        session: The database session.

    Returns:
        Pre-signed upload URL, file key, and expiry seconds from the file service.

    Raises:
        AppError: If the profile is not found, soft-deleted, or the file service
            returns an error.
    """
    profile = (await session.execute(select(UserProfile).where(UserProfile.id == ctx.user_id))).scalar_one_or_none()
    if not profile or profile.is_deleted:
        raise AppError("USER_NOT_FOUND", "User profile not found.", status_code=404)

    resp = await s2s_client.post(
        "/api/v1/files/avatar/upload-url",
        json={
            "owner_user_id": str(ctx.user_id),
            "content_type": body.content_type,
            "file_name": body.file_name,
            "size_bytes": body.size_bytes,
        },
    )
    if resp.status_code >= 400:
        raise AppError("FILE_SERVICE_ERROR", "Avatar upload delegation failed.", status_code=502)

    data = resp.json()
    avatar_url = data.get("public_url")
    if avatar_url and avatar_url != profile.avatar_url:
        profile.avatar_url = avatar_url
        await session.commit()

    return AvatarDelegationResponse(
        upload_url=data["upload_url"],
        file_key=data["file_key"],
        expires_in=int(data["expires_in"]),
    )
