"""Add inventory reconciliation date to stock history.

Revision ID: c9d4e7a1b630
Revises: f2c7a91e6b40
"""

from alembic import op
import sqlalchemy as sa


revision = "c9d4e7a1b630"
down_revision = "f2c7a91e6b40"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "stock_history",
        sa.Column("inventory_date", sa.Date(), nullable=True),
    )


def downgrade():
    op.drop_column("stock_history", "inventory_date")
