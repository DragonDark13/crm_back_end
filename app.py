from flask import Flask, jsonify, request
from peewee import SqliteDatabase
from playhouse.shortcuts import model_to_dict
from models import Product, StockHistory  # Імпортуємо модель Product з файлу models.py

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
def get_stock_history(product_id):
    """Отримати історію змін для товару"""
    try:
        product = Product.get(Product.id == product_id)
        history = StockHistory.select().where(StockHistory.product == product)
        history_list = [model_to_dict(record) for record in history]
        return jsonify(history_list), 200
    except Product.DoesNotExist:
        return jsonify({'error': 'Product not found'}), 404


if __name__ == '__main__':
    app.run(debug=True)
