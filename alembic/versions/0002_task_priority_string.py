"""Store task priority as string enum.

Revision ID: 0002_task_priority_string
Revises: 0001_initial_schema
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_task_priority_string"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "tasks",
        "priority",
        existing_type=sa.Integer(),
        type_=sa.String(length=32),
        existing_nullable=False,
        postgresql_using=(
            "case priority "
            "when 0 then 'low' "
            "when 1 then 'normal' "
            "when 2 then 'important' "
            "when 3 then 'urgent' "
            "else 'normal' end"
        ),
    )


def downgrade() -> None:
    op.alter_column(
        "tasks",
        "priority",
        existing_type=sa.String(length=32),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using=(
            "case priority "
            "when 'low' then 0 "
            "when 'normal' then 1 "
            "when 'important' then 2 "
            "when 'urgent' then 3 "
            "else 1 end"
        ),
    )
