from datetime import datetime

from flask import Flask, jsonify, request
from peewee import SqliteDatabase
from playhouse.shortcuts import model_to_dict
from models import Product, StockHistory, PurchaseHistory, SaleHistory, \
    Category, ProductCategory  # Імпортуємо модель Product з файлу models.py

from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Підключаємо базу даних
db = SqliteDatabase('shop_crm.db')


@app.route('/api/products', methods=['GET'])
def get_products():
    """Отримати всі товари"""
    products = Product.select()
    product_list = [model_to_dict(product) for product in products]
    return jsonify(product_list), 200


@app.route('/api/product', methods=['POST'])
def create_product():
    """Створити новий товар"""
    data = request.get_json()

    # Створюємо товар
    product = Product.create(
        name=data['name'],
        supplier=data['supplier'],
        quantity=data['quantity'],
        total_price=data['total_price'],
        price_per_item=data['price_per_item']
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
    """Оновити товар"""
    data = request.get_json()
    try:
        product = Product.get(Product.id == product_id)
        change_amount = data['quantity'] - product.quantity
        product.quantity = data['quantity']
        product.total_price = data['total_price']
        product.price_per_item = data['price_per_item']
        product.save()

        # Додаємо запис в історію
        if change_amount != 0:
            change_type = 'add' if change_amount > 0 else 'subtract'
            StockHistory.create(
                product=product,
                change_amount=abs(change_amount),
                change_type=change_type
            )
        return jsonify(model_to_dict(product)), 200
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404


@app.route('/api/product/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Видалити товар"""
    try:
        product = Product.get(Product.id == product_id)
        product.delete_instance()
        return jsonify({'message': 'Product deleted successfully'}), 200
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404


@app.route('/api/product/<int:product_id>/history', methods=['GET'])
def get_product_history(product_id):
    """Отримати історію змін запасів, покупок і продажів для товару"""
    try:
        product = Product.get(Product.id == product_id)

        # Отримання історії змін запасів
        stock_history = StockHistory.select().where(StockHistory.product == product)
        stock_history_list = [model_to_dict(record) for record in stock_history]

        # Отримання історії покупок
        purchase_history = PurchaseHistory.select().where(PurchaseHistory.product == product)
        purchase_history_list = [model_to_dict(purchase) for purchase in purchase_history]

        # Отримання історії продажів
        sale_history = SaleHistory.select().where(SaleHistory.product == product)
        sale_history_list = [model_to_dict(sale) for sale in sale_history]

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
        price_per_item = data['price_per_item']
        total_price = data['total_price']
        supplier = data['supplier']
        purchase_date = data.get('purchase_date')  # Можна вказати значення за замовчуванням

        # Створення нового запису в історії
        PurchaseHistory.create(
            product=product,
            price_per_item=price_per_item,
            total_price=total_price,
            supplier=supplier,
            purchase_date=purchase_date
        )
    except KeyError as e:
        return jsonify({'error': f'Missing field: {str(e)}'}), 400

    # Повертаємо відповідь
    return jsonify({'message': 'Purchase recorded successfully'}), 201


@app.route('/api/product/<int:product_id>/sale', methods=['POST'])
def record_sale(product_id):
    """Записати продаж товару і додати в історію продажів"""
    try:
        product = Product.get(Product.id == product_id)
        data = request.get_json()

        # Створення нового запису продажу
        SaleHistory.create(
            product=product,
            customer=data['customer'],
            quantity_sold=data['quantity'],
            price_per_item=data['price_per_item'],
            total_price=data['total_price'],
            sale_date=data.get('sale_date', datetime.now())  # Якщо немає дати, використати поточну
        )

        return jsonify({'message': 'Sale recorded successfully'}), 201

    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404


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


if __name__ == '__main__':
    app.run(debug=True)
