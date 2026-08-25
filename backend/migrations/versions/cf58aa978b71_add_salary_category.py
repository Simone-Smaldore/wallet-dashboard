"""add salary category

Which income category counts as the salary. The savings goal is judged salary to
salary rather than month to month, so the app has to be told which movement is a
salary instead of guessing — "any income" would let a refund open a cycle.

Nullable: not chosen yet is a real state, and the screen asks rather than
assuming.

Revision ID: cf58aa978b71
Revises: a5fa7907b274
Create Date: 2026-08-25 23:40:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'cf58aa978b71'
down_revision: str | None = 'a5fa7907b274'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'household', sa.Column('salary_category_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_household_salary_category',
        'household',
        'category',
        ['salary_category_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_household_salary_category', 'household', type_='foreignkey')
    op.drop_column('household', 'salary_category_id')
