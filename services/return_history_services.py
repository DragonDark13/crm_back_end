from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from sqlalchemy.exc import SQLAlchemyError

from models import Product, SaleHistory, ReturnHistory, StockHistory, User
from services.product_service import record_product_audit


return_history_bp = Blueprint("return_history", __name__)


def _refund_amount(sale, quantity, previous_returns):
    returned_quantity = sum(item.quantity_returned for item in previous_returns)
    refunded_amount = Decimal("0.00")
    for item in previous_returns:
        if item.return_amount is not None:
            refunded_amount += Decimal(item.return_amount)
        else:
            refunded_amount += Decimal(sale.selling_price_per_item or 0) * item.quantity_returned

    remaining_quantity = sale.quantity_sold - returned_quantity
    remaining_amount = Decimal(sale.selling_total_price or 0) - refunded_amount
    if quantity == remaining_quantity:
        return remaining_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return (remaining_amount * Decimal(quantity) / Decimal(remaining_quantity)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


@return_history_bp.route("/sales/<int:sale_id>/returns", methods=["POST"])
@jwt_required()
def create_customer_return(sale_id):
    from postgreSQLConnect import db_session

    roles = get_jwt().get("roles", [])
    if "manager" not in roles:
        return jsonify({"error": "Manager access required"}), 403

    data = request.get_json(silent=True) or {}
    raw_quantity = data.get("quantity")
    if isinstance(raw_quantity, bool):
        return jsonify({"error": "Quantity must be a positive integer"}), 400
    try:
        quantity = int(raw_quantity)
    except (TypeError, ValueError):
        return jsonify({"error": "Quantity must be a positive integer"}), 400
    if quantity <= 0 or str(raw_quantity).strip() not in (str(quantity), f"{quantity}.0"):
        return jsonify({"error": "Quantity must be a positive integer"}), 400

    reason = data.get("reason")
    if reason is not None and not isinstance(reason, str):
        return jsonify({"error": "Reason must be a string"}), 400
    reason = reason.strip() or None if reason is not None else None

    try:
        sale = db_session.query(SaleHistory).filter(
            SaleHistory.id == sale_id
        ).with_for_update().one_or_none()
        if sale is None:
            db_session.rollback()
            return jsonify({"error": "Sale not found"}), 404

        product = db_session.query(Product).filter(
            Product.id == sale.product_id
        ).with_for_update().populate_existing().one_or_none()
        if product is None:
            db_session.rollback()
            return jsonify({"error": "Product not found"}), 404

        previous_returns = db_session.query(ReturnHistory).filter(
            ReturnHistory.sale_id == sale.id
        ).with_for_update().all()
        already_returned = sum(item.quantity_returned for item in previous_returns)
        remaining_quantity = sale.quantity_sold - already_returned
        if quantity > remaining_quantity:
            db_session.rollback()
            return jsonify({
                "error": f"Return quantity exceeds the remaining quantity ({remaining_quantity})"
            }), 409

        refund_amount = _refund_amount(sale, quantity, previous_returns)
        if refund_amount < 0:
            db_session.rollback()
            return jsonify({"error": "Refund amount cannot be negative"}), 409

        actor_id = get_jwt_identity()
        actor = db_session.query(User).filter(User.id == int(actor_id)).one_or_none()
        actor_name = actor.username if actor else "Невідомий користувач"

        quantity_before = product.available_quantity or 0
        previous_sold_quantity = product.sold_quantity or 0
        previous_selling_quantity = product.selling_quantity or 0
        previous_selling_total = Decimal(product.selling_total_price or 0)

        product.available_quantity = quantity_before + quantity
        product.sold_quantity = max(0, previous_sold_quantity - quantity)
        product.selling_quantity = max(0, previous_selling_quantity - quantity)
        product.selling_total_price = max(Decimal("0.00"), previous_selling_total - refund_amount)

        record_product_audit(
            db_session,
            product,
            "return",
            {
                "available_quantity": (quantity_before, product.available_quantity),
                "sold_quantity": (previous_sold_quantity, product.sold_quantity),
                "selling_total_price": (previous_selling_total, product.selling_total_price),
            },
            reason=reason,
        )

        return_record = ReturnHistory(
            product_id=product.id,
            customer_id=sale.customer_id,
            sale_id=sale.id,
            quantity_returned=quantity,
            return_reason=reason,
            return_date=datetime.now(),
            return_amount=refund_amount,
            returned_by_id=actor.id if actor else None,
            returned_by_username=actor_name,
        )
        db_session.add(return_record)
        db_session.add(StockHistory(
            product_id=product.id,
            change_amount=quantity,
            change_type="return",
            timestamp=datetime.now(),
            quantity_before=quantity_before,
            quantity_after=product.available_quantity,
            reason=reason,
        ))
        db_session.commit()

        return jsonify({
            "message": "Customer return recorded successfully",
            "return": {
                "id": return_record.id,
                "sale_id": sale.id,
                "product_id": product.id,
                "product_name": product.name,
                "customer_id": sale.customer_id,
                "customer_name": sale.customer.name if sale.customer else "",
                "quantity_returned": quantity,
                "return_amount": float(refund_amount),
                "return_reason": reason,
                "return_date": return_record.return_date.isoformat(),
                "returned_by_username": actor_name,
            },
            "available_quantity": product.available_quantity,
            "remaining_return_quantity": remaining_quantity - quantity,
        }), 201
    except SQLAlchemyError:
        db_session.rollback()
        return jsonify({"error": "Database error while recording return"}), 500
    except Exception:
        db_session.rollback()
        return jsonify({"error": "Unexpected error while recording return"}), 500


@return_history_bp.route("/returns", methods=["GET"])
@jwt_required()
def get_customer_returns():
    from postgreSQLConnect import db_session

    roles = get_jwt().get("roles", [])
    if "manager" not in roles:
        return jsonify({"error": "Manager access required"}), 403

    try:
        records = db_session.query(ReturnHistory).order_by(
            ReturnHistory.return_date.desc(), ReturnHistory.id.desc()
        ).all()
        result = []
        for item in records:
            sale = item.sale
            amount = item.return_amount
            if amount is None:
                amount = (
                    Decimal(sale.selling_price_per_item or 0) * item.quantity_returned
                    if sale else Decimal("0.00")
                )
            result.append({
                "id": item.id,
                "sale_id": item.sale_id,
                "product_id": item.product_id,
                "product_name": item.product.name if item.product else "Товар",
                "customer_id": item.customer_id,
                "customer_name": item.customer.name if item.customer else "Клієнт",
                "quantity_returned": item.quantity_returned,
                "return_amount": float(amount),
                "return_reason": item.return_reason,
                "return_date": item.return_date.isoformat() if item.return_date else None,
                "returned_by_username": item.returned_by_username,
            })
        return jsonify(result), 200
    except SQLAlchemyError:
        return jsonify({"error": "Database error while loading returns"}), 500
    finally:
        db_session.close()
