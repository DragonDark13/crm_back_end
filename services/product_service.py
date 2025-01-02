import logging

from sqlalchemy import insert

from models import Product, product_categories_table, Supplier, PurchaseHistory, StockHistory, Category, SaleHistory, \
    Customer
from flask import jsonify, Blueprint, request
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import NoResultFound
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from database import db_session  # Assuming `db_session` is the SQLAlchemy session
from flask import jsonify
from decimal import Decimal
from datetime import datetime

# Створюємо Blueprint для продуктів
product_bp = Blueprint('products', __name__)


class ProductService:

    @staticmethod
    def get_product_by_id(product_id):
        """Отримати продукт за ID"""
        try:
            product = db_session.query(Product).filter(Product.id == product_id).one()
            product_dict = product.to_dict()  # Assuming you have a method for dict conversion
            product_dict['category_ids'] = [category.id for category in product.categories]
            product_dict['supplier'] = {
                'id': product.supplier.id,
                'name': product.supplier.name,
                'contact_info': product.supplier.contact_info
            } if product.supplier else None
            return product_dict, 200
        except NoResultFound:
            return {'error': 'Product not found'}, 404

    @staticmethod
    def get_all_products():
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
            # Convert the 'created_date' string to a datetime object
            created_date_str = data.get('created_date')
            if created_date_str:
                created_date = datetime.strptime(created_date_str, '%Y-%m-%d').date()
            else:
                created_date = datetime.today().date()  # Default to today's date if not provided

            # Create the product
            product = Product(
                name=data['name'],
                total_quantity=0,
                available_quantity=0,
                created_date=created_date  # Pass the datetime object
            )

            # Add product to session before associating categories
            db_session.add(product)

            # Add categories to the product
            category_ids = data.get('category_ids', [])
            if category_ids:
                # Ensure categories exist
                categories = db_session.query(Category).filter(Category.id.in_(category_ids)).all()
                if len(categories) != len(category_ids):
                    return {'error': 'Some categories were not found'}, 404
                product.categories.extend(categories)

            # Assign supplier to the product
            supplier = db_session.query(Supplier).filter(Supplier.id == data['supplier_id']).one_or_none()
            if not supplier:
                return {'error': 'Supplier not found'}, 404

            product.supplier = supplier

            # Set purchase price and quantity values
            product.purchase_total_price = Decimal(data['purchase_total_price'])
            product.purchase_price_per_item = Decimal(data['purchase_price_per_item'])
            product.total_quantity = data['quantity']
            product.available_quantity = data['quantity']
            product.selling_price_per_item = Decimal(data.get('selling_price_per_item', 0))

            # Commit the product to the session
            db_session.commit()

            # Create purchase and stock history entries
            purchase_history = PurchaseHistory(
                product_id=product.id,
                purchase_price_per_item=Decimal(data['purchase_price_per_item']),
                purchase_total_price=Decimal(data['purchase_total_price']),
                supplier_id=supplier.id,
                quantity_purchase=data['quantity'],
                purchase_date=created_date  # Use the created_date here as well
            )
            db_session.add(purchase_history)

            stock_history = StockHistory(
                product_id=product.id,
                change_amount=data['quantity'],
                change_type='create',
                timestamp=created_date  # Use the created_date here
            )
            db_session.add(stock_history)

            db_session.commit()

            return product.to_dict(), 201
        except NoResultFound:
            return {'error': 'Supplier not found'}, 404
        except Exception as e:
            db_session.rollback()
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
        categories = db_session.query(Category).filter(Category.id.in_(category_ids)).all()
        for category in categories:
            product_category = product_categories_table(product_id=product.id, category_id=category.id)
            db_session.add(product_category)


@product_bp.route('/api/product/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Оновити товар з валідацією і збереженням всіх змін"""
    data = request.get_json()

    # Перевірка обов'язкових полів
    required_fields = ['available_quantity', 'purchase_price_per_item', 'purchase_total_price', 'created_date']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f"Missing required fields: {', '.join(missing_fields)}"}), 400

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
        product = db_session.query(Product).filter(Product.id == product_id).one()

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

        change_amount = data['available_quantity'] - product.available_quantity

        product.available_quantity = available_quantity
        product.purchase_total_price = purchase_total_price
        product.purchase_price_per_item = purchase_price_per_item
        product.selling_price_per_item = selling_price_per_item

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

            # Commit the transaction
            db_session.commit()
        stock_history_record = db_session.query(StockHistory).filter(
            StockHistory.product_id == product.id,
            StockHistory.change_type == 'create'
        ).first()

        if stock_history_record:
            stock_history_record.timestamp = created_date if created_date else datetime.now()
            stock_history_record.change_amount = available_quantity
            db_session.commit()

        else:
            stock_history = StockHistory(
                product_id=product.id,
                change_amount=available_quantity,
                change_type='create',
                timestamp=created_date if created_date else datetime.now()
            )
            db_session.add(stock_history)

        db_session.commit()

        updated_product = product.to_dict()  # Assuming you have a method to convert to dict
        return jsonify(updated_product), 200

    except NoResultFound:
        return jsonify({'error': 'Product not found'}),


# Створюємо Blueprint для продуктів і пов'язаних маршрутів
product_history_bp = Blueprint('product_history', __name__)


@product_history_bp.route('/api/product/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Delete product and all related records."""
    try:
        # Fetch the product
        product = db_session.query(Product).filter(Product.id == product_id).one()

        # Delete related records
        # Ensure the column name in the filter is correct (e.g., product_id or product_fk)
        db_session.query(product_categories_table).filter(product_categories_table.c.product_id == product.id).delete()
        db_session.query(SaleHistory).filter(SaleHistory.product_id == product.id).delete()
        db_session.query(PurchaseHistory).filter(PurchaseHistory.product_id == product.id).delete()
        db_session.query(StockHistory).filter(StockHistory.product_id == product.id).delete()

        # Delete the product itself
        db_session.delete(product)
        db_session.commit()

        return jsonify({'message': 'Product and related records deleted successfully'}), 200
    except NoResultFound:
        return jsonify({'error': 'Product not found'}), 404


@product_history_bp.route('/api/product/<int:product_id>/history', methods=['GET'])
def get_product_history(product_id):
    """Get history of stock, purchase, and sales changes for a product."""
    try:
        product = db_session.query(Product).filter(Product.id == product_id).one()

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

        combined_history = {
            'stock_history': stock_history_list,
            'purchase_history': purchase_history_list,
            'sale_history': sale_history_list
        }

        return jsonify(combined_history), 200
    except NoResultFound:
        return jsonify({'error': 'Product not found'}), 404


@product_history_bp.route('/api/product/<int:product_id>/purchase', methods=['POST'])
def purchase_product(product_id):
    """Handle product purchase and record in history."""
    data = request.get_json()

    # Validate data
    errors = validate_purchase_data(data)
    if errors:
        return jsonify({'errors': errors}), 400

    try:
        product = db_session.query(Product).filter(Product.id == product_id).one()

        quantity = data['quantity']
        purchase_price_per_item = Decimal(data['purchase_price_per_item'])
        purchase_total_price = Decimal(data['purchase_total_price'])
        supplier_id = data.get('supplier_id')

        # Convert purchase_date string to Python date object
        purchase_date_str = data.get('purchase_date', datetime.now().strftime('%Y-%m-%d'))
        purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()

        if supplier_id:
            supplier = db_session.query(Supplier).filter(Supplier.id == supplier_id).one_or_none()
            if supplier is None:
                return jsonify({'error': 'Supplier not found'}), 404
            product.supplier = supplier

        product.total_quantity += quantity
        product.available_quantity += quantity
        product.selling_total_price += purchase_total_price
        product.purchase_total_price += purchase_total_price
        product.purchase_price_per_item = product.purchase_total_price / product.total_quantity
        db_session.commit()

        # Create PurchaseHistory record
        purchase_history = PurchaseHistory(
            product_id=product.id,
            purchase_price_per_item=purchase_price_per_item,
            purchase_total_price=purchase_total_price,
            supplier_id=supplier.id if supplier else None,
            purchase_date=purchase_date,
            quantity_purchase=quantity
        )
        db_session.add(purchase_history)
        db_session.commit()

        return jsonify({'message': 'Purchase recorded successfully'}), 201
    except NoResultFound:
        return jsonify({'error': 'Product not found'}), 404
    except KeyError as e:
        return jsonify({'error': f'Missing field: {str(e)}'}), 400


@product_history_bp.route('/api/product/<int:product_id>/sale', methods=['POST'])
def record_sale(product_id):
    """Record a sale for a product and update sale history."""
    data = request.get_json()

    # Validate data
    errors = validate_sale_data(data)
    if errors:
        return jsonify({'errors': errors}), 400

    try:
        product = db_session.query(Product).filter(Product.id == product_id).one()

        quantity_sold = data['quantity']
        selling_price_per_item = Decimal(data['selling_price_per_item'])
        selling_total_price = Decimal(data['selling_total_price'])

        if product.available_quantity < quantity_sold:
            return jsonify({'error': 'Not enough quantity in stock'}), 400

        product.available_quantity -= quantity_sold
        product.selling_quantity += quantity_sold
        product.sold_quantity += quantity_sold
        product.selling_price_per_item = selling_price_per_item
        product.selling_total_price += selling_total_price
        db_session.commit()

        customer = db_session.query(Customer).filter(Customer.id == data['customer']).one()

        # Convert sale_date string to a datetime object if it's provided
        sale_date_str = data.get('sale_date', None)
        if sale_date_str:
            sale_date = datetime.strptime(sale_date_str, '%Y-%m-%d')
        else:
            sale_date = datetime.now()

        sale_history = SaleHistory(
            product_id=product.id,
            customer_id=customer.id,
            quantity_sold=quantity_sold,
            selling_price_per_item=selling_price_per_item,
            selling_total_price=selling_total_price,
            sale_date=sale_date
        )
        db_session.add(sale_history)
        db_session.commit()

        return jsonify({'message': 'Sale recorded successfully'}), 201
    except NoResultFound:
        return jsonify({'error': 'Product or Customer not found'}), 404
    except KeyError as e:
        return jsonify({'error': f'Missing field: {str(e)}'}), 400


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
