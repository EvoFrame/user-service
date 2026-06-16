"""initial

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users_profile",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("bio", sa.String(), nullable=True),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("timezone", sa.String(), nullable=False, server_default="UTC"),
        sa.Column("locale", sa.String(), nullable=False, server_default="en"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_profile_deleted_at", "users_profile", ["deleted_at"])

    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("email_notifs", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("inapp_notifs", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("theme", sa.String(), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users_profile.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_preferences")
    op.drop_index("ix_users_profile_deleted_at", table_name="users_profile")
    op.drop_table("users_profile")
