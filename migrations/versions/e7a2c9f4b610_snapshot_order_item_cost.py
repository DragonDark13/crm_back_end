"""Persist order-item unit-cost snapshots for accurate historical profit.

Revision ID: e7a2c9f4b610
Revises: c6f1d8a9b420, d1e5f7a9c240
"""

from alembic import op
import sqlalchemy as sa


revision = "e7a2c9f4b610"
down_revision = ("c6f1d8a9b420", "d1e5f7a9c240")
branch_labels = None
depends_on = None


def upgrade():
    # Nullable for legacy orders: their original cost cannot be reconstructed
    # reliably. Completion of such orders is blocked until the snapshot exists.
    op.add_column(
        "order_items",
        sa.Column("unit_cost", sa.Numeric(12, 3), nullable=True),
    )


def downgrade():
    op.drop_column("order_items", "unit_cost")
