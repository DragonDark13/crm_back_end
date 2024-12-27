from models import Product, product_categories_table, Supplier, PurchaseHistory, StockHistory, Category, SaleHistory, \
    Customer
from flask import jsonify, Blueprint, request
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import NoResultFound
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import sessionmaker

# Створюємо Blueprint для продуктів
product_bp = Blueprint('products', __name__)
from database import db_session  # Assuming `db_session` is the SQLAlchemy session


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
            product = Product(
                name=data['name'],
                quantity=0,
                created_date=data.get('created_date')
            )

            # Додаємо категорії
            category_ids = data.get('category_ids', [])
            if category_ids:
                ProductService.assign_categories_to_product(product, category_ids)

            supplier = db_session.query(Supplier).filter(Supplier.id == data['supplier_id']).one()
            product.supplier = supplier

            product.purchase_total_price = Decimal(data['purchase_total_price'])
            product.purchase_price_per_item = Decimal(data['purchase_price_per_item'])
            product.quantity = data['quantity']
            product.selling_price_per_item = Decimal(data.get('selling_price_per_item', 0))

            # Add to session and commit
            db_session.add(product)
            db_session.commit()

            # Створення записів в історії
            purchase_history = PurchaseHistory(
                product_id=product.id,
                purchase_price_per_item=Decimal(data['purchase_price_per_item']),
                purchase_total_price=Decimal(data['purchase_total_price']),
                supplier_id=supplier.id,
                quantity_purchase=data['quantity'],
                purchase_date=data.get('purchase_date')
            )
            db_session.add(purchase_history)

            stock_history = StockHistory(
                product_id=product.id,
                change_amount=data['quantity'],
                change_type='create',
                timestamp=data.get('purchase_date')
            )
            db_session.add(stock_history)

            db_session.commit()

            return product.to_dict(), 201
        except NoResultFound:
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
        categories = db_session.query(Category).filter(Category.id.in_(category_ids)).all()
        for category in categories:
            product_category = product_categories_table(product_id=product.id, category_id=category.id)
            db_session.add(product_category)


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
        product = db_session.query(Product).filter(Product.id == product_id).one()

        supplier_id = data.get('supplier_id')
        if supplier_id:
            try:
                supplier = db_session.query(Supplier).filter(Supplier.id == supplier_id).one()
                product.supplier = supplier
            except NoResultFound:
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
            # Clear old categories first
            db_session.query(product_categories_table).filter(
                product_categories_table.product_id == product.id).delete()

            categories = db_session.query(Category).filter(Category.id.in_(category_ids)).all()
            for category in categories:
                product_category = product_categories_table(product_id=product.id, category_id=category.id)
                db_session.add(product_category)

        db_session.commit()

        stock_history_record = db_session.query(StockHistory).filter(
            StockHistory.product_id == product.id,
            StockHistory.change_type == 'create'
        ).first()

        if stock_history_record:
            stock_history_record.timestamp = created_date if created_date else datetime.now()
            stock_history_record.change_amount = quantity
            db_session.commit()

        else:
            stock_history = StockHistory(
                product_id=product.id,
                change_amount=quantity,
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
        product = db_session.query(Product).filter(Product.id == product_id).one()

        # Delete related records
        db_session.query(product_categories_table).filter(product_categories_table.product_id == product.id).delete()
        db_session.query(SaleHistory).filter(SaleHistory.product_id == product.id).delete()
        db_session.query(PurchaseHistory).filter(PurchaseHistory.product_id == product.id).delete()
        db_session.query(StockHistory).filter(StockHistory.product_id == product.id).delete()

        # Delete the product
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

        # Sale History
        sale_history = db_session.query(SaleHistory).filter(SaleHistory.product_id == product.id).all()
        sale_history_list = [
            {
                **record.to_dict(),
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


from flask import jsonify
from decimal import Decimal
from datetime import datetime


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
        purchase_date = data.get('purchase_date', datetime.now())

        if supplier_id:
            supplier = db_session.query(Supplier).filter(Supplier.id == supplier_id).one_or_none()
            if supplier is None:
                return jsonify({'error': 'Supplier not found'}), 404
            product.supplier = supplier

        product.quantity += quantity
        product.purchase_total_price += purchase_total_price
        product.purchase_price_per_item = product.purchase_total_price / product.quantity
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

        if product.quantity < quantity_sold:
            return jsonify({'error': 'Not enough quantity in stock'}), 400

        product.quantity -= quantity_sold
        product.selling_quantity += quantity_sold
        product.selling_price_per_item = selling_price_per_item
        product.selling_total_price += selling_total_price
        db_session.commit()

        customer = db_session.query(Customer).filter(Customer.id == data['customer']).one()

        sale_history = SaleHistory(
            product_id=product.id,
            customer_id=customer.id,
            quantity_sold=quantity_sold,
            selling_price_per_item=selling_price_per_item,
            selling_total_price=selling_total_price,
            sale_date=data.get('sale_date', datetime.now())
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
