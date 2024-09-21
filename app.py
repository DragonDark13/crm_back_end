from datetime import datetime

from flask import Flask, jsonify, request
from peewee import SqliteDatabase
from playhouse.shortcuts import model_to_dict
from models import Product, StockHistory, PurchaseHistory, SaleHistory  # Імпортуємо модель Product з файлу models.py

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
    product = Product.create(
        name=data['name'],
        supplier=data['supplier'],
        quantity=data['quantity'],
        total_price=data['total_price'],
        price_per_item=data['price_per_item']
    )
    return jsonify(model_to_dict(product)), 201


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




if __name__ == '__main__':
    app.run(debug=True)
