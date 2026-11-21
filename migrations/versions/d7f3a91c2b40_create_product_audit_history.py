"""Create append-only product audit history.

Revision ID: d7f3a91c2b40
Revises: c4e82a1b7d90
"""

from alembic import op
import sqlalchemy as sa


revision = "d7f3a91c2b40"
down_revision = "c4e82a1b7d90"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "product_audit_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("changed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("changed_by_username", sa.String(length=255), nullable=False, server_default="Невідомий користувач"),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_product_audit_history_product_id",
        "product_audit_history",
        ["product_id"],
    )


def downgrade():
    op.drop_index("ix_product_audit_history_product_id", table_name="product_audit_history")
    op.drop_table("product_audit_history")
