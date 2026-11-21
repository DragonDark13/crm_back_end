from datetime import date, datetime

from flask import Blueprint, jsonify

from models import (
    GiftSetSalesHistory,
    OtherInvestment,
    PackagingPurchaseHistory,
    PurchaseHistory,
    SaleHistory,
)

financial_journal_bp = Blueprint("financial_journal", __name__)


def _format_date(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value) if value is not None else None


@financial_journal_bp.route("/financial-journal", methods=["GET"])
def get_financial_journal():
    """Return a unified, read-only view of recorded financial operations."""
    from postgreSQLConnect import db_session

    try:
        operations = []

        for item in db_session.query(PurchaseHistory).all():
            operations.append({
                "id": f"product-purchase-{item.id}",
                "source_id": item.id,
                "date": _format_date(item.purchase_date),
                "direction": "expense",
                "type": "Закупівля товару",
                "description": item.product.name if item.product else "Товар",
                "counterparty": item.supplier.name if item.supplier else "",
                "amount": float(item.purchase_total_price or 0),
            })

        for item in db_session.query(PackagingPurchaseHistory).all():
            operations.append({
                "id": f"packaging-purchase-{item.id}",
                "source_id": item.id,
                "date": _format_date(item.purchase_date),
                "direction": "expense",
                "type": "Закупівля пакування",
                "description": item.material.name if item.material else "Пакування",
                "counterparty": (
                    item.packaging_material_supplier.name
                    if item.packaging_material_supplier else ""
                ),
                "amount": float(item.purchase_total_price or 0),
            })

        for item in db_session.query(OtherInvestment).all():
            operations.append({
                "id": f"other-expense-{item.id}",
                "source_id": item.id,
                "date": _format_date(item.date),
                "direction": "expense",
                "type": "Інші витрати",
                "description": item.type_name,
                "counterparty": item.supplier,
                "amount": float(item.cost or 0),
            })

        for item in db_session.query(SaleHistory).all():
            operations.append({
                "id": f"product-sale-{item.id}",
                "source_id": item.id,
                "date": _format_date(item.sale_date),
                "direction": "income",
                "type": "Продаж товару",
                "description": item.product.name if item.product else "Товар",
                "counterparty": item.customer.name if item.customer else "",
                "amount": float(item.selling_total_price or 0),
            })

        for item in db_session.query(GiftSetSalesHistory).all():
            operations.append({
                "id": f"gift-set-sale-{item.id}",
                "source_id": item.id,
                "date": _format_date(item.sold_at),
                "direction": "income",
                "type": "Продаж гіфтбоксу",
                "description": item.gift_set.name if item.gift_set else "Гіфтбокс",
                "counterparty": item.customer.name if item.customer else "",
                "amount": float(item.sold_price or 0),
            })

        operations.sort(
            key=lambda operation: operation["date"] or "",
            reverse=True,
        )
        return jsonify(operations), 200
    finally:
        db_session.close()
