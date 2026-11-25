"""Create product images table.

Revision ID: e3b7c9d1a520
Revises: f2a6c8d1e430
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3b7c9d1a520"
down_revision: Union[str, Sequence[str], None] = "f2a6c8d1e430"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=50), nullable=False),
        sa.Column("image_data", sa.LargeBinary(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_product_images_product_id",
        "product_images",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_product_images_product_id", table_name="product_images")
    op.drop_table("product_images")
