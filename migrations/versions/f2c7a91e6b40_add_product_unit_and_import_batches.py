"""Add product unit of measure, import batch tracking and precise purchase prices.

Revision ID: f2c7a91e6b40
Revises: e8a4c2d91f60
"""

from alembic import op
import sqlalchemy as sa


revision = "f2c7a91e6b40"
down_revision = "e8a4c2d91f60"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "products",
        sa.Column("unit_of_measure", sa.String(length=50), nullable=True),
    )
    op.alter_column(
        "products",
        "purchase_price_per_item",
        existing_type=sa.Numeric(10, 2),
        type_=sa.Numeric(12, 3),
        existing_nullable=True,
    )
    op.alter_column(
        "purchase_history",
        "purchase_price_per_item",
        existing_type=sa.Numeric(10, 2),
        type_=sa.Numeric(12, 3),
        existing_nullable=True,
    )
    op.create_table(
        "product_import_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("file_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("rows_imported", sa.Integer(), nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("product_import_batches")
    op.alter_column(
        "purchase_history",
        "purchase_price_per_item",
        existing_type=sa.Numeric(12, 3),
        type_=sa.Numeric(10, 2),
        existing_nullable=True,
    )
    op.alter_column(
        "products",
        "purchase_price_per_item",
        existing_type=sa.Numeric(12, 3),
        type_=sa.Numeric(10, 2),
        existing_nullable=True,
    )
    op.drop_column("products", "unit_of_measure")
