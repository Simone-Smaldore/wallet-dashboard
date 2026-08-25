"""add monthly savings target

Nullable on purpose: null means "I have not set a target", which is a different
statement from a target of zero. Defaulting it to 0 would make every household
start out already failing an objective nobody chose.

Revision ID: a5fa7907b274
Revises: 0200ac14b92a
Create Date: 2026-08-25 21:10:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a5fa7907b274'
down_revision: str | None = '0200ac14b92a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'household',
        sa.Column('monthly_savings_target_cents', sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('household', 'monthly_savings_target_cents')
