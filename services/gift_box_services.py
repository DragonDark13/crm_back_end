from datetime import datetime
from decimal import Decimal

from flask import request, jsonify, Blueprint
from models import GiftSet, GiftSetProduct, GiftSetPackaging, Product, PackagingMaterial, GiftSetSalesHistory, \
    GiftSetSalesHistoryProduct, GiftSetSalesHistoryPackaging, Customer, StockHistory, PackagingStockHistory

gift_box_services_bp = Blueprint('gift_box_services', __name__)


@gift_box_services_bp.route('/create_gift_set', methods=['POST'])
def create_gift_set():
    data = request.json
    from postgreSQLConnect import db_session

    # Валідація вхідних даних
    if 'name' not in data or 'items' not in data:
        return jsonify({"error": "Invalid data"}), 400

    name = data['name']
    description = data['description']
    items = data['items']  # список об'єктів {item_id, item_type, quantity}
    gift_selling_price = data.get('gift_selling_price', 0)  # Optional gift selling price

    # Перевірка на унікальність назви набору
    existing_gift_set = db_session.query(GiftSet).filter(GiftSet.name == name).first()
    if existing_gift_set:
        return jsonify({"error": f"Gift set with name '{name}' already exists"}), 400

    # Перевірка на наявність хоча б одного продукту або пакування
    if not any(item['item_type'] in ['product', 'packaging'] for item in items):
        return jsonify({"error": "At least one product or packaging must be included in the gift set"}), 400

    gift_set = GiftSet(
        name=name,
        description=description,
        gift_selling_price=gift_selling_price
    )
    db_session.add(gift_set)
    db_session.flush()  # Отримуємо gift_set.id без часткового commit

    total_price = 0

    for item in items:
        item_id = item.get('item_id')
        item_type = item.get('item_type')  # "product" або "packaging"
        quantity = item.get('quantity', 1)

        if item_type == "product":
            product = db_session.query(Product).filter(
                Product.id == item_id
            ).with_for_update().populate_existing().one_or_none()
            if not product:
                db_session.rollback()
                return jsonify({"error": f"Product {item_id} not found"}), 400
            if product.available_quantity < quantity:
                db_session.rollback()
                return jsonify({"error": f"Product {item_id} not available in required quantity"}), 400
            quantity_before = product.available_quantity
            product.available_quantity -= quantity
            product.reserved_quantity += quantity  # Резервуємо товар
            db_session.add(StockHistory(product_id=product.id, change_amount=-quantity, change_type='gift_set_reserve', timestamp=datetime.now(), quantity_before=quantity_before, quantity_after=product.available_quantity, reason='Gift set reservation'))
            total_price += product.purchase_price_per_item * quantity
            gift_set_product = GiftSetProduct(
                gift_set_id=gift_set.id,
                product_id=product.id,
                quantity=quantity
            )
            db_session.add(gift_set_product)

        elif item_type == "packaging":
            packaging = db_session.query(PackagingMaterial).filter(PackagingMaterial.id == item_id).with_for_update().one_or_none()
            if not packaging:
                db_session.rollback()
                return jsonify({"error": f"Packaging {item_id} not found"}), 400
            if packaging.available_quantity < quantity:
                db_session.rollback()
                return jsonify({"error": f"Packaging {item_id} not available in required quantity"}), 400
            packaging_quantity_before = packaging.available_quantity
            packaging.available_quantity -= quantity
            db_session.add(PackagingStockHistory(material_id=packaging.id, change_amount=-quantity, change_type='gift_set_reserve', timestamp=datetime.now()))  # Оновлюємо кількість доступного пакування та відзначаємо як використане
            packaging.reserved_quantity += quantity  # Резервуємо пакування
            total_price += packaging.purchase_price_per_unit * quantity
            gift_set_packaging = GiftSetPackaging(
                gift_set_id=gift_set.id,
                packaging_id=packaging.id,
                quantity=quantity
            )
            db_session.add(gift_set_packaging)

    gift_set.total_price = total_price
    db_session.commit()

    return jsonify({"message": "Gift set created successfully", "id": gift_set.id}), 201


@gift_box_services_bp.route('/gift_set_show_details/<int:gift_set_id>', methods=['GET'])
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


@gift_box_services_bp.route('/update_gift_set/<int:gift_set_id>', methods=['PUT'])
def update_gift_set(gift_set_id):
    try:
        data = request.json
        from postgreSQLConnect import db_session

        # Отримуємо набір з бази даних
        gift_set = db_session.query(GiftSet).filter(
            GiftSet.id == gift_set_id
        ).with_for_update().populate_existing().one_or_none()
        if not gift_set:
            return jsonify({"error": "Gift set not found"}), 404
        if gift_set.is_sold or db_session.query(GiftSetSalesHistory.id).filter_by(gift_set_id=gift_set.id).first():
            return jsonify({"error": "Sold gift sets cannot be edited because they have sales history."}), 409

        # Оновлення назви, опису та ціни
        name = data.get('name')
        description = data.get('description')
        gift_selling_price = data.get('gift_selling_price')

        if name:
            # Перевірка унікальності нової назви
            existing_gift_set = db_session.query(GiftSet).filter(GiftSet.name == name,
                                                                 GiftSet.id != gift_set_id).first()
            if existing_gift_set:
                return jsonify({"error": f"Gift set with name '{name}' already exists"}), 400
            gift_set.name = name

        if description is not None:
            gift_set.description = description

        if gift_selling_price is not None:
            gift_set.gift_selling_price = gift_selling_price

        # Оновлюємо склад набору: продукти та пакування
        new_items = data.get('items', [])  # Список нових елементів: {item_id, quantity, price}

        total_price = 0
        # Очищуємо попередні записи, але перед цим повертаємо зарезервовані кількості
        for item in gift_set.gift_set_products:
            existing_product = db_session.query(Product).filter(Product.id == item.product_id).with_for_update().one_or_none()
            if existing_product:
                quantity_before = existing_product.available_quantity
                existing_product.available_quantity += item.quantity
                existing_product.reserved_quantity -= item.quantity
                db_session.add(StockHistory(product_id=existing_product.id, change_amount=item.quantity, change_type='gift_set_unreserve', timestamp=datetime.now(), quantity_before=quantity_before, quantity_after=existing_product.available_quantity, reason='Gift set composition updated'))
            db_session.delete(item)

        for item in gift_set.gift_set_packagings:
            existing_packaging = db_session.query(PackagingMaterial).filter(
                PackagingMaterial.id == item.packaging_id).with_for_update().one_or_none()
            if existing_packaging:
                existing_packaging.available_quantity += item.quantity
                existing_packaging.reserved_quantity -= item.quantity
                db_session.add(PackagingStockHistory(material_id=existing_packaging.id, change_amount=item.quantity, change_type='gift_set_unreserve', timestamp=datetime.now()))
            db_session.delete(item)


        # Додаємо нові елементи до набору
        for item in new_items:
            item_id = item.get('product_id') or item.get('packaging_id')
            quantity = item.get('quantity', 1)
            price = float(item.get('price', 0))
            item_type = item.get('type', 'product')

            # Додаємо продукти
            if item_type == "product" and item_id:
                product = db_session.query(Product).filter(Product.id == item_id).with_for_update().one_or_none()
                if not product:
                    db_session.rollback()
                    return jsonify({"error": f"Product {item_id} not found"}), 400
                if product.available_quantity < quantity:
                    db_session.rollback()
                    return jsonify({"error": f"Product {item_id} not available in required quantity"}), 400
                quantity_before = product.available_quantity
                product.available_quantity -= quantity
                product.reserved_quantity += quantity
                db_session.add(StockHistory(product_id=product.id, change_amount=-quantity, change_type='gift_set_reserve', timestamp=datetime.now(), quantity_before=quantity_before, quantity_after=product.available_quantity, reason='Gift set reservation updated'))
                total_price += price * quantity

                gift_set_product = GiftSetProduct(
                    gift_set_id=gift_set.id,
                    product_id=product.id,
                    quantity=quantity
                )
                db_session.add(gift_set_product)

            # Додаємо пакування
            elif item_type == "packaging" and item_id:
                packaging = db_session.query(PackagingMaterial).filter(PackagingMaterial.id == item_id).with_for_update().one_or_none()
                if not packaging:
                    db_session.rollback()
                    return jsonify({"error": f"Packaging {item_id} not found"}), 400
                if packaging.available_quantity < quantity:
                    db_session.rollback()
                    return jsonify({"error": f"Packaging {item_id} not available in required quantity"}), 400
                packaging.available_quantity -= quantity
                db_session.add(PackagingStockHistory(material_id=packaging.id, change_amount=-quantity, change_type='gift_set_reserve', timestamp=datetime.now()))
                packaging.reserved_quantity += quantity
                total_price += float(packaging.purchase_price_per_unit) * quantity

                gift_set_packaging = GiftSetPackaging(
                    gift_set_id=gift_set.id,
                    packaging_id=packaging.id,
                    quantity=quantity
                )
                db_session.add(gift_set_packaging)

        # Оновлюємо загальну ціну набору
        gift_set.total_price = total_price
        db_session.commit()

        return jsonify({"message": "Gift set updated successfully", "id": gift_set.id}), 200

    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500


@gift_box_services_bp.route('/remove_gift_set/<int:gift_set_id>', methods=['DELETE'])
def dismantle_gift_set(gift_set_id):
    from postgreSQLConnect import db_session

    try:
        # Знаходимо подарунковий набір
        gift_set = db_session.query(GiftSet).filter(
            GiftSet.id == gift_set_id
        ).with_for_update().populate_existing().one_or_none()
        if not gift_set:
            return jsonify({"error": "Gift set not found"}), 404
        if db_session.query(GiftSetSalesHistory.id).filter_by(gift_set_id=gift_set.id).first():
            return jsonify({"error": "Gift set has sales history and cannot be dismantled."}), 409

        # Повертаємо кількість товарів та пакувань на склад.
        gift_set_products = db_session.query(GiftSetProduct).filter_by(gift_set_id=gift_set.id).all()
        for item in gift_set_products:
            product = db_session.query(Product).filter(Product.id == item.product_id).with_for_update().one_or_none()
            if product:
                quantity_before = product.available_quantity
                product.available_quantity += item.quantity
                product.reserved_quantity -= item.quantity
                db_session.add(StockHistory(product_id=product.id, change_amount=item.quantity, change_type='gift_set_unreserve', timestamp=datetime.now(), quantity_before=quantity_before, quantity_after=product.available_quantity, reason='Gift set dismantled'))
            db_session.delete(item)

        gift_set_packagings = db_session.query(GiftSetPackaging).filter_by(gift_set_id=gift_set.id).all()
        for item in gift_set_packagings:
            packaging = db_session.query(PackagingMaterial).filter(PackagingMaterial.id == item.packaging_id).with_for_update().one_or_none()
            if packaging:
                packaging.available_quantity += item.quantity
                packaging.reserved_quantity -= item.quantity
                db_session.add(PackagingStockHistory(material_id=packaging.id, change_amount=item.quantity, change_type='gift_set_unreserve', timestamp=datetime.now()))
            db_session.delete(item)

        # Видаляємо сам набір.
        db_session.delete(gift_set)

        # Повернення залишків, видалення історії та набору — одна транзакція.
        db_session.commit()

        return jsonify({"message": "Gift set and all related data dismantled successfully"}), 200
    except Exception:
        db_session.rollback()
        return jsonify({"error": "Failed to dismantle gift set"}), 500

@gift_box_services_bp.route('/sell_gift_set/<int:gift_set_id>', methods=['POST'])
def sell_gift_set(gift_set_id):
    from postgreSQLConnect import db_session

    try:
        gift_set = db_session.query(GiftSet).filter(
            GiftSet.id == gift_set_id
        ).with_for_update().populate_existing().one_or_none()

        if not gift_set:
            return jsonify({"error": "Gift set not found"}), 404

        if gift_set.is_sold or db_session.query(GiftSetSalesHistory.id).filter_by(
            gift_set_id=gift_set.id
        ).first():
            db_session.rollback()
            return jsonify({"error": "Gift set has already been sold"}), 409

        data = request.json or {}
        customer = db_session.query(Customer).filter(
            Customer.id == data['customer_id']
        ).one_or_none()
        if customer is None:
            db_session.rollback()
            return jsonify({"error": "Customer not found"}), 404

        sold_price = Decimal(str(data['selling_price']))
        total_cost = Decimal("0.000")

        # Створюємо фінансовий знімок набору саме на момент продажу.
        sales_record = GiftSetSalesHistory(
            gift_set_id=gift_set.id,
            sold_price=float(sold_price),
            quantity=1,
            customer_id=customer.id,
        )
        db_session.add(sales_record)
        db_session.flush()

        for gift_set_product in gift_set.gift_set_products:
            product = db_session.query(Product).filter(
                Product.id == gift_set_product.product_id
            ).with_for_update().populate_existing().one()

            reserved_quantity = int(product.reserved_quantity or 0)
            if reserved_quantity < gift_set_product.quantity:
                db_session.rollback()
                return jsonify({"error": "Product reservation is inconsistent"}), 409

            unit_cost = Decimal(str(product.purchase_price_per_item or 0))
            total_cost += unit_cost * gift_set_product.quantity
            product.reserved_quantity = reserved_quantity - gift_set_product.quantity
            product.sold_quantity = int(product.sold_quantity or 0) + gift_set_product.quantity

            sales_record.sales_history_products.append(GiftSetSalesHistoryProduct(
                gift_set_product=gift_set_product,
                quantity=gift_set_product.quantity,
                unit_cost=unit_cost,
            ))

        for gift_set_packaging in gift_set.gift_set_packagings:
            packaging = db_session.query(PackagingMaterial).filter(
                PackagingMaterial.id == gift_set_packaging.packaging_id
            ).with_for_update().populate_existing().one()

            reserved_quantity = int(packaging.reserved_quantity or 0)
            if reserved_quantity < gift_set_packaging.quantity:
                db_session.rollback()
                return jsonify({"error": "Packaging reservation is inconsistent"}), 409

            unit_cost = Decimal(str(packaging.purchase_price_per_unit or 0))
            total_cost += unit_cost * gift_set_packaging.quantity
            packaging.reserved_quantity = reserved_quantity - gift_set_packaging.quantity
            packaging.sold_quantity = int(packaging.sold_quantity or 0) + gift_set_packaging.quantity

            sales_record.sales_history_packagings.append(GiftSetSalesHistoryPackaging(
                gift_set_packaging=gift_set_packaging,
                quantity=gift_set_packaging.quantity,
                unit_cost=unit_cost,
            ))

        sales_record.cost_price = total_cost
        sales_record.profit = sold_price - total_cost
        gift_set.is_sold = True

        # Фінансовий знімок, історія продажу та залишки фіксуються атомарно.
        db_session.commit()

        return jsonify({
            "message": "Gift set sold successfully",
            "sales_record": sales_record.to_dict()
        }), 200
    except (KeyError, ValueError, ArithmeticError):
        db_session.rollback()
        return jsonify({"error": "Invalid gift set sale data"}), 400
    except Exception:
        db_session.rollback()
        return jsonify({"error": "Failed to sell gift set"}), 500

@gift_box_services_bp.route('/get_all_gift_sets', methods=['GET'])
def get_gift_sets():
    # Отримуємо параметри для фільтрації (за потреби)
    name_filter = request.args.get('name', '').lower()
    min_price = request.args.get('min_price', type=float, default=0)
    max_price = request.args.get('max_price', type=float, default=float('inf'))
    from postgreSQLConnect import db_session

    # Пошук наборів подарунків за заданими фільтрами
    gift_sets_query = db_session.query(GiftSet).filter(
        GiftSet.total_price >= min_price,
        GiftSet.total_price <= max_price,
        GiftSet.is_sold == False  # ��ише не продані набори подарунків
    )

    if name_filter:
        gift_sets_query = gift_sets_query.filter(GiftSet.name.ilike(f'%{name_filter}%'))

    # Отримуємо всі набори
    gift_sets = gift_sets_query.all()

    # Перетворюємо кожен gift_set на словник для відповіді
    gift_sets_data = [gift_set.to_dict() for gift_set in gift_sets]

    return jsonify(gift_sets_data), 200


@gift_box_services_bp.route('/get_all_gift_set_sales_history', methods=['GET'])
def get_gift_set_sales_history():
    from postgreSQLConnect import db_session

    # Отримуємо всі записи історії продажів подарункових наборів
    gift_set_sales_history = db_session.query(GiftSetSalesHistory).all()

    # Підготовка даних для відповіді
    sales_data = []
    for sale in gift_set_sales_history:
        products_data = [
            {
                "product_id": item.gift_set_product.product_id,
                "name": item.gift_set_product.product.name,
                "quantity": item.quantity,
                "price": item.gift_set_product.product.selling_price_per_item,
                "unit_cost": float(item.unit_cost) if item.unit_cost is not None else None
            }
            for item in sale.sales_history_products
        ]

        packagings_data = [
            {
                "packaging_id": item.gift_set_packaging.packaging_id,
                "quantity": item.quantity,
                "price": item.gift_set_packaging.packaging.purchase_price_per_unit,
                "unit_cost": float(item.unit_cost) if item.unit_cost is not None else None
            }
            for item in sale.sales_history_packagings
        ]

        sale_data = {
            "id": sale.id,
            "gift_set_id": sale.gift_set_id,
            "sold_at": sale.sold_at.isoformat(),
            "sold_price": sale.sold_price,
            "cost_price": float(sale.cost_price) if sale.cost_price is not None else None,
            "profit": float(sale.profit) if sale.profit is not None else None,
            "quantity": sale.quantity,
            "customer_name": sale.customer_name,
            "products": products_data,
            "packagings": packagings_data
        }

        sales_data.append(sale_data)

    return jsonify(sales_data)
