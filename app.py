from datetime import datetime
from decimal import Decimal

from flask import Flask, jsonify, request
from peewee import SqliteDatabase
from playhouse.shortcuts import model_to_dict
from models import Product, StockHistory, PurchaseHistory, SaleHistory, \
    Category, ProductCategory, Supplier  # Імпортуємо модель Product з файлу models.py

from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Підключаємо базу даних
db = SqliteDatabase('shop_crm.db')


@app.route('/api/products', methods=['GET'])
def get_products():
    """Отримати всі товари разом з категоріями"""
    products = Product.select()
    product_list = []

    for product in products:
        # Перетворюємо продукт в словник і додаємо категорії
        product_dict = model_to_dict(product, exclude=[ProductCategory])

        # Переконайтесь, що total_price і price_per_item у форматі чисел
        product_dict['total_price'] = float(product.total_price)
        product_dict['price_per_item'] = float(product.price_per_item)

        # Отримуємо категорії продукту
        product_dict['category_ids'] = [pc.category.id for pc in product.categories]

        # Додаємо постачальника продукту (якщо він є)
        if product.supplier:
            product_dict['supplier'] = {
                'id': product.supplier.id,
                'name': product.supplier.name,
                'contact_info': product.supplier.contact_info
            }
        else:
            product_dict['supplier'] = None  # Якщо постачальника немає

        product_list.append(product_dict)

    return jsonify(product_list), 200


@app.route('/api/product', methods=['POST'])
def create_product():
    """Створити новий товар з валідацією"""
    data = request.get_json()

    # Перевірка наявності обов'язкових полів
    required_fields = ['name', 'supplier_id', 'quantity', 'price_per_item']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f"Missing required fields: {', '.join(missing_fields)}"}), 400

    # Валідація полів
    errors = {}

    # Перевірка, що поля 'name' та 'supplier' не пусті
    if not data['name'].strip():
        errors['name'] = "Name is required."

    # Перевірка, що 'quantity' та 'price_per_item' є числами більше або рівними 0
    try:
        quantity = float(data['quantity'])
        if quantity < 0:
            errors['quantity'] = "Quantity must be greater than or equal to 0."
    except ValueError:
        errors['quantity'] = "Quantity must be a valid number."

    try:
        price_per_item = float(data['price_per_item'])
        if price_per_item < 0:
            errors['price_per_item'] = "Price per item must be greater than or equal to 0."
    except ValueError:
        errors['price_per_item'] = "Price per item must be a valid number."

    # Обчислення та перевірка total_price
    # expected_total_price = quantity * price_per_item
    total_price = data.get('total_price')

    # if total_price != expected_total_price:
    #     errors['total_price'] = f"Total price should be {expected_total_price}, but received {total_price}."

    # Якщо є помилки валідації, повертаємо їх
    if errors:
        return jsonify({'errors': errors}), 400

    # Створюємо товар
    product = Product.create(
        name=data['name'],
        supplier=data['supplier_id'],
        quantity=quantity,
        total_price=total_price,
        price_per_item=price_per_item
    )

    # Записуємо подію створення товару до історії запасів
    StockHistory.create(
        product=product,
        change_amount=quantity,
        change_type='create'  # Тип операції "додавання" при створенні товару
    )

    # Додаємо категорії до товару, якщо передано category_ids
    if 'category_ids' in data:
        category_ids = data['category_ids']
        for category_id in category_ids:
            category = Category.get_or_none(Category.id == category_id)
            if category:
                ProductCategory.create(product=product, category=category)

    return jsonify(model_to_dict(product, backrefs=True)), 201


@app.route('/api/product/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Отримати товар за ID"""
    try:
        product = Product.get(Product.id == product_id)
        return jsonify(model_to_dict(product)), 200
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404


@app.route('/api/product/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Оновити товар з валідацією і збереженням всіх змін"""
    data = request.get_json()

    # Перевірка обов'язкових полів
    required_fields = ['quantity', 'price_per_item', 'total_price']
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
        price_per_item = float(data['price_per_item'])
        if price_per_item < 0:
            errors['price_per_item'] = "Price per item must be greater than or equal to 0."
    except ValueError:
        errors['price_per_item'] = "Price per item must be a valid number."

    # expected_total_price = quantity * price_per_item
    total_price = data.get('total_price')

    # if total_price != expected_total_price:
    #     errors['total_price'] = f"Total price should be {expected_total_price}, but received {total_price}."

    # Якщо є помилки валідації, повертаємо їх
    if errors:
        return jsonify({'errors': errors}), 400

    try:
        # Перевіряємо, чи існує продукт
        product = Product.get(Product.id == product_id)

        # Оновлюємо постачальника, якщо він був переданий
        supplier_id = data.get('supplier_id')
        if supplier_id:
            try:
                supplier = Supplier.get(Supplier.id == supplier_id)
                product.supplier = supplier
            except Supplier.DoesNotExist:
                return jsonify({'error': 'Supplier not found'}), 404

        # Розрахунок зміни кількості
        change_amount = data['quantity'] - product.quantity

        # Оновлення полів продукту
        product.quantity = quantity
        product.total_price = total_price
        product.price_per_item = price_per_item

        # Оновлюємо категорії, якщо вони передані
        category_ids = data.get('category_ids', [])
        if category_ids:
            # Очищаємо попередні категорії та додаємо нові
            product.categories.clear()
            categories = Category.select().where(Category.id.in_(category_ids))
            product.categories.add(categories)

        product.save()

        # Запис змін в історію
        if change_amount != 0:
            change_type = 'add' if change_amount > 0 else 'subtract'
            StockHistory.create(
                product=product,
                change_amount=abs(change_amount),
                change_type=change_type
            )

        # Повертаємо оновлений продукт у вигляді JSON
        updated_product = model_to_dict(product, backrefs=True, exclude=[ProductCategory])
        return jsonify(updated_product), 200

    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404


@app.route('/api/product/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Видалити товар та всі пов'язані записи"""
    try:
        product = Product.get(Product.id == product_id)

        ProductCategory.delete().where(ProductCategory.product == product).execute()
        # Видалення всіх пов'язаних продажів
        SaleHistory.delete().where(SaleHistory.product == product).execute()

        # Видалення всіх пов'язаних покупок
        PurchaseHistory.delete().where(PurchaseHistory.product == product).execute()

        # Видалення всіх записів змін запасів
        StockHistory.delete().where(StockHistory.product == product).execute()

        # Видалення самого товару
        product.delete_instance()

        return jsonify({'message': 'Product and related records deleted successfully'}), 200
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404


@app.route('/api/product/<int:product_id>/history', methods=['GET'])
def get_product_history(product_id):
    """Отримати історію змін запасів, покупок і продажів для товару"""
    try:
        product = Product.get(Product.id == product_id)

        # Отримання історії змін запасів
        stock_history = StockHistory.select().where(StockHistory.product == product)
        stock_history_list = [
            {
                **model_to_dict(record),
                'timestamp': record.timestamp.strftime('%Y-%m-%d %H:%M:%S')  # Або інший бажаний формат
            }
            for record in stock_history
        ]

        # Отримання історії покупок
        purchase_history = PurchaseHistory.select().where(PurchaseHistory.product == product)
        purchase_history_list = [model_to_dict(purchase) for purchase in purchase_history]

        # Отримання історії продажів
        sale_history = SaleHistory.select().where(SaleHistory.product == product)
        sale_history_list = [
            {
                **model_to_dict(sale),
                'price_per_item': float(sale.price_per_item),  # Конвертація в число
                'total_price': float(sale.total_price)  # Конвертація в число
            }
            for sale in sale_history
        ]

        # Об'єднуємо всі списки в один об'єкт
        combined_history = {
            'stock_history': stock_history_list,
            'purchase_history': purchase_history_list,
            'sale_history': sale_history_list
        }

        return jsonify(combined_history), 200
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404


@app.route('/api/product/<int:product_id>/purchase', methods=['POST'])
def purchase_product(product_id):
    """Обробити покупку товару і записати в історію"""
    data = request.get_json()

    # Перевірка, чи продукт існує
    try:
        product = Product.get(Product.id == product_id)
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404

    # Валідація даних
    try:
        # Валідація кількості
        quantity = data['quantity']
        if quantity <= 0:
            return jsonify({'error': 'Quantity must be greater than 0'}), 400

        # Валідація ціни та інших полів
        price_per_item = Decimal(data['price_per_item'])  # Перетворення у Decimal
        total_price = Decimal(data['total_price'])  # Перетворення у Decimal
        supplier_id = data['supplier_id']
        purchase_date = data.get('purchase_date')  # Можна вказати значення за замовчуванням

        if supplier_id:
            try:
                supplier = Supplier.get(Supplier.id == supplier_id)
                product.supplier = supplier
            except Supplier.DoesNotExist:
                return jsonify({'error': 'Supplier not found'}), 404

        # Перевірка на від'ємні значення ціни
        if price_per_item <= 0 or total_price <= 0:
            return jsonify({'error': 'Price must be greater than 0'}), 400

        # Оновлення кількості товару в таблиці Product
        product.quantity += quantity
        product.total_price += total_price
        product.save()
        product.price_per_item = product.total_price / product.quantity
        product.save()
        # Створення нового запису в історії покупок
        PurchaseHistory.create(
            product=product,
            price_per_item=price_per_item,
            total_price=total_price,
            supplier=supplier.name,
            purchase_date=purchase_date,
            quantity_purchase=quantity
        )
    except KeyError as e:
        return jsonify({'error': f'Missing field: {str(e)}'}), 400

    # Повертаємо відповідь
    return jsonify({'message': 'Purchase recorded successfully'}), 201


@app.route('/api/product/<int:product_id>/sale', methods=['POST'])
def record_sale(product_id):
    """Записати продаж товару і додати в історію продажів"""
    try:
        # Перевірка, чи існує продукт
        product = Product.get(Product.id == product_id)
        data = request.get_json()

        # Валідація даних
        required_fields = ['customer', 'quantity', 'price_per_item', 'total_price']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing field: {field}'}), 400

        quantity_sold = data['quantity']
        if quantity_sold <= 0:
            return jsonify({'error': 'Quantity must be greater than 0'}), 400

        price_per_item = data['price_per_item']
        total_price = data['total_price']
        if price_per_item <= 0 or total_price <= 0:
            return jsonify({'error': 'Price per item and total price must be greater than 0'}), 400

        # Перевірка, чи є достатня кількість товару на складі
        if product.quantity < quantity_sold:
            return jsonify({'error': 'Not enough quantity in stock'}), 400

        # Оновлення кількості товару
        product.quantity -= quantity_sold
        product.total_price = product.quantity * product.price_per_item
        product.save()

        # Створення нового запису продажу в історії
        SaleHistory.create(
            product=product,
            customer=data['customer'],
            quantity_sold=quantity_sold,
            price_per_item=price_per_item,
            total_price=total_price,
            sale_date=data.get('sale_date', datetime.now())  # Якщо немає дати, використати поточну
        )

        return jsonify({'message': 'Sale recorded successfully'}), 201

    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404

    except KeyError as e:
        return jsonify({'error': f'Missing field: {str(e)}'}), 400


@app.route('/api/categories', methods=['GET'])
def get_all_categories():
    """Отримати список всіх категорій"""
    categories = Category.select()  # Отримуємо всі категорії
    category_list = [model_to_dict(category) for category in categories]  # Перетворюємо на список словників
    return jsonify(category_list), 200  # Повертаємо JSON відповідь


@app.route('/api/categories', methods=['POST'])
def create_category():
    """Створити нову категорію"""
    data = request.get_json()
    try:
        category, created = Category.get_or_create(name=data['name'])
        if created:
            return jsonify({'message': 'Category created successfully', 'category': model_to_dict(category)}), 201
        else:
            return jsonify({'message': 'Category already exists', 'category': model_to_dict(category)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/product/<int:product_id>/categories', methods=['POST'])
def assign_categories_to_product(product_id):
    """Прив'язати категорії до товару"""
    data = request.get_json()
    try:
        product = Product.get(Product.id == product_id)
        category_ids = data['category_ids']  # список ID категорій

        # Додаємо категорії до товару
        for category_id in category_ids:
            category = Category.get(Category.id == category_id)
            ProductCategory.get_or_create(product=product, category=category)

        return jsonify({'message': 'Categories assigned successfully'}), 200
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404
    except Category.DoesNotExist:
        return jsonify({'error': 'One or more categories not found'}), 404


@app.route('/api/product/<int:product_id>/categories', methods=['GET'])
def get_product_categories(product_id):
    """Отримати категорії товару"""
    try:
        product = Product.get(Product.id == product_id)
        categories = [model_to_dict(category) for category in product.categories]
        return jsonify(categories), 200
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404


@app.route('/api/supplier', methods=['POST'])
def create_supplier():
    """Додати нового постачальника"""
    data = request.get_json()

    # Перевірка наявності обов'язкового поля
    if 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400

    supplier, created = Supplier.get_or_create(name=data['name'], defaults={'contact_info': data.get('contact_info')})

    if created:
        return jsonify({'message': 'Supplier created successfully', 'supplier_id': supplier.id}), 201
    else:
        return jsonify({'error': 'Supplier already exists'}), 409


@app.route('/api/suppliers', methods=['GET'])
def get_suppliers():
    """Отримати список усіх постачальників"""
    suppliers = Supplier.select()
    suppliers_list = [model_to_dict(supplier) for supplier in suppliers]

    return jsonify(suppliers_list), 200


if __name__ == '__main__':
    app.run(debug=True)
