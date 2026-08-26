"""add asset and asset_valuation

An investment account's balance is the capital paid into it, derived from the
movements. What it is worth today is a different fact, and it lives here: a
quantity that rarely changes, and a price that changes every minute.

⚠️ `quantity` is NUMERIC(28, 8) — the only decimal column in the schema. A
bitcoin is counted to eight places; integers do not reach and the scale is not
money's. `value_cents` stays an integer, like every other amount.

Revision ID: 4a1e1d5476ff
Revises: cf58aa978b71
Create Date: 2026-08-26 12:20:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '4a1e1d5476ff'
down_revision: str | None = 'cf58aa978b71'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'asset',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('household_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=28, scale=8), nullable=False),
        sa.Column('price_basis', sa.String(length=24), nullable=False),
        sa.Column('source', sa.String(length=24), nullable=False),
        sa.Column('source_ref', sa.String(length=60), nullable=True),
        sa.Column('opened_at', sa.Date(), nullable=True),
        sa.Column('closed_at', sa.Date(), nullable=True),
        sa.Column('notes', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['account.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['household_id'], ['household.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('household_id', 'name', name='uq_asset_household_name'),
    )
    op.create_index('ix_asset_household_id', 'asset', ['household_id'])
    op.create_index('ix_asset_household_account', 'asset', ['household_id', 'account_id'])

    op.create_table(
        'asset_valuation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('unit_price_cents', sa.BigInteger(), nullable=True),
        sa.Column('value_cents', sa.BigInteger(), nullable=False),
        sa.Column('source', sa.String(length=24), nullable=False),
        sa.Column('imported_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['asset.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        # One per asset per day: a second fetch is a correction, not a new point.
        sa.UniqueConstraint('asset_id', 'date', name='uq_asset_valuation_asset_date'),
    )
    op.create_index('ix_asset_valuation_asset_id', 'asset_valuation', ['asset_id'])


def downgrade() -> None:
    op.drop_table('asset_valuation')
    op.drop_table('asset')
