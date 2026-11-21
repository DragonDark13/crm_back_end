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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "return_history" not in tables:
        op.create_table(
            "return_history",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="RESTRICT")),
            sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT")),
            sa.Column("quantity_returned", sa.Integer(), nullable=False),
            sa.Column("return_reason", sa.String(), nullable=True),
            sa.Column("return_date", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("sale_id", sa.Integer(), sa.ForeignKey("sale_history.id", ondelete="RESTRICT")),
            sa.Column("return_amount", sa.Numeric(12, 2), nullable=True),
            sa.Column("returned_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("returned_by_username", sa.String(length=255), nullable=True),
        )
        return

    existing_columns = {column["name"] for column in inspector.get_columns("return_history")}
    if "return_amount" not in existing_columns:
        op.add_column("return_history", sa.Column("return_amount", sa.Numeric(12, 2), nullable=True))
    if "returned_by_id" not in existing_columns:
        op.add_column("return_history", sa.Column("returned_by_id", sa.Integer(), nullable=True))
    if "returned_by_username" not in existing_columns:
        op.add_column("return_history", sa.Column("returned_by_username", sa.String(length=255), nullable=True))

    foreign_keys = inspector.get_foreign_keys("return_history")
    if not any(fk.get("constrained_columns") == ["returned_by_id"] for fk in foreign_keys):
        op.create_foreign_key(
            "fk_return_history_returned_by_user",
            "return_history",
            "users",
            ["returned_by_id"],
            ["id"],
            ondelete="SET NULL",
        )

    for foreign_key in foreign_keys:
        if foreign_key.get("constrained_columns") == ["sale_id"] and foreign_key.get("name"):
            op.drop_constraint(foreign_key["name"], "return_history", type_="foreignkey")
    if not any(fk.get("constrained_columns") == ["sale_id"] for fk in foreign_keys):
        op.create_foreign_key(
            "fk_return_history_sale_restrict",
            "return_history",
            "sale_history",
            ["sale_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    else:
        op.create_foreign_key(
            "fk_return_history_sale_restrict",
            "return_history",
            "sale_history",
            ["sale_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "return_history" not in inspector.get_table_names():
        return

    for foreign_key in inspector.get_foreign_keys("return_history"):
        if foreign_key.get("constrained_columns") == ["returned_by_id"] and foreign_key.get("name"):
            op.drop_constraint(foreign_key["name"], "return_history", type_="foreignkey")
        if foreign_key.get("constrained_columns") == ["sale_id"] and foreign_key.get("name"):
            op.drop_constraint(foreign_key["name"], "return_history", type_="foreignkey")

    op.create_foreign_key(
        "fk_return_history_sale_restrict",
        "return_history",
        "sale_history",
        ["sale_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    columns = {column["name"] for column in sa.inspect(bind).get_columns("return_history")}
    for column_name in ("returned_by_username", "returned_by_id", "return_amount"):
        if column_name in columns:
            op.drop_column("return_history", column_name)
