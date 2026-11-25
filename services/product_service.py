from sqlalchemy import insert, delete, or_, func

from models import Product, product_categories_table, Supplier, PurchaseHistory, StockHistory, Category, SaleHistory, \
    Customer, ReturnHistory, PackagingMaterial, PackagingSaleHistory, GiftSet, GiftSetProduct, GiftSetPackaging, \
    GiftSetSalesHistory, GiftSetSalesHistoryProduct, ProductAuditHistory, Payment, PackagingStockHistory, User
from flask import Blueprint, request
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import NoResultFound, SQLAlchemyError, IntegrityError
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from decimal import Decimal, InvalidOperation
from datetime import datetime

# Створюємо Blueprint для продуктів

product_bp = Blueprint('products', __name__)

def record_product_audit(db_session, product, action, changes, reason=None):
    """Append immutable before/after records for each changed product field."""
    try:
        identity = get_jwt_identity()
    except Exception:
        identity = None

    actor = None
    if identity is not None:
        try:
            actor = db_session.query(User).filter(User.id == int(identity)).one_or_none()
        except (TypeError, ValueError):
            actor = None

    for field_name, values in changes.items():
        old_value, new_value = values
        old_text = str(old_value) if old_value is not None else None
        new_text = str(new_value) if new_value is not None else None
        if old_text == new_text:
            continue

        db_session.add(ProductAuditHistory(
            product_id=product.id,
            changed_by_id=actor.id if actor else None,
            changed_by_username=actor.username if actor else "Невідомий користувач",
            action=action,
            field_name=field_name,
            old_value=old_text,
            new_value=new_text,
            reason=reason,
        ))



def generate_article_for_new_prod():
    from postgreSQLConnect import db_session

    last_product = db_session.query(Product).order_by(Product.id.desc()).first()
    if last_product and last_product.article.startswith("PRD-"):
        last_number = int(last_product.article.split("-")[1])
        new_number = last_number + 1
    else:
        new_number = 1
    return f"PRD-{new_number:04d}"


class ProductService:

    @staticmethod
    def get_product_by_id(product_id):
        from postgreSQLConnect import db_session

        """Отримати продукт за ID"""
        try:
            product = db_session.query(Product).filter(
            Product.id == product_id
        ).populate_existing().one()
            product_dict = product.to_dict()  # Assuming you have a method for dict conversion
            product_dict['category_ids'] = [category.id for category in product.categories]
            product_dict['supplier'] = product.supplier.to_dict() if product.supplier else None
            return product_dict, 200
        except NoResultFound:
            return {'error': 'Product not found'}, 404

    @staticmethod
    def get_all_products():
        from postgreSQLConnect import db_session

        """Отримати всі товари з категоріями"""
        products = db_session.query(Product).options(joinedload(Product.categories), joinedload(Product.supplier)).all()
        product_list = []
        for product in products:
            product_dict = product.to_dict()  # Assuming you have a method for dict conversion
            product_dict['purchase_total_price'] = float(product.purchase_total_price)
            product_dict['purchase_price_per_item'] = float(product.purchase_price_per_item)
            product_dict['selling_total_price'] = float(product.selling_total_price or 0)
            product_dict['selling_price_per_item'] = float(product.selling_price_per_item or 0)

            # Отримуємо категорії продукту
            product_dict['category_ids'] = [category.id for category in product.categories]

            # Додаємо постачальника продукту
            if product.supplier:
                product_dict['supplier'] = product.supplier.to_dict()

            else:
                product_dict['supplier'] = None

            product_list.append(product_dict)
        return product_list, 200

    @staticmethod
    def create_product(data):
        from postgreSQLConnect import db_session

        """Створення нового продукту та обробка закупки"""
        required_product_fields = ['name', 'category_ids', 'created_date']
        missing_product_fields = [field for field in required_product_fields if field not in data]

        if missing_product_fields:
            return {'error': f"Missing required fields for product: {', '.join(missing_product_fields)}"}, 400

        name = data.get('name')
        if not isinstance(name, str) or not name.strip():
            return {'error': 'Product name must not be empty'}, 400
        name = name.strip()
        if len(name) > 255:
            return {'error': 'Product name must not exceed 255 characters'}, 400

        if db_session.query(Product.id).filter(func.lower(func.trim(Product.name)) == name.lower()).first():
            return {'error': 'A product with this name already exists'}, 409

        required_purchase_fields = ['available_quantity', 'purchase_price_per_item', 'purchase_total_price',
                                    'supplier_id']
        missing_purchase_fields = [field for field in required_purchase_fields if field not in data]

        if missing_purchase_fields:
            return {'error': f"Missing required fields for purchase: {', '.join(missing_purchase_fields)}"}, 400

        errors = ProductService.validate_product_data(data)
        if errors:
            return {'errors': errors}, 400

        try:
            created_date_str = data.get('created_date')
            if created_date_str:
                created_date = datetime.strptime(created_date_str, '%Y-%m-%d').date()
            else:
                created_date = datetime.today().date()

            # Validate all foreign-key dependencies before creating the product.
            category_ids = data.get('category_ids', [])
            categories = []
            if category_ids:
                categories = db_session.query(Category).filter(Category.id.in_(category_ids)).all()
                if len(categories) != len(category_ids):
                    return {'error': 'Some categories were not found'}, 404

            supplier = db_session.query(Supplier).filter(
                Supplier.id == data['supplier_id']
            ).one_or_none()
            if not supplier:
                return {'error': 'Supplier not found'}, 404

            product = Product(
                name=name,
                total_quantity=0,
                available_quantity=0,
                created_date=created_date,
                article=generate_article_for_new_prod(),
                product_description=data['product_description']
            )

            db_session.add(product)
            if categories:
                product.categories.extend(categories)

            product.supplier = supplier
            product.purchase_total_price = Decimal(data['purchase_total_price'])
            product.purchase_price_per_item = Decimal(data['purchase_price_per_item'])
            product.total_quantity = data['available_quantity']
            product.available_quantity = data['available_quantity']
            product.selling_price_per_item = Decimal(data.get('selling_price_per_item', 0))

            # Obtain the generated ID without committing partial product state.
            db_session.flush()

            record_product_audit(
                db_session,
                product,
                "create",
                {
                    "available_quantity": (None, product.available_quantity),
                    "purchase_price_per_item": (None, product.purchase_price_per_item),
                    "selling_price_per_item": (None, product.selling_price_per_item),
                },
            )

            purchase_history = PurchaseHistory(
                product_id=product.id,
                purchase_price_per_item=Decimal(data['purchase_price_per_item']),
                purchase_total_price=Decimal(data['purchase_total_price']),
                supplier_id=supplier.id,
                quantity_purchase=data['available_quantity'],
                purchase_date=created_date,
            )
            db_session.add(purchase_history)

            stock_history = StockHistory(
                product_id=product.id,
                change_amount=data['available_quantity'],
                change_type='create',
                timestamp=created_date
            )
            db_session.add(stock_history)

            # Product and both history records are committed atomically.
            db_session.commit()
            return product.to_dict(), 201
        except NoResultFound:
            db_session.rollback()
            return {'error': 'Supplier not found'}, 404
        except IntegrityError as error:
            db_session.rollback()
            constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if constraint_name == "uq_products_name_normalized":
                return {'error': 'A product with this name already exists'}, 409
            return {'error': 'Database integrity error'}, 500
        except Exception as e:
            db_session.rollback()
            return {'error': str(e)}, 500

    @staticmethod
    def validate_product_data(data):
        """Валідація вхідних даних для продукту"""
        errors = {}
        try:
            quantity = float(data['available_quantity'])
            if quantity <= 0:
                errors['available_quantity'] = "Quantity must be greater than 0."
        except ValueError:
            errors['available_quantity'] = "Quantity must be a valid number."

        try:
            purchase_price_per_item = float(data['purchase_price_per_item'])
            if purchase_price_per_item <= 0:
                errors['purchase_price_per_item'] = "Price per item must be greater than 0."
        except ValueError:
            errors['purchase_price_per_item'] = "Price per item must be a valid number."

        return errors

    @staticmethod
    def assign_categories_to_product(product, category_ids):
        from postgreSQLConnect import db_session

        """Призначити категорії для продукту"""
        categories = db_session.query(Category).filter(Category.id.in_(category_ids)).all()
        for category in categories:
            product_category = product_categories_table(product_id=product.id, category_id=category.id)
            db_session.add(product_category)


@product_bp.route('/product/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    from postgreSQLConnect import db_session

    """Оновити товар з валідацією і збереженням всіх змін"""
    data = request.get_json()

    # Перевірка обов'язкових полів
    required_fields = ['name', 'available_quantity', 'purchase_price_per_item', 'purchase_total_price', 'created_date']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f"Missing required fields: {', '.join(missing_fields)}"}), 400

    name = data.get('name')
    if not isinstance(name, str) or not name.strip():
        return jsonify({'error': 'Product name must not be empty'}), 400
    name = name.strip()
    if len(name) > 255:
        return jsonify({'error': 'Product name must not exceed 255 characters'}), 400

    errors = {}

    # Валідація полів
    try:
        available_quantity = float(data['available_quantity'])
        if available_quantity < 0:
            errors['available_quantity'] = "available_quantity must be greater than or equal to 0."
    except ValueError:
        errors['available_quantity'] = "available_quantity must be a valid number."

    try:
        purchase_price_per_item = float(data['purchase_price_per_item'])
        if purchase_price_per_item < 0:
            errors['purchase_price_per_item'] = "Price per item must be greater than or equal to 0."
    except ValueError:
        errors['purchase_price_per_item'] = "Price per item must be a valid number."

    purchase_total_price = data.get('purchase_total_price')
    selling_price_per_item = data.get('selling_price_per_item')

    if errors:
        return jsonify({'errors': errors}), 400

    try:
        product = db_session.query(Product).filter(
            Product.id == product_id
        ).with_for_update().populate_existing().one()

        if db_session.query(Product.id).filter(
            func.lower(func.trim(Product.name)) == name.lower(),
            Product.id != product.id,
        ).first():
            db_session.rollback()
            return jsonify({'error': 'A product with this name already exists'}), 409

        supplier_id = data.get('supplier_id')
        if supplier_id:
            try:
                supplier = db_session.query(Supplier).filter(Supplier.id == supplier_id).one()
                product.supplier = supplier
            except NoResultFound:
                return jsonify({'error': 'Supplier not found'}), 404

        created_date = datetime.strptime(data.get('created_date'), "%Y-%m-%d")

        if created_date:
            product.created_date = created_date
        else:
            product.created_date = datetime.now()

        previous_values = {
            "name": product.name,
            "available_quantity": product.available_quantity,
            "purchase_price_per_item": product.purchase_price_per_item,
            "selling_price_per_item": product.selling_price_per_item,
        }

        product.name = name
        product.available_quantity = available_quantity
        product.purchase_total_price = purchase_total_price
        product.purchase_price_per_item = purchase_price_per_item
        product.selling_price_per_item = selling_price_per_item

        record_product_audit(
            db_session,
            product,
            "manual_edit",
            {
                "name": (previous_values["name"], product.name),
                "available_quantity": (previous_values["available_quantity"], product.available_quantity),
                "purchase_price_per_item": (previous_values["purchase_price_per_item"], product.purchase_price_per_item),
                "selling_price_per_item": (previous_values["selling_price_per_item"], product.selling_price_per_item),
            },
        )

        category_ids = data.get('category_ids', [])
        category_ids = data.get('category_ids', [])
        if category_ids:
            # Clear old categories first by deleting the association from the junction table
            db_session.query(product_categories_table).filter(
                product_categories_table.c.product_id == product.id).delete()

            # Fetch the new categories from the database
            categories = db_session.query(Category).filter(Category.id.in_(category_ids)).all()

            # Add new category associations to the product using insert
            for category in categories:
                db_session.execute(
                    insert(product_categories_table).values(product_id=product.id, category_id=category.id)
                )

        previous_quantity = previous_values["available_quantity"] or 0
        quantity_difference = available_quantity - previous_quantity
        if quantity_difference:
            db_session.add(StockHistory(
                product_id=product.id,
                change_amount=quantity_difference,
                change_type='manual_adjustment',
                timestamp=datetime.now(),
                quantity_before=previous_quantity,
                quantity_after=available_quantity,
                reason='Manual product edit',
            ))

        db_session.commit()

        updated_product = product.to_dict()  # Assuming you have a method to convert to dict
        return jsonify(updated_product), 200

    except NoResultFound:
        db_session.rollback()
        return jsonify({'error': 'Product not found'}), 404
    except IntegrityError as error:
        db_session.rollback()
        constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        if constraint_name == "uq_products_name_normalized":
            return jsonify({'error': 'A product with this name already exists'}), 409
        return jsonify({'error': 'Database integrity error'}), 500


@product_bp.route('/delete_all_products', methods=['DELETE'])
def delete_all_products():
    """

    Видалення всіх товарів та пов'язаних із ними записів.
    """
    from postgreSQLConnect import db_session

    try:
        # Не дозволяємо масове видалення, якщо воно знищить історичні записи.
        has_history = any((
            db_session.query(ReturnHistory.id).first(),
            db_session.query(SaleHistory.id).first(),
            db_session.query(StockHistory.id).first(),
            db_session.query(PurchaseHistory.id).first(),
            db_session.query(GiftSetSalesHistory.id).first(),
            db_session.query(GiftSetProduct.id).first(),
        ))
        if has_history:
            return jsonify({
                'error': 'Products cannot be bulk-deleted while historical records or gift set references exist. Archive functionality is required instead.'
            }), 409

        db_session.execute(delete(Product))

        # Коміт транзакції
        db_session.commit()
        print("Усі товари та пов'язані записи успішно видалено.")

        # Повернення успішної відповіді
        return jsonify({'message': 'Усі товари та пов’язані записи успішно видалено.'}), 200
    except SQLAlchemyError as e:
        # У разі помилки відкотити транзакцію
        db_session.rollback()
        print(f"Помилка під час видалення: {str(e)}")
        return jsonify({'error': f'Помилка під час видалення: {str(e)}'}), 500


# Створюємо Blueprint для продуктів і пов'язаних маршрутів
product_history_bp = Blueprint('product_history', __name__)


@product_history_bp.route('/product/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Delete a product, optionally removing only records directly related to it."""
    from postgreSQLConnect import db_session

    delete_mode = request.args.get('mode', 'product_only')
    if delete_mode not in {'product_only', 'all_related'}:
        return jsonify({'error': 'Invalid product deletion mode'}), 400

    try:
        product = db_session.query(Product).filter(
            Product.id == product_id
        ).with_for_update().populate_existing().one()

        related_queries = (
            db_session.query(SaleHistory.id).filter(SaleHistory.product_id == product.id),
            db_session.query(PurchaseHistory.id).filter(PurchaseHistory.product_id == product.id),
            db_session.query(StockHistory.id).filter(StockHistory.product_id == product.id),
            db_session.query(ReturnHistory.id).filter(ReturnHistory.product_id == product.id),
            db_session.query(GiftSetProduct.id).filter(GiftSetProduct.product_id == product.id),
            db_session.query(ProductAuditHistory.id).filter(ProductAuditHistory.product_id == product.id),
        )
        has_related_data = any(query.first() for query in related_queries)

        if has_related_data and delete_mode == 'product_only':
            db_session.rollback()
            return jsonify({
                'error': 'Product has related records. Choose deletion with all related data or keep the product.'
            }), 409

        if delete_mode == 'all_related':
            sale_ids = db_session.query(SaleHistory.id).filter(
                SaleHistory.product_id == product.id
            ).subquery()
            gift_set_product_ids = db_session.query(GiftSetProduct.id).filter(
                GiftSetProduct.product_id == product.id
            ).subquery()
            affected_gift_set_ids = [
                row[0] for row in db_session.query(GiftSetProduct.gift_set_id).filter(
                    GiftSetProduct.product_id == product.id
                ).all()
            ]

            has_sold_gift_set_reference = db_session.query(GiftSetSalesHistoryProduct.id).join(
                GiftSetProduct,
                GiftSetSalesHistoryProduct.gift_set_product_id == GiftSetProduct.id,
            ).filter(GiftSetProduct.product_id == product.id).first()
            if has_sold_gift_set_reference:
                db_session.rollback()
                return jsonify({
                    'error': 'Product is part of a sold gift set. Delete is blocked to preserve gift-set sales history.'
                }), 409

            # Restore packaging stock consumed by this product's sales before removing their records.
            packaging_sale_records = db_session.query(PackagingSaleHistory).filter(
                PackagingSaleHistory.sale_id.in_(sale_ids)
            ).all()
            for packaging_sale in packaging_sale_records:
                if packaging_sale.packaging_material_id is None:
                    continue
                packaging_material = db_session.query(PackagingMaterial).filter(
                    PackagingMaterial.id == packaging_sale.packaging_material_id
                ).with_for_update().one_or_none()
                if packaging_material is None:
                    continue
                packaging_material.available_quantity += packaging_sale.packaging_quantity
                packaging_material.available_stock_cost += packaging_sale.total_packaging_cost
                if packaging_material.available_quantity > 0 and packaging_material.status == 'used':
                    packaging_material.status = 'available'
                db_session.add(PackagingStockHistory(
                    material_id=packaging_material.id,
                    change_amount=packaging_sale.packaging_quantity,
                    change_type='product_delete_restore',
                    timestamp=datetime.now(),
                ))

            # Remove child records first; shared customers, suppliers and packaging materials remain untouched.
            db_session.query(Payment).filter(Payment.sale_id.in_(sale_ids)).delete(synchronize_session=False)
            db_session.query(PackagingSaleHistory).filter(
                PackagingSaleHistory.sale_id.in_(sale_ids)
            ).delete(synchronize_session=False)
            db_session.query(ReturnHistory).filter(
                ReturnHistory.product_id == product.id
            ).delete(synchronize_session=False)
            db_session.query(GiftSetSalesHistoryProduct).filter(
                GiftSetSalesHistoryProduct.gift_set_product_id.in_(gift_set_product_ids)
            ).delete(synchronize_session=False)
            db_session.query(GiftSetProduct).filter(
                GiftSetProduct.product_id == product.id
            ).delete(synchronize_session=False)

            # Recalculate affected unsold gift sets after removing this product from their composition.
            for gift_set_id in affected_gift_set_ids:
                gift_set = db_session.query(GiftSet).filter(
                    GiftSet.id == gift_set_id
                ).with_for_update().one_or_none()
                if gift_set is None:
                    continue

                remaining_products = db_session.query(GiftSetProduct).filter_by(
                    gift_set_id=gift_set_id
                ).all()
                remaining_packagings = db_session.query(GiftSetPackaging).filter_by(
                    gift_set_id=gift_set_id
                ).all()

                if not remaining_products and not remaining_packagings:
                    db_session.delete(gift_set)
                    continue

                product_cost = sum(
                    (item.product.purchase_price_per_item or 0) * item.quantity
                    for item in remaining_products
                )
                packaging_cost = sum(
                    (item.packaging.purchase_price_per_unit or 0) * item.quantity
                    for item in remaining_packagings
                )
                gift_set.total_price = product_cost + packaging_cost

            db_session.query(SaleHistory).filter(
                SaleHistory.product_id == product.id
            ).delete(synchronize_session=False)
            db_session.query(PurchaseHistory).filter(
                PurchaseHistory.product_id == product.id
            ).delete(synchronize_session=False)
            db_session.query(StockHistory).filter(
                StockHistory.product_id == product.id
            ).delete(synchronize_session=False)
            db_session.query(ProductAuditHistory).filter(
                ProductAuditHistory.product_id == product.id
            ).delete(synchronize_session=False)

        db_session.query(product_categories_table).filter(
            product_categories_table.c.product_id == product.id
        ).delete(synchronize_session=False)
        db_session.delete(product)
        db_session.commit()

        message = (
            'Product and all related records deleted successfully'
            if delete_mode == 'all_related'
            else 'Product deleted successfully'
        )
        return jsonify({'message': message}), 200
    except NoResultFound:
        db_session.rollback()
        return jsonify({'error': 'Product not found'}), 404
    except SQLAlchemyError:
        db_session.rollback()
        return jsonify({'error': 'Database error while deleting product'}), 500


class InventoryConflict(Exception):
    pass


@product_history_bp.route('/product/<int:product_id>/inventory', methods=['POST'])
@jwt_required()
def inventory_product(product_id):
    from postgreSQLConnect import db_session

    data = request.get_json(silent=True) or {}
    raw_actual_quantity = data.get('actual_quantity')

    if isinstance(raw_actual_quantity, bool):
        return jsonify({'error': 'actual_quantity must be a non-negative integer'}), 400

    try:
        actual_quantity = int(raw_actual_quantity)
    except (TypeError, ValueError):
        return jsonify({'error': 'actual_quantity must be a non-negative integer'}), 400

    if isinstance(raw_actual_quantity, float) and not raw_actual_quantity.is_integer():
        return jsonify({'error': 'actual_quantity must be a non-negative integer'}), 400

    if actual_quantity < 0:
        return jsonify({'error': 'actual_quantity must be a non-negative integer'}), 400

    reason = data.get('reason')
    if reason is not None and not isinstance(reason, str):
        return jsonify({'error': 'reason must be a string'}), 400
    reason = reason.strip() or None if reason is not None else None

    raw_inventory_date = data.get('inventory_date')
    if raw_inventory_date is None:
        inventory_date = datetime.now().date()
    elif not isinstance(raw_inventory_date, str):
        return jsonify({'error': 'inventory_date must use YYYY-MM-DD format'}), 400
    else:
        try:
            inventory_date = datetime.strptime(raw_inventory_date, '%Y-%m-%d').date()
            if inventory_date.isoformat() != raw_inventory_date:
                raise ValueError
        except ValueError:
            return jsonify({'error': 'inventory_date must use YYYY-MM-DD format'}), 400

    try:
        # Блокуємо інвентаризований товар до читання наборів, щоб нове резервування
        # не могло пройти паралельно з інвентаризацією.
        product = db_session.query(Product).filter(
            Product.id == product_id
        ).with_for_update().populate_existing().one_or_none()
        if not product:
            db_session.rollback()
            return jsonify({'error': 'Product not found'}), 404

        # Беремо лише непродані набори, у складі яких є інвентаризований товар.
        gift_sets = db_session.query(GiftSet).join(
            GiftSetProduct, GiftSetProduct.gift_set_id == GiftSet.id
        ).filter(
            GiftSetProduct.product_id == product_id,
            or_(GiftSet.is_sold.is_(False), GiftSet.is_sold.is_(None))
        ).with_for_update().all()

        gift_set_ids = [gift_set.id for gift_set in gift_sets]

        if gift_set_ids:
            # Не дозволяємо видалити набір, якщо для нього вже існує історія продажу.
            has_sales_history = db_session.query(GiftSetSalesHistory.id).filter(
                GiftSetSalesHistory.gift_set_id.in_(gift_set_ids)
            ).first()
            if has_sales_history:
                raise InventoryConflict(
                    'An unsold gift set has sales history and cannot be safely removed'
                )

            gift_set_products = db_session.query(GiftSetProduct).filter(
                GiftSetProduct.gift_set_id.in_(gift_set_ids)
            ).all()
            gift_set_packagings = db_session.query(GiftSetPackaging).filter(
                GiftSetPackaging.gift_set_id.in_(gift_set_ids)
            ).all()
        else:
            gift_set_products = []
            gift_set_packagings = []

        # Блокуємо всі товари та пакування, резерви яких будемо повертати.
        product_ids = sorted({item.product_id for item in gift_set_products if item.product_id != product_id})
        if product_ids:
            other_products = db_session.query(Product).filter(
                Product.id.in_(product_ids)
            ).order_by(Product.id).with_for_update().populate_existing().all()
        else:
            other_products = []
        products_by_id = {item.id: item for item in other_products}
        products_by_id[product_id] = product

        packaging_ids = sorted({item.packaging_id for item in gift_set_packagings})
        if packaging_ids:
            locked_packagings = db_session.query(PackagingMaterial).filter(
                PackagingMaterial.id.in_(packaging_ids)
            ).order_by(PackagingMaterial.id).with_for_update().all()
        else:
            locked_packagings = []
        packagings_by_id = {packaging.id: packaging for packaging in locked_packagings}

        product = products_by_id.get(product_id)
        if not product:
            return jsonify({'error': 'Product not found'}), 404

        quantity_before = (product.available_quantity or 0) + (product.reserved_quantity or 0)

        # Повертаємо на склад усі складові кожного видаленого набору.
        for item in gift_set_products:
            related_product = products_by_id.get(item.product_id)
            if not related_product or not item.quantity or item.quantity < 0:
                raise InventoryConflict('Gift set contains an invalid product item')

            reserved_quantity = related_product.reserved_quantity or 0
            if reserved_quantity < item.quantity:
                raise InventoryConflict(
                    f'Reserved quantity is inconsistent for product {related_product.id}'
                )

            related_product.available_quantity = (related_product.available_quantity or 0) + item.quantity
            related_product.reserved_quantity = reserved_quantity - item.quantity

        for item in gift_set_packagings:
            packaging = packagings_by_id.get(item.packaging_id)
            if not packaging or not item.quantity or item.quantity < 0:
                raise InventoryConflict('Gift set contains an invalid packaging item')

            reserved_quantity = packaging.reserved_quantity or 0
            if reserved_quantity < item.quantity:
                raise InventoryConflict(
                    f'Reserved quantity is inconsistent for packaging {packaging.id}'
                )

            packaging.available_quantity = (packaging.available_quantity or 0) + item.quantity
            packaging.reserved_quantity = reserved_quantity - item.quantity

        # Видаляємо склад наборів та самі непродані набори.
        for item in gift_set_products:
            db_session.delete(item)
        for item in gift_set_packagings:
            db_session.delete(item)

        # Спочатку фізично видаляємо дочірні рядки, потім набори bulk-delete,
        # щоб ORM не намагався обнулити NOT NULL gift_set_id у зв'язках.
        db_session.flush()
        if gift_set_ids:
            db_session.query(GiftSet).filter(
                GiftSet.id.in_(gift_set_ids),
                or_(GiftSet.is_sold.is_(False), GiftSet.is_sold.is_(None))
            ).delete(synchronize_session=False)

        # Усі резерви інвентаризованого товару скасовані разом із його непроданими наборами.
        product.reserved_quantity = 0
        product.available_quantity = actual_quantity

        change_amount = actual_quantity - quantity_before
        record_product_audit(
            db_session,
            product,
            "inventory",
            {"available_quantity": (product.available_quantity, actual_quantity)},
            reason=reason,
        )
        stock_history = StockHistory(
            product_id=product.id,
            change_amount=change_amount,
            change_type='inventory',
            timestamp=datetime.now(),
            inventory_date=inventory_date,
            quantity_before=quantity_before,
            quantity_after=actual_quantity,
            reason=reason
        )
        db_session.add(stock_history)

        # Усі зміни фіксуються одним commit.
        db_session.commit()

        return jsonify({
            'message': 'Inventory completed successfully',
            'product_id': product.id,
            'quantity_before': quantity_before,
            'quantity_after': actual_quantity,
            'change_amount': change_amount,
            'deleted_gift_sets': gift_set_ids,
            'available_quantity': product.available_quantity,
            'reserved_quantity': product.reserved_quantity,
            'stock_history': stock_history.to_dict()
        }), 200

    except InventoryConflict as e:
        db_session.rollback()
        return jsonify({'error': str(e)}), 409
    except SQLAlchemyError:
        db_session.rollback()
        return jsonify({'error': 'Database error during inventory'}), 500
    except Exception:
        db_session.rollback()
        return jsonify({'error': 'Unexpected error during inventory'}), 500


@product_history_bp.route('/product/<int:product_id>/history', methods=['GET'])
def get_product_history(product_id):
    """Get history of stock, purchase, and sales changes for a product."""
    try:
        from postgreSQLConnect import db_session

        product = db_session.query(Product).filter(
            Product.id == product_id
        ).with_for_update().populate_existing().one()

        # Stock History
        stock_history = db_session.query(StockHistory).filter(StockHistory.product_id == product.id).all()
        stock_history_list = [
            {
                **record.to_dict(),
                'timestamp': record.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
            for record in stock_history
        ]

        # Purchase History
        purchase_history = db_session.query(PurchaseHistory).filter(PurchaseHistory.product_id == product.id).all()
        purchase_history_list = [record.to_dict() for record in purchase_history]

        # Query SaleHistory for a specific product
        sale_history = db_session.query(SaleHistory).filter(SaleHistory.product_id == product.id).all()

        # Prepare a list of dictionaries with the required details
        sale_history_list = [
            {
                **record.to_dict(include_customer=True),  # Include customer details in the response
                'selling_price_per_item': float(record.selling_price_per_item),
                'selling_total_price': float(record.selling_total_price)
            }
            for record in sale_history
        ]

        audit_history = db_session.query(ProductAuditHistory).filter(
            ProductAuditHistory.product_id == product.id
        ).order_by(ProductAuditHistory.changed_at.desc(), ProductAuditHistory.id.desc()).all()
        audit_history_list = [
            {
                'id': record.id,
                'product_id': record.product_id,
                'changed_by_id': record.changed_by_id,
                'changed_by_username': record.changed_by_username,
                'action': record.action,
                'field_name': record.field_name,
                'old_value': record.old_value,
                'new_value': record.new_value,
                'reason': record.reason,
                'changed_at': record.changed_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for record in audit_history
        ]

        combined_history = {
            'stock_history': stock_history_list,
            'purchase_history': purchase_history_list,
            'sale_history': sale_history_list,
            'audit_history': audit_history_list,
        }

        return jsonify(combined_history), 200
    except NoResultFound:
        return jsonify({'error': 'Product not found'}), 404


@product_history_bp.route('/product/<int:product_id>/purchase', methods=['POST'])
def purchase_product(product_id):
    """Handle product purchase and record it atomically with stock and cost updates."""
    data = request.get_json()
    from postgreSQLConnect import db_session

    errors = validate_purchase_data(data)
    if errors:
        return jsonify({'errors': errors}), 400

    try:
        product = db_session.query(Product).filter(
            Product.id == product_id
        ).with_for_update().populate_existing().one()

        quantity = data['quantity']
        purchase_price_per_item = Decimal(data['purchase_price_per_item'])
        purchase_total_price = Decimal(data['purchase_total_price'])
        supplier_id = data.get('supplier_id')
        supplier = None

        purchase_date_str = data.get('purchase_date', datetime.now().strftime('%Y-%m-%d'))
        purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()

        if supplier_id:
            supplier = db_session.query(Supplier).filter(
                Supplier.id == supplier_id
            ).one_or_none()
            if supplier is None:
                db_session.rollback()
                return jsonify({'error': 'Supplier not found'}), 404
            product.supplier = supplier

        previous_available_quantity = product.available_quantity
        previous_purchase_price = product.purchase_price_per_item

        product.total_quantity += quantity
        product.available_quantity += quantity
        product.purchase_total_price += purchase_total_price
        product.purchase_price_per_item = purchase_price_per_item

        record_product_audit(
            db_session,
            product,
            "purchase",
            {
                "available_quantity": (previous_available_quantity, product.available_quantity),
                "purchase_price_per_item": (previous_purchase_price, product.purchase_price_per_item),
            },
        )

        purchase_history = PurchaseHistory(
            product_id=product.id,
            purchase_price_per_item=purchase_price_per_item,
            purchase_total_price=purchase_total_price,
            supplier_id=supplier.id if supplier else None,
            purchase_date=purchase_date,
            quantity_purchase=quantity
        )
        db_session.add(purchase_history)
        db_session.add(StockHistory(
            product_id=product.id,
            change_amount=quantity,
            change_type='purchase',
            timestamp=datetime.now(),
            quantity_before=previous_available_quantity,
            quantity_after=product.available_quantity,
            reason='Purchase recorded',
        ))

        # Stock, financial totals and purchase history share one transaction.
        db_session.commit()
        return jsonify({'message': 'Purchase recorded successfully'}), 201
    except NoResultFound:
        db_session.rollback()
        return jsonify({'error': 'Product not found'}), 404
    except KeyError as e:
        db_session.rollback()
        return jsonify({'error': f'Missing field: {str(e)}'}), 400
    except SQLAlchemyError:
        db_session.rollback()
        return jsonify({'error': 'Database error during purchase'}), 500
    except Exception:
        db_session.rollback()
        return jsonify({'error': 'Unexpected error during purchase'}), 500


@product_history_bp.route('/product/<int:product_id>/sale', methods=['POST'])
def record_sale(product_id):
    """Record a sale and all related stock/history changes atomically."""
    data = request.get_json()
    from postgreSQLConnect import db_session

    errors = validate_sale_data(data)
    if errors:
        return jsonify({'errors': errors}), 400

    try:
        product = db_session.query(Product).filter(
            Product.id == product_id
        ).with_for_update().populate_existing().one()

        quantity_sold = data['quantity']
        selling_price_per_item = Decimal(data['selling_price_per_item'])
        selling_total_price = Decimal(data['selling_total_price'])
        total_packaging_cost = Decimal(data.get('total_packaging_cost', 0))
        packaging_material_id = data.get('packaging_id') or None
        packaging_quantity = data.get('packaging_quantity', 0)

        if quantity_sold <= 0:
            db_session.rollback()
            return jsonify({'error': 'Quantity sold must be greater than zero'}), 400
        if selling_price_per_item <= 0:
            db_session.rollback()
            return jsonify({'error': 'Selling price must be greater than zero'}), 400
        if product.available_quantity < quantity_sold:
            db_session.rollback()
            return jsonify({'error': 'Not enough quantity in stock'}), 400

        customer = db_session.query(Customer).filter(
            Customer.id == data['customer']
        ).one_or_none()
        if customer is None:
            db_session.rollback()
            return jsonify({'error': 'Customer not found'}), 404

        sale_date_str = data.get('sale_date')
        sale_date = (
            datetime.strptime(sale_date_str, '%Y-%m-%d')
            if sale_date_str else datetime.now()
        )

        packaging_material = None
        if packaging_material_id:
            packaging_material = db_session.query(PackagingMaterial).filter(
                PackagingMaterial.id == packaging_material_id
            ).with_for_update().one_or_none()
            if packaging_material is None:
                db_session.rollback()
                return jsonify({'error': 'Packaging material not found'}), 404
            if packaging_material.available_quantity < packaging_quantity:
                db_session.rollback()
                return jsonify({'error': 'Not enough packaging material available'}), 400

        previous_available_quantity = product.available_quantity
        previous_selling_price = product.selling_price_per_item

        product.available_quantity -= quantity_sold
        product.selling_quantity += quantity_sold
        product.sold_quantity += quantity_sold
        product.selling_price_per_item = selling_price_per_item

        record_product_audit(
            db_session,
            product,
            "sale",
            {
                "available_quantity": (previous_available_quantity, product.available_quantity),
                "selling_price_per_item": (previous_selling_price, product.selling_price_per_item),
            },
        )
        product.selling_total_price += selling_total_price

        sale_history = SaleHistory(
            product_id=product.id,
            customer_id=customer.id,
            quantity_sold=quantity_sold,
            selling_price_per_item=selling_price_per_item,
            selling_total_price=selling_total_price,
            sale_date=sale_date,
            packaging_material_id=packaging_material_id,
            profit=(
                (selling_price_per_item - product.purchase_price_per_item) * quantity_sold
            ) - total_packaging_cost,
            packaging_quantity=packaging_quantity,
            total_packaging_cost=total_packaging_cost
        )
        db_session.add(sale_history)
        db_session.add(StockHistory(
            product_id=product.id,
            change_amount=-quantity_sold,
            change_type='sale',
            timestamp=sale_date,
            quantity_before=previous_available_quantity,
            quantity_after=product.available_quantity,
            reason='Sale recorded',
        ))
        db_session.flush()

        if packaging_material is not None:
            packaging_material.available_quantity -= packaging_quantity
            packaging_material.available_stock_cost -= total_packaging_cost
            if packaging_material.available_quantity == 0:
                packaging_material.status = 'used'

            db_session.add(PackagingSaleHistory(
                sale_id=sale_history.id,
                packaging_material_id=packaging_material_id,
                packaging_quantity=packaging_quantity,
                total_packaging_cost=total_packaging_cost,
                sale_date=sale_date
            ))

        # Product, packaging and both history records share one commit boundary.
        db_session.commit()
        return jsonify({'message': 'Sale recorded successfully'}), 201
    except NoResultFound:
        db_session.rollback()
        return jsonify({'error': 'Product or Customer not found'}), 404
    except KeyError as e:
        db_session.rollback()
        return jsonify({'error': f'Missing field: {str(e)}'}), 400
    except SQLAlchemyError:
        db_session.rollback()
        return jsonify({'error': 'Database error during sale'}), 500
    except Exception:
        db_session.rollback()
        return jsonify({'error': 'Unexpected error during sale'}), 500


@product_history_bp.route('/delete-history/<int:product_id>/<string:history_type>/<int:history_id>',
                          methods=['DELETE'])
def delete_product_history(product_id, history_type, history_id):
    from postgreSQLConnect import db_session

    if history_type not in {'stock', 'purchase', 'sale'}:
        return jsonify({'error': 'Invalid history type'}), 400

    # Ledger entries are immutable: deleting an old event can invalidate later
    # stock movements, returns, payments and financial totals.
    return jsonify({'error': 'Historical records cannot be deleted. Record a correcting inventory adjustment or customer return instead.'}), 409


def delete_stock_history(product_id, history_id):
    """Delete stock history and verify product ID"""
    from postgreSQLConnect import db_session

    history = db_session.query(StockHistory).filter_by(id=history_id, product_id=product_id).first()
    if not history:
        return {'error': 'Stock history record not found or does not belong to this product'}
    if history.change_type == 'inventory':
        return {'error': 'Inventory records cannot be deleted; perform a new inventory instead'}

    product = history.product
    if history.change_type == 'add':
        product.available_quantity -= history.change_amount
    elif history.change_type == 'remove':
        product.available_quantity += history.change_amount
    db_session.delete(history)
    return {'success': True}


def delete_purchase_history(product_id, history_id):
    """Логіка видалення записів історії закупівель"""
    from postgreSQLConnect import db_session

    history = db_session.query(PurchaseHistory).filter_by(id=history_id, product_id=product_id).first()
    if not history:
        return {'error': 'Purchase history record not found'}

    product = history.product
    product.total_quantity -= history.quantity_purchase
    product.available_quantity -= history.quantity_purchase
    product.purchase_total_price -= history.purchase_total_price
    product.purchase_price_per_item = (
        float(product.purchase_total_price) / product.total_quantity
        if product.total_quantity > 0 else 0
    )

    db_session.delete(history)
    return {'success': True}


def delete_sale_history(product_id, history_id):
    """Логіка видалення записів історії продажів"""
    from postgreSQLConnect import db_session

    history = db_session.query(SaleHistory).filter_by(id=history_id, product_id=product_id).first()
    if not history:
        return {'error': 'Sale history record not found'}

    product = history.product
    product.available_quantity += history.quantity_sold
    product.sold_quantity -= history.quantity_sold
    product.selling_total_price -= history.selling_total_price
    product.selling_price_per_item = (
        product.selling_total_price / product.sold_quantity
        if product.sold_quantity > 0 else 0
    )

    # Якщо було використано пакувальні матеріали
    if history.packaging_material_id:
        packaging_material = db_session.query(PackagingMaterial).filter(
            PackagingMaterial.id == history.packaging_material_id).first()

        if packaging_material:
            # Відновлюємо кількість пакувальних матеріалів та їхню вартість
            packaging_material.available_quantity += history.packaging_quantity
            packaging_material.available_stock_cost += history.total_packaging_cost

            # Змінюємо статус, якщо матеріал більше не "used"
            if packaging_material.available_quantity > 0 and packaging_material.status == 'used':
                packaging_material.status = 'available'

            db_session.add(packaging_material)

        # Видаляємо запис із PackagingSaleHistory
        packaging_sale_history = db_session.query(PackagingSaleHistory).filter_by(
            sale_id=history.id, packaging_material_id=history.packaging_material_id).first()
        if packaging_sale_history:
            db_session.delete(packaging_sale_history)

    db_session.delete(history)
    return {'success': True}


def validate_sale_data(data):
    """Validate sale data."""
    errors = {}
    required_fields = ['customer', 'quantity', 'selling_price_per_item', 'selling_total_price']
    for field in required_fields:
        if field not in data:
            errors[field] = f'Missing field: {field}'

    if 'quantity' in data and data['quantity'] <= 0:
        errors['quantity'] = 'Quantity must be greater than 0.'

    try:
        selling_price_per_item = Decimal(str(data.get('selling_price_per_item', 0)))
        selling_total_price = Decimal(str(data.get('selling_total_price', 0)))
        if selling_price_per_item <= 0 or selling_total_price <= 0:
            errors['selling_price'] = 'Selling price and total price must be greater than 0.'
    except (InvalidOperation, TypeError, ValueError):
        errors['selling_price'] = 'Selling price and total price must be valid numbers.'

    return errors


def validate_purchase_data(data):
    """Validate purchase data."""
    errors = {}
    if 'quantity' not in data or data['quantity'] <= 0:
        errors['quantity'] = 'Quantity must be greater than 0.'
    if 'purchase_price_per_item' not in data or Decimal(data['purchase_price_per_item']) <= 0:
        errors['purchase_price_per_item'] = 'Price per item must be greater than 0.'
    if 'purchase_total_price' not in data or Decimal(data['purchase_total_price']) <= 0:
        errors['purchase_total_price'] = 'Total price must be greater than 0.'
    if 'supplier_id' not in data:
        errors['supplier_id'] = 'Supplier ID is required.'
    return errors