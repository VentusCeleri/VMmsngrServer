"""Pair management lifecycle.

Revision ID: 0004_pair_management
Revises: 0003_profiles_presence
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_pair_management"
down_revision: str | None = "0003_profiles_presence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "pairs",
        "user_a_id",
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        """
        delete from pairs
        where user_a_id is null
        """
    )
    op.alter_column(
        "pairs",
        "user_a_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
