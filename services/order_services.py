from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload

from models import Customer, Product, SaleHistory, StockHistory
from models.order import Order, OrderItem, OrderStatusHistory

orders_bp = Blueprint("orders", __name__)

STATUS_LABELS = {
    "new": "Нове",
    "confirmed": "Підтверджене",
    "awaiting_payment": "Очікує оплати",
    "paid": "Оплачене",
    "shipped": "Відправлене",
    "completed": "Виконане",
    "cancelled": "Скасоване",
}
TRANSITIONS = {
    "new": {"confirmed", "cancelled"},
    "confirmed": {"awaiting_payment", "cancelled"},
    "awaiting_payment": {"paid", "cancelled"},
    "paid": {"shipped"},
    "shipped": {"completed"},
    "completed": set(),
    "cancelled": set(),
}


def serialize_order(order):
    return {
        "id": order.id,
        "customer_id": order.customer_id,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "customer_email": order.customer_email,
        "delivery_address": order.delivery_address,
        "status": order.status,
        "status_label": STATUS_LABELS.get(order.status, order.status),
        "total_amount": float(order.total_amount),
        "notes": order.notes,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "items": [{
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product_name,
            "article": item.article,
            "quantity": item.quantity,
            "unit_price": float(item.unit_price),
            "line_total": float(item.line_total),
        } for item in order.items],
        "status_history": [{
            "id": entry.id,
            "from_status": entry.from_status,
            "to_status": entry.to_status,
            "changed_at": entry.changed_at.isoformat() if entry.changed_at else None,
            "changed_by_username": entry.changed_by_username,
            "note": entry.note,
        } for entry in order.status_history],
        "available_transitions": sorted(TRANSITIONS.get(order.status, set())),
    }


def _load_order(session, order_id, lock=False):
    query = session.query(Order).options(
        selectinload(Order.items),
        selectinload(Order.status_history),
    ).filter(Order.id == order_id)
    if lock:
        query = query.with_for_update()
    return query.one_or_none()


def _record_status(session, order, new_status, username, note=None):
    old_status = order.status
    order.status = new_status
    order.updated_at = datetime.utcnow()
    if new_status == "confirmed":
        order.confirmed_at = datetime.utcnow()
    elif new_status == "paid":
        order.paid_at = datetime.utcnow()
    elif new_status == "shipped":
        order.shipped_at = datetime.utcnow()
    elif new_status == "completed":
        order.completed_at = datetime.utcnow()
    elif new_status == "cancelled":
        order.cancelled_at = datetime.utcnow()
    order.status_history.append(OrderStatusHistory(
        from_status=old_status,
        to_status=new_status,
        changed_by_username=username,
        note=note,
    ))


@orders_bp.route("/store/orders", methods=["POST"])
def create_store_order():
    from postgreSQLConnect import db_session

    data = request.get_json(silent=True) or {}
    customer_name = str(data.get("customer_name") or "").strip()
    items_data = data.get("items")
    if not customer_name or not isinstance(items_data, list) or not items_data:
        return jsonify(error="Потрібні ім'я покупця та щонайменше один товар"), 400

    try:
        quantities = {}
        for raw in items_data:
            product_id = int(raw.get("product_id"))
            quantity = int(raw.get("quantity"))
            if quantity <= 0:
                raise ValueError
            quantities[product_id] = quantities.get(product_id, 0) + quantity
    except (TypeError, ValueError, AttributeError):
        return jsonify(error="Некоректний список товарів або кількість"), 400

    try:
        customer = db_session.query(Customer).filter_by(name=customer_name).one_or_none()
        if customer is None:
            customer = Customer(
                name=customer_name,
                phone_number=(str(data.get("customer_phone") or "").strip() or None),
                email=(str(data.get("customer_email") or "").strip() or None),
                address=(str(data.get("delivery_address") or "").strip() or None),
            )
            db_session.add(customer)
            db_session.flush()

        products = db_session.query(Product).filter(
            Product.id.in_(sorted(quantities))
        ).order_by(Product.id).with_for_update().all()
        if len(products) != len(quantities):
            db_session.rollback()
            return jsonify(error="Один або кілька товарів не знайдені"), 404

        order_items = []
        total = Decimal("0.00")
        for product in products:
            quantity = quantities[product.id]
            available = int(product.available_quantity or 0)
            if quantity > available:
                db_session.rollback()
                return jsonify(error=f"Недостатньо товару «{product.name}» у наявності"), 409
            price = Decimal(str(product.selling_price_per_item or 0))
            line_total = price * quantity
            total += line_total
            order_items.append(OrderItem(
                product_id=product.id,
                product_name=product.name,
                article=product.article,
                quantity=quantity,
                unit_price=price,
                line_total=line_total,
            ))

        order = Order(
            customer_id=customer.id,
            customer_name=customer_name,
            customer_phone=(str(data.get("customer_phone") or "").strip() or None),
            customer_email=(str(data.get("customer_email") or "").strip() or None),
            delivery_address=(str(data.get("delivery_address") or "").strip() or None),
            notes=(str(data.get("notes") or "").strip() or None),
            status="new",
            total_amount=total,
        )
        order.items.extend(order_items)
        db_session.add(order)
        db_session.flush()
        db_session.add(OrderStatusHistory(order_id=order.id, from_status=None, to_status="new", note="Замовлення створено з інтернет-магазину"))
        db_session.commit()
        return jsonify(message="Замовлення створено", order=serialize_order(order)), 201
    except (InvalidOperation, SQLAlchemyError):
        db_session.rollback()
        return jsonify(error="Не вдалося створити замовлення"), 500


@orders_bp.route("/orders", methods=["GET"])
def get_orders():
    from postgreSQLConnect import db_session

    orders = db_session.query(Order).options(
        selectinload(Order.items),
        selectinload(Order.status_history),
    ).order_by(Order.created_at.desc(), Order.id.desc()).all()
    return jsonify([serialize_order(order) for order in orders]), 200


@orders_bp.route("/orders/<int:order_id>/status", methods=["PATCH"])
def update_order_status(order_id):
    from postgreSQLConnect import db_session

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    note = data.get("note")
    if new_status not in STATUS_LABELS:
        return jsonify(error="Невідомий статус замовлення"), 400

    try:
        order = _load_order(db_session, order_id, lock=True)
        if order is None:
            db_session.rollback()
            return jsonify(error="Замовлення не знайдено"), 404
        if new_status not in TRANSITIONS.get(order.status, set()):
            db_session.rollback()
            return jsonify(error="Недозволений перехід статусу"), 409

        username = str(get_jwt_identity() or "manager")
        if new_status == "confirmed":
            products = db_session.query(Product).filter(
                Product.id.in_(sorted({item.product_id for item in order.items}))
            ).order_by(Product.id).with_for_update().all()
            products_by_id = {product.id: product for product in products}
            for item in order.items:
                product = products_by_id[item.product_id]
                available = int(product.available_quantity or 0)
                if available < item.quantity:
                    db_session.rollback()
                    return jsonify(error=f"Недостатньо товару «{item.product_name}» для резервування"), 409
            for item in order.items:
                product = products_by_id[item.product_id]
                before = int(product.available_quantity or 0)
                product.available_quantity = before - item.quantity
                product.reserved_quantity = int(product.reserved_quantity or 0) + item.quantity
                db_session.add(StockHistory(
                    product_id=product.id,
                    change_amount=-item.quantity,
                    change_type="order_reservation",
                    quantity_before=before,
                    quantity_after=product.available_quantity,
                    reason=f"Резерв замовлення №{order.id}",
                ))

        elif new_status == "cancelled" and order.status in {"confirmed", "awaiting_payment"}:
            products = db_session.query(Product).filter(
                Product.id.in_(sorted({item.product_id for item in order.items}))
            ).order_by(Product.id).with_for_update().all()
            products_by_id = {product.id: product for product in products}
            for item in order.items:
                product = products_by_id[item.product_id]
                before = int(product.available_quantity or 0)
                product.available_quantity = before + item.quantity
                product.reserved_quantity = max(0, int(product.reserved_quantity or 0) - item.quantity)
                db_session.add(StockHistory(
                    product_id=product.id,
                    change_amount=item.quantity,
                    change_type="order_reservation_release",
                    quantity_before=before,
                    quantity_after=product.available_quantity,
                    reason=f"Зняття резерву замовлення №{order.id}",
                ))

        elif new_status == "completed":
            customer = db_session.query(Customer).filter_by(id=order.customer_id).one_or_none()
            if customer is None:
                customer = Customer(
                    name=order.customer_name,
                    phone_number=order.customer_phone,
                    email=order.customer_email,
                    address=order.delivery_address,
                )
                db_session.add(customer)
                db_session.flush()
                order.customer_id = customer.id
            products = db_session.query(Product).filter(
                Product.id.in_(sorted({item.product_id for item in order.items}))
            ).order_by(Product.id).with_for_update().all()
            products_by_id = {product.id: product for product in products}
            for item in order.items:
                product = products_by_id[item.product_id]
                reserved = int(product.reserved_quantity or 0)
                if reserved < item.quantity:
                    db_session.rollback()
                    return jsonify(error="Резерв товару не відповідає замовленню; завершення скасовано"), 409
                product.reserved_quantity = reserved - item.quantity
                product.sold_quantity = int(product.sold_quantity or 0) + item.quantity
                product.selling_quantity = int(product.selling_quantity or 0) + item.quantity
                product.selling_total_price = Decimal(str(product.selling_total_price or 0)) + item.line_total
                profit = (item.unit_price - Decimal(str(product.purchase_price_per_item or 0))) * item.quantity
                db_session.add(SaleHistory(
                    product_id=product.id,
                    customer_id=customer.id,
                    quantity_sold=item.quantity,
                    selling_price_per_item=item.unit_price,
                    selling_total_price=item.line_total,
                    sale_date=datetime.utcnow(),
                    profit=profit,
                ))

        _record_status(db_session, order, new_status, username, note)
        db_session.commit()
        return jsonify(message="Статус замовлення оновлено", order=serialize_order(order)), 200
    except SQLAlchemyError:
        db_session.rollback()
        return jsonify(error="Не вдалося оновити статус замовлення"), 500
