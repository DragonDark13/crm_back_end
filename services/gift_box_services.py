from flask import request, jsonify, Blueprint
from database import db_session
from models import GiftSet, GiftSetProduct, GiftSetPackaging, Product, PackagingMaterial, GiftSetSalesHistory

gift_box_services_bp = Blueprint('gift_box_services', __name__)


@gift_box_services_bp.route('/api/create_gift_set', methods=['POST'])
def create_gift_set():
    data = request.json

    # Валідація вхідних даних
    if 'name' not in data or 'items' not in data:
        return jsonify({"error": "Invalid data"}), 400

    name = data['name']
    items = data['items']  # список об'єктів {item_id, item_type, quantity}

    gift_set = GiftSet(name=name)
    db_session.add(gift_set)
    db_session.commit()  # Отримуємо gift_set.id

    total_price = 0

    for item in items:
        item_id = item.get('item_id')
        item_type = item.get('item_type')  # "product" або "packaging"
        quantity = item.get('quantity', 1)

        if item_type == "product":
            product = Product.query.get(item_id)
            if not product or product.quantity - product.reserved_quantity < quantity:
                return jsonify({"error": f"Product {item_id} not available"}), 400
            product.available_quantity -= quantity
            product.reserved_quantity += quantity  # Резервуємо товар
            total_price += product.price * quantity
            gift_set_product = GiftSetProduct(
                gift_set_id=gift_set.id,
                product_id=product.id,
                quantity=quantity
            )
            db_session.add(gift_set_product)

        elif item_type == "packaging":
            packaging = PackagingMaterial.query.get(item_id)
            if not packaging or packaging.quantity - packaging.reserved_quantity < quantity:
                return jsonify({"error": f"Packaging {item_id} not available"}), 400
            packaging.available_quantity -= quantity  # Оновлюємо кількість доступного пакування та відзначаємо як використане
            packaging.reserved_quantity += quantity  # Резервуємо пакування
            total_price += packaging.price * quantity
            gift_set_packaging = GiftSetPackaging(
                gift_set_id=gift_set.id,
                packaging_id=packaging.id,
                quantity=quantity
            )
            db_session.add(gift_set_packaging)

    gift_set.total_price = total_price
    db_session.commit()

    return jsonify({"message": "Gift set created successfully", "id": gift_set.id}), 201


@gift_box_services_bp.route('/api/gift_set_details/<int:gift_set_id>', methods=['GET'])
def get_gift_set(gift_set_id):
    gift_set = GiftSet.query.get(gift_set_id)
    if not gift_set:
        return jsonify({"error": "Gift set not found"}), 404

    products = [
        {
            "id": item.product_id,
            "name": item.product.name,
            "price": item.product.price,
            "quantity": item.quantity
        }
        for item in gift_set.products
    ]

    packagings = [
        {
            "id": item.packaging_id,
            "type": item.packaging.type,
            "price": item.packaging.price,
            "quantity": item.quantity
        }
        for item in gift_set.packagings
    ]

    return jsonify({
        "id": gift_set.id,
        "name": gift_set.name,
        "total_price": gift_set.total_price,
        "products": products,
        "packagings": packagings
    })


@gift_box_services_bp.route('/api/dismantle_gift_set/<int:gift_set_id>', methods=['DELETE'])
def dismantle_gift_set(gift_set_id):
    gift_set = GiftSet.query.get(gift_set_id)
    if not gift_set:
        return jsonify({"error": "Gift set not found"}), 404

    # Повертаємо кількість товарів та пакувань на склад
    gift_set_products = GiftSetProduct.query.filter_by(gift_set_id=gift_set.id).all()
    for item in gift_set_products:
        product = Product.query.get(item.product_id)
        product.quantity += item.quantity

    gift_set_packagings = GiftSetPackaging.query.filter_by(gift_set_id=gift_set.id).all()
    for item in gift_set_packagings:
        packaging = PackagingMaterial.query.get(item.packaging_id)
        packaging.quantity += item.quantity

    # Видаляємо набір і його вміст
    db_session.delete(gift_set)
    db_session.commit()

    return jsonify({"message": "Gift set dismantled successfully"}), 200


@gift_box_services_bp.route('/api/sell_gift_set/<int:gift_set_id>', methods=['POST'])
def sell_gift_set(gift_set_id):
    gift_set = GiftSet.query.get(gift_set_id)
    if not gift_set:
        return jsonify({"error": "Gift set not found"}), 404

    data = request.json
    customer_name = data.get('customer_name', None)  # Необов'язкове поле для покупця

    # Створення запису в історії продажів
    sales_record = GiftSetSalesHistory(
        gift_set_id=gift_set.id,
        sold_price=gift_set.total_price,
        quantity=1,  # Ми продаємо один набір (можна додати можливість продавати більше)
        customer_name=customer_name
    )
    db_session.add(sales_record)
    db_session.commit()

    # Зміна кількості зарезервованих і проданих товарів та пакувань
    for gift_set_product in gift_set.products:
        product = gift_set_product.product
        product.reserved_quantity -= gift_set_product.quantity  # Зменшуємо кількість зарезервовану
        product.sold_quantity += gift_set_product.quantity  # Збільшуємо кількість продану
        product.available_quantity -= gift_set_product.quantity  # Зменшуємо кількість в наявності

        # Додаємо запис про цей товар у історію продажів
        sales_record.products.append(gift_set_product)

    for gift_set_packaging in gift_set.packagings:
        packaging = gift_set_packaging.packaging
        packaging.reserved_quantity -= gift_set_packaging.quantity  # Зменшуємо кількість зарезервовану
        packaging.sold_quantity += gift_set_packaging.quantity  # Збільшуємо кількість продану
        packaging.available_quantity -= gift_set_packaging.quantity  # Зменшуємо кількість в наявності

        # Додаємо запис про це пакування у історію продажів
        sales_record.packagings.append(gift_set_packaging)

    # Записуємо зміни в базу даних
    db_session.commit()

    return jsonify({
        "message": "Gift set sold successfully",
        "sales_record": sales_record.to_dict()
    }), 200
