import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.controllers import user_profile as profile_ctrl
from src.db.session import get_session
from src.events.publisher import EventPublisher
from src.libs.auth_context import UserContext, get_user_context
from src.libs.s2s_client import S2SClient
from src.redis.client import get_redis
from src.schemas.user_profile import (
    AvatarDelegationRequest,
    AvatarDelegationResponse,
    PublicUserProfileResponse,
    UserPreferencesResponse,
    UserPreferencesUpdateRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
)


async def _publisher(redis=Depends(get_redis)) -> EventPublisher:
    """FastAPI dependency that constructs an EventPublisher from the Redis client.

    Args:
        redis: Injected Redis connection.

    Returns:
        An EventPublisher bound to the current Redis connection.
    """
    return EventPublisher(redis)


def _s2s_client(request: Request) -> S2SClient:
    """FastAPI dependency that constructs an S2SClient for the file service.

    Args:
        request: The current FastAPI request, used to access app-level state.

    Returns:
        An S2SClient configured for the file service URL with the cached service token.
    """
    token_cache = request.app.state.service_token
    return S2SClient(base_url=settings.FILE_SERVICE_URL, token_cache=token_cache)


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    ctx: UserContext = Depends(get_user_context),
    session: AsyncSession = Depends(get_session),
):
    return await profile_ctrl.get_me(ctx, session)


@router.patch("/me", response_model=UserProfileResponse)
async def patch_me(
    body: UserProfileUpdateRequest,
    ctx: UserContext = Depends(get_user_context),
    session: AsyncSession = Depends(get_session),
    publisher: EventPublisher = Depends(_publisher),
):
    return await profile_ctrl.update_me(ctx, body, session, publisher)


@router.delete("/me")
async def delete_me(
    ctx: UserContext = Depends(get_user_context),
    session: AsyncSession = Depends(get_session),
    publisher: EventPublisher = Depends(_publisher),
):
    return await profile_ctrl.delete_me(ctx, session, publisher)


@router.get("/{user_id}", response_model=PublicUserProfileResponse)
async def get_user(
    user_id: uuid.UUID,
    ctx: UserContext = Depends(get_user_context),
    session: AsyncSession = Depends(get_session),
):
    return await profile_ctrl.get_public_profile(user_id, ctx, session)


@router.get("/me/preferences", response_model=UserPreferencesResponse)
async def get_preferences(
    ctx: UserContext = Depends(get_user_context),
    session: AsyncSession = Depends(get_session),
):
    return await profile_ctrl.get_preferences(ctx, session)


@router.patch("/me/preferences", response_model=UserPreferencesResponse)
async def patch_preferences(
    body: UserPreferencesUpdateRequest,
    ctx: UserContext = Depends(get_user_context),
    session: AsyncSession = Depends(get_session),
    publisher: EventPublisher = Depends(_publisher),
):
    return await profile_ctrl.update_preferences(ctx, body, session, publisher)


@router.post("/me/avatar", response_model=AvatarDelegationResponse)
async def upload_avatar(
    body: AvatarDelegationRequest,
    ctx: UserContext = Depends(get_user_context),
    session: AsyncSession = Depends(get_session),
    s2s: S2SClient = Depends(_s2s_client),
):
    return await profile_ctrl.delegate_avatar_upload(ctx, body, s2s, session)
