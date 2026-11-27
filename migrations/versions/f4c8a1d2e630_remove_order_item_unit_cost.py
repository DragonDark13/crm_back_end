"""Remove the incorrect order-item purchase-price snapshot.

Revision ID: f4c8a1d2e630
Revises: e7a2c9f4b610
"""

from alembic import op
import sqlalchemy as sa


revision = "f4c8a1d2e630"
down_revision = "e7a2c9f4b610"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("order_items", "unit_cost")


def downgrade():
    op.add_column(
        "order_items",
        sa.Column("unit_cost", sa.Numeric(12, 3), nullable=True),
    )
