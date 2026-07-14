"""Profiles, presence and string task priority.

Revision ID: 0003_profiles_presence
Revises: 0002_task_priority_string
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_profiles_presence"
down_revision: str | None = "0002_task_priority_string"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=30), nullable=True))
    op.add_column("users", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        """
        update users
        set username = left(
            trim(both '.' from regexp_replace(lower(split_part(email, '@', 1)), '[^a-z0-9_.]+', '.', 'g'))
            || '.' || left(replace(id::text, '-', ''), 10),
            30
        )
        where username is null
        """
    )
    op.execute("update users set username = 'user.' || left(replace(id::text, '-', ''), 10) where username = ''")
    op.alter_column("users", "username", nullable=False)
    op.alter_column("users", "display_name", existing_type=sa.String(length=120), type_=sa.String(length=50))
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index("ux_users_username_lower", "users", [sa.text("lower(username)")], unique=True)


def downgrade() -> None:
    op.drop_index("ux_users_username_lower", table_name="users")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.alter_column("users", "display_name", existing_type=sa.String(length=50), type_=sa.String(length=120))
    op.drop_column("users", "last_seen_at")
    op.drop_column("users", "username")
