"""Enforce unique normalized product names.

Revision ID: f2a6c8d1e430
Revises: d1e5f7a9c240
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a6c8d1e430"
down_revision: Union[str, Sequence[str], None] = "d1e5f7a9c240"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    duplicates = connection.execute(
        sa.text(
            """
            SELECT lower(trim(name)) AS normalized_name, COUNT(*) AS product_count
            FROM products
            GROUP BY lower(trim(name))
            HAVING COUNT(*) > 1
            LIMIT 10
            """
        )
    ).fetchall()

    if duplicates:
        duplicate_names = ", ".join(
            f"{row.normalized_name!r} ({row.product_count})" for row in duplicates
        )
        raise RuntimeError(
            "Cannot enforce unique product names because duplicate names already exist: "
            f"{duplicate_names}. Resolve them manually before retrying this migration."
        )

    op.create_index(
        "uq_products_name_normalized",
        "products",
        [sa.text("lower(trim(name))")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_products_name_normalized", table_name="products")
