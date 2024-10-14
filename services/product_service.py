# services/product_service.py

from models import Product, ProductCategory, Supplier, PurchaseHistory, StockHistory, Category, SaleHistory, Customer
from peewee import DoesNotExist
from decimal import Decimal
from flask import jsonify, Blueprint, request
from playhouse.shortcuts import model_to_dict
from datetime import datetime

# Створюємо Blueprint для продуктів
product_bp = Blueprint('products', __name__)


class ProductService:

    @staticmethod
    def get_product_by_id(product_id):
        """Отримати продукт за ID"""
        try:
            product = Product.get(Product.id == product_id)
            return model_to_dict(product, backrefs=True, exclude=[ProductCategory])
        except Product.DoesNotExist:
            return {'error': 'Product not found'}, 404

    @staticmethod
    def get_all_products():
        """Отримати всі товари з категоріями"""
        products = Product.select().prefetch(ProductCategory, Supplier)
        product_list = []
        for product in products:
            product_dict = model_to_dict(product, exclude=[ProductCategory])

            product_dict['purchase_total_price'] = float(product.purchase_total_price)
            product_dict['purchase_price_per_item'] = float(product.purchase_price_per_item)
            product_dict['selling_total_price'] = float(product.selling_total_price or 0)
            product_dict['selling_price_per_item'] = float(product.selling_price_per_item or 0)

            # Отримуємо категорії продукту
            product_dict['category_ids'] = [pc.category.id for pc in product.categories]

            # Додаємо постачальника продукту
            if product.supplier:
                product_dict['supplier'] = {
                    'id': product.supplier.id,
                    'name': product.supplier.name,
                    'contact_info': product.supplier.contact_info
                }
            else:
                product_dict['supplier'] = None

            product_list.append(product_dict)
        return product_list, 200

    @staticmethod
    def create_product(data):
        """Створення нового продукту та обробка закупки"""
        required_product_fields = ['name', 'category_ids', 'created_date']
        missing_product_fields = [field for field in required_product_fields if field not in data]

        if missing_product_fields:
            return {'error': f"Missing required fields for product: {', '.join(missing_product_fields)}"}, 400

        required_purchase_fields = ['quantity', 'purchase_price_per_item', 'purchase_total_price', 'supplier_id']
        missing_purchase_fields = [field for field in required_purchase_fields if field not in data]

        if missing_purchase_fields:
            return {'error': f"Missing required fields for purchase: {', '.join(missing_purchase_fields)}"}, 400

        # Валідація даних
        errors = ProductService.validate_product_data(data)
        if errors:
            return {'errors': errors}, 400

        try:
            product = Product.create(
                name=data['name'],
                quantity=0,
                created_date=data.get('created_date')
            )

            # Додаємо категорії
            category_ids = data.get('category_ids', [])
            if category_ids:
                ProductService.assign_categories_to_product(product, category_ids)

            supplier = Supplier.get(Supplier.id == data['supplier_id'])
            product.supplier = supplier

            product.purchase_total_price = Decimal(data['purchase_total_price'])
            product.purchase_price_per_item = Decimal(data['purchase_price_per_item'])
            product.quantity = data['quantity']
            product.selling_price_per_item = Decimal(data.get('selling_price_per_item', 0))
            product.save()

            # Створення записів в історії
            PurchaseHistory.create(
                product=product,
                purchase_price_per_item=Decimal(data['purchase_price_per_item']),
                purchase_total_price=Decimal(data['purchase_total_price']),
                supplier=supplier,
                quantity_purchase=data['quantity'],
                purchase_date=data.get('purchase_date')
            )

            StockHistory.create(
                product=product,
                change_amount=data['quantity'],
                change_type='create',
                timestamp=data.get('purchase_date')
            )

            return model_to_dict(product, backrefs=True), 201
        except Supplier.DoesNotExist:
            return {'error': 'Supplier not found'}, 404
        except Exception as e:
            return {'error': str(e)}, 500

    @staticmethod
    def validate_product_data(data):
        """Валідація вхідних даних для продукту"""
        errors = {}
        try:
            quantity = float(data['quantity'])
            if quantity <= 0:
                errors['quantity'] = "Quantity must be greater than 0."
        except ValueError:
            errors['quantity'] = "Quantity must be a valid number."

        try:
            purchase_price_per_item = float(data['purchase_price_per_item'])
            if purchase_price_per_item <= 0:
                errors['purchase_price_per_item'] = "Price per item must be greater than 0."
        except ValueError:
            errors['purchase_price_per_item'] = "Price per item must be a valid number."

        return errors

    @staticmethod
    def assign_categories_to_product(product, category_ids):
        """Призначити категорії для продукту"""
        categories = Category.select().where(Category.id.in_(category_ids))
        for category in categories:
            ProductCategory.create(product=product, category=category)


@product_bp.route('/api/product/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Оновити товар з валідацією і збереженням всіх змін"""
    data = request.get_json()

    # Перевірка обов'язкових полів
    required_fields = ['quantity', 'purchase_price_per_item', 'purchase_total_price', 'created_date']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f"Missing required fields: {', '.join(missing_fields)}"}), 400

    errors = {}

    # Валідація полів
    try:
        quantity = float(data['quantity'])
        if quantity < 0:
            errors['quantity'] = "Quantity must be greater than or equal to 0."
    except ValueError:
        errors['quantity'] = "Quantity must be a valid number."

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
        product = Product.get(Product.id == product_id)

        supplier_id = data.get('supplier_id')
        if supplier_id:
            try:
                supplier = Supplier.get(Supplier.id == supplier_id)
                product.supplier = supplier
            except Supplier.DoesNotExist:
                return jsonify({'error': 'Supplier not found'}), 404

        created_date = data.get('created_date')

        if created_date:
            product.created_date = created_date
        else:
            product.created_date = datetime.now()

        change_amount = data['quantity'] - product.quantity

        product.quantity = quantity
        product.purchase_total_price = purchase_total_price
        product.purchase_price_per_item = purchase_price_per_item
        product.selling_price_per_item = selling_price_per_item

        category_ids = data.get('category_ids', [])
        if category_ids:
            ProductCategory.delete().where(ProductCategory.product == product).execute()

            categories = Category.select().where(Category.id.in_(category_ids))
            for category in categories:
                ProductCategory.create(product=product, category=category)

        product.save()

        stock_history_record = StockHistory.get_or_none(
            (StockHistory.product == product) &
            (StockHistory.change_type == 'create')
        )

        if stock_history_record:
            stock_history_record.timestamp = created_date if created_date else datetime.now()
            stock_history_record.change_amount = quantity
            stock_history_record.save()

        else:
            StockHistory.create(
                product=product,
                change_amount=quantity,
                change_type='create',
                timestamp=created_date if created_date else datetime.now()
            )

        updated_product = model_to_dict(product, backrefs=True, exclude=[ProductCategory])
        return jsonify(updated_product), 200

    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404


# Створюємо Blueprint для продуктів і пов'язаних маршрутів
product_history_bp = Blueprint('product_history', __name__)


@product_history_bp.route('/api/product/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Видалити товар та всі пов'язані записи"""
    try:
        product = Product.get(Product.id == product_id)

        ProductCategory.delete().where(ProductCategory.product == product).execute()
        SaleHistory.delete().where(SaleHistory.product == product).execute()
        PurchaseHistory.delete().where(PurchaseHistory.product == product).execute()
        StockHistory.delete().where(StockHistory.product == product).execute()

        product.delete_instance()

        return jsonify({'message': 'Product and related records deleted successfully'}), 200
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404


@product_history_bp.route('/api/product/<int:product_id>/history', methods=['GET'])
def get_product_history(product_id):
    """Отримати історію змін запасів, покупок і продажів для товару"""
    try:
        product = Product.get(Product.id == product_id)

        # Історія змін запасів
        stock_history = StockHistory.select().where(StockHistory.product == product)
        stock_history_list = [
            {
                **model_to_dict(record),
                'timestamp': record.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
            for record in stock_history
        ]

        # Історія покупок
        purchase_history = PurchaseHistory.select().where(PurchaseHistory.product == product)
        purchase_history_list = [model_to_dict(purchase) for purchase in purchase_history]

        # Історія продажів
        sale_history = SaleHistory.select().where(SaleHistory.product == product)
        sale_history_list = [
            {
                **model_to_dict(sale),
                'selling_price_per_item': float(sale.selling_price_per_item),
                'selling_total_price': float(sale.selling_total_price)
            }
            for sale in sale_history
        ]

        combined_history = {
            'stock_history': stock_history_list,
            'purchase_history': purchase_history_list,
            'sale_history': sale_history_list
        }

        return jsonify(combined_history), 200
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404


@product_history_bp.route('/api/product/<int:product_id>/purchase', methods=['POST'])
def purchase_product(product_id):
    """Обробити покупку товару і записати в історію"""
    data = request.get_json()

    # Перевірка, чи продукт існує
    try:
        product = Product.get(Product.id == product_id)
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404

    # Валідація даних
    errors = validate_purchase_data(data)
    if errors:
        return jsonify({'errors': errors}), 400

    try:
        quantity = data['quantity']
        purchase_price_per_item = Decimal(data['purchase_price_per_item'])
        purchase_total_price = Decimal(data['purchase_total_price'])
        supplier_id = data.get('supplier_id')
        purchase_date = data.get('purchase_date', datetime.now())

        if supplier_id:
            try:
                supplier = Supplier.get(Supplier.id == supplier_id)
                product.supplier = supplier
            except Supplier.DoesNotExist:
                return jsonify({'error': 'Supplier not found'}), 404

        product.quantity += quantity
        product.purchase_total_price += purchase_total_price
        product.save()
        product.purchase_price_per_item = product.purchase_total_price / product.quantity
        product.save()

        PurchaseHistory.create(
            product=product,
            purchase_price_per_item=purchase_price_per_item,
            purchase_total_price=purchase_total_price,
            supplier=supplier if supplier_id else None,
            purchase_date=purchase_date,
            quantity_purchase=quantity
        )
    except KeyError as e:
        return jsonify({'error': f'Missing field: {str(e)}'}), 400

    return jsonify({'message': 'Purchase recorded successfully'}), 201


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


@product_history_bp.route('/api/product/<int:product_id>/sale', methods=['POST'])
def record_sale(product_id):
    """Записати продаж товару і додати в історію продажів"""
    data = request.get_json()

    # Перевірка, чи існує продукт
    try:
        product = Product.get(Product.id == product_id)
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404

    # Валідація даних
    errors = validate_sale_data(data)
    if errors:
        return jsonify({'errors': errors}), 400

    try:
        quantity_sold = data['quantity']
        selling_price_per_item = Decimal(data['selling_price_per_item'])
        selling_total_price = Decimal(data['selling_total_price'])

        # Перевірка, чи є достатня кількість товару на складі
        if product.quantity < quantity_sold:
            return jsonify({'error': 'Not enough quantity in stock'}), 400

        # Оновлення кількості товару
        product.quantity -= quantity_sold
        product.selling_quantity += quantity_sold
        product.selling_price_per_item = selling_price_per_item
        product.selling_total_price += selling_total_price
        product.save()

        # Створення нового запису продажу в історії
        customer = Customer.get(Customer.id == data['customer'])
        SaleHistory.create(
            product=product,
            customer=customer,
            quantity_sold=quantity_sold,
            selling_price_per_item=selling_price_per_item,
            selling_total_price=selling_total_price,
            sale_date=data.get('sale_date', datetime.now())
        )

        return jsonify({'message': 'Sale recorded successfully'}), 201

    except KeyError as e:
        return jsonify({'error': f'Missing field: {str(e)}'}), 400

    except Customer.DoesNotExist:
        return jsonify({'error': 'Customer not found'}), 40



def validate_sale_data(data):
    """Validate sale data."""
    errors = {}
    required_fields = ['customer', 'quantity', 'selling_price_per_item', 'selling_total_price']
    for field in required_fields:
        if field not in data:
            errors[field] = f'Missing field: {field}'
    if data['quantity'] <= 0:
        errors['quantity'] = 'Quantity must be greater than 0.'
    if data['selling_price_per_item'] <= 0 or data['selling_total_price'] <= 0:
        errors['selling_price'] = 'Selling price and total price must be greater than 0.'
    return errors

