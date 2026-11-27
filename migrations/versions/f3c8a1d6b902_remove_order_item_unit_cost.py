"""Remove the incorrect order-creation purchase-price snapshot.

Revision ID: f3c8a1d6b902
Revises: e7a2c9f4b610
"""

from alembic import op
import sqlalchemy as sa


revision = "f3c8a1d6b902"
down_revision = "e7a2c9f4b610"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("order_items", "unit_cost")


def downgrade():
    # The removed values were captured at order creation and are not valid
    # historical purchase prices for completed sales.
    op.add_column(
        "order_items",
        sa.Column("unit_cost", sa.Numeric(12, 3), nullable=True),
    )
