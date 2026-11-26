"""Store immutable gift set sale cost and profit snapshots.

Revision ID: c6f1d8a9b420
Revises: 3ee5783020b2
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c6f1d8a9b420"
down_revision: Union[str, Sequence[str], None] = "3ee5783020b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "gift_set_sales_history",
        sa.Column("cost_price", sa.Numeric(12, 3), nullable=True),
    )
    op.add_column(
        "gift_set_sales_history",
        sa.Column("profit", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "gift_set_sales_history_product",
        sa.Column("unit_cost", sa.Numeric(12, 3), nullable=True),
    )
    op.add_column(
        "gift_set_sales_history_packaging",
        sa.Column("unit_cost", sa.Numeric(12, 3), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("gift_set_sales_history_packaging", "unit_cost")
    op.drop_column("gift_set_sales_history_product", "unit_cost")
    op.drop_column("gift_set_sales_history", "profit")
    op.drop_column("gift_set_sales_history", "cost_price")
    op.drop_column("products", "is_archived")
