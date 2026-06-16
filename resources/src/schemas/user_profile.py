import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    """Full user profile response schema returned to the authenticated user."""

    id: uuid.UUID
    display_name: str
    bio: str | None
    avatar_url: str | None
    timezone: str
    locale: str
    is_deleted: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PublicUserProfileResponse(BaseModel):
    """Public user profile response schema with only non-sensitive fields."""

    id: uuid.UUID
    display_name: str
    bio: str | None
    avatar_url: str | None
    locale: str

    model_config = {"from_attributes": True}


class UserProfileUpdateRequest(BaseModel):
    """Request body for partially updating a user's profile."""

    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    bio: str | None = Field(default=None, max_length=300)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    locale: str | None = Field(default=None, min_length=2, max_length=16)


class UserPreferencesResponse(BaseModel):
    """User preferences response schema."""

    user_id: uuid.UUID
    email_notifs: bool
    inapp_notifs: bool
    theme: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserPreferencesUpdateRequest(BaseModel):
    """Request body for partially updating a user's preferences."""

    email_notifs: bool | None = None
    inapp_notifs: bool | None = None
    theme: str | None = Field(default=None, min_length=1, max_length=16)


class AvatarDelegationRequest(BaseModel):
    """Request body for delegating an avatar upload to the file service."""

    content_type: str
    file_name: str
    size_bytes: int = Field(gt=0)


class AvatarDelegationResponse(BaseModel):
    """Response containing pre-signed upload details from the file service."""

    upload_url: str
    file_key: str
    expires_in: int
