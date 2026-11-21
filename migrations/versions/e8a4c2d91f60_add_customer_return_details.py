"""Add refund details to customer return history and protect sale references.

Revision ID: e8a4c2d91f60
Revises: d7f3a91c2b40
"""
from alembic import op
import sqlalchemy as sa


revision = "e8a4c2d91f60"
down_revision = "d7f3a91c2b40"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("return_history", sa.Column("return_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("return_history", sa.Column("returned_by_id", sa.Integer(), nullable=True))
    op.add_column("return_history", sa.Column("returned_by_username", sa.String(length=255), nullable=True))
    op.create_foreign_key(
        "fk_return_history_returned_by_user",
        "return_history",
        "users",
        ["returned_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for foreign_key in inspector.get_foreign_keys("return_history"):
        if foreign_key.get("constrained_columns") == ["sale_id"]:
            op.drop_constraint(foreign_key["name"], "return_history", type_="foreignkey")
    op.create_foreign_key(
        "fk_return_history_sale_restrict",
        "return_history",
        "sale_history",
        ["sale_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade():
    # Keep the sale reference restrictive: restoring CASCADE could erase return history.
    op.drop_constraint("fk_return_history_returned_by_user", "return_history", type_="foreignkey")
    op.drop_constraint("fk_return_history_sale_restrict", "return_history", type_="foreignkey")
    op.create_foreign_key(
        "fk_return_history_sale_restrict",
        "return_history",
        "sale_history",
        ["sale_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_column("return_history", "returned_by_username")
    op.drop_column("return_history", "returned_by_id")
    op.drop_column("return_history", "return_amount")
