import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey
from sqlmodel import Field, SQLModel


class UserProfile(SQLModel, table=True):
    """ORM model representing a user's profile record.

    Attributes:
        id: The user's UUID, shared with the auth service.
        display_name: Publicly visible display name.
        bio: Optional short biography text.
        avatar_url: Optional URL pointing to the user's avatar image.
        timezone: IANA timezone string (default ``"UTC"``).
        locale: BCP 47 language tag (default ``"en"``).
        is_deleted: Soft-delete flag.
        deleted_at: Timestamp of soft-deletion, if applicable.
        created_at: Creation timestamp (UTC).
        updated_at: Last-modification timestamp (UTC).
    """

    __tablename__ = "users_profile"

    id: uuid.UUID = Field(primary_key=True)
    display_name: str = Field(nullable=False)
    bio: str | None = Field(default=None, nullable=True)
    avatar_url: str | None = Field(default=None, nullable=True)
    timezone: str = Field(default="UTC", nullable=False)
    locale: str = Field(default="en", nullable=False)
    is_deleted: bool = Field(default=False, nullable=False)
    deleted_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True), nullable=True, default=None))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=lambda: datetime.now(UTC),
            onupdate=lambda: datetime.now(UTC),
        )
    )


class UserPreference(SQLModel, table=True):
    """ORM model representing a user's configurable preferences.

    Attributes:
        user_id: Foreign key referencing :class:`UserProfile`.
        email_notifs: Whether the user receives email notifications.
        inapp_notifs: Whether the user receives in-app notifications.
        theme: UI theme preference (e.g. ``"system"``, ``"light"``, ``"dark"``).
        created_at: Creation timestamp (UTC).
        updated_at: Last-modification timestamp (UTC).
    """

    __tablename__ = "user_preferences"

    user_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("users_profile.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    )
    email_notifs: bool = Field(default=True, nullable=False)
    inapp_notifs: bool = Field(default=True, nullable=False)
    theme: str = Field(default="system", nullable=False)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=lambda: datetime.now(UTC),
            onupdate=lambda: datetime.now(UTC),
        )
    )
