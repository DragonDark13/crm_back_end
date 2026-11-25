"""Track imported purchase rows to prevent duplicate history imports.

Revision ID: a4b7c9d2e610
Revises: f2a6c8d1e430
"""

from collections import defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json

from alembic import op
import sqlalchemy as sa


revision = "a4b7c9d2e610"
down_revision = "f2a6c8d1e430"
branch_labels = None
depends_on = None


def _decimal_text(value, scale):
    decimal_value = Decimal(str(value or 0))
    quantum = Decimal("1").scaleb(-scale)
    return format(decimal_value.quantize(quantum, rounding=ROUND_HALF_UP), "f")


def _fingerprint(name, supplier_name, purchase_date, quantity, total_price, price_per_item):
    payload = [
        (name or "").strip().casefold(),
        (supplier_name or "").strip().casefold(),
        purchase_date.isoformat(),
        _decimal_text(quantity, 0),
        _decimal_text(total_price, 2),
        _decimal_text(price_per_item, 3),
    ]
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def upgrade():
    op.create_table(
        "product_import_rows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "purchase_history_id",
            sa.Integer(),
            sa.ForeignKey("purchase_history.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("occurrence_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "fingerprint",
            "occurrence_index",
            name="uq_product_import_rows_fingerprint_occurrence",
        ),
    )
    op.create_index(
        "ix_product_import_rows_fingerprint",
        "product_import_rows",
        ["fingerprint"],
    )

    connection = op.get_bind()
    purchases = connection.execute(
        sa.text(
            """
            SELECT ph.id, p.name AS product_name, s.name AS supplier_name,
                   ph.purchase_date, ph.quantity_purchase,
                   ph.purchase_total_price, ph.purchase_price_per_item
            FROM purchase_history ph
            JOIN products p ON p.id = ph.product_id
            LEFT JOIN suppliers s ON s.id = ph.supplier_id
            ORDER BY ph.id
            """
        )
    ).mappings()

    occurrences = defaultdict(int)
    rows = []
    for purchase in purchases:
        fingerprint = _fingerprint(
            purchase["product_name"],
            purchase["supplier_name"],
            purchase["purchase_date"],
            purchase["quantity_purchase"],
            purchase["purchase_total_price"],
            purchase["purchase_price_per_item"],
        )
        occurrences[fingerprint] += 1
        rows.append({
            "purchase_history_id": purchase["id"],
            "fingerprint": fingerprint,
            "occurrence_index": occurrences[fingerprint],
            "created_at": datetime.utcnow(),
        })

    if rows:
        op.bulk_insert(
            sa.table(
                "product_import_rows",
                sa.column("purchase_history_id", sa.Integer),
                sa.column("fingerprint", sa.String(64)),
                sa.column("occurrence_index", sa.Integer),
                sa.column("created_at", sa.DateTime),
            ),
            rows,
        )


def downgrade():
    op.drop_index("ix_product_import_rows_fingerprint", table_name="product_import_rows")
    op.drop_table("product_import_rows")
