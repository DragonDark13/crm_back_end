import subprocess
from datetime import datetime
from decimal import Decimal
import logging


from flask import Flask, jsonify, request
from peewee import SqliteDatabase, fn, SQL, IntegrityError, DoesNotExist
from playhouse.shortcuts import model_to_dict

from method import verify_product_sale_history
from models import Product, StockHistory, PurchaseHistory, SaleHistory, \
    Category, ProductCategory, Supplier, User, Customer  # Імпортуємо модель Product з файлу models.py

from flask_cors import CORS

from services.category_routes import category_bp
from services.customer_routes import customer_bp
from services.product_service import ProductService, product_bp, product_history_bp
from services.supplier_routes import supplier_bp

app = Flask(__name__)
CORS(app)

# Підключаємо базу даних
db = SqliteDatabase('shop_crm.db')

# Виклик перевірки при запуску програми

verify_product_sale_history()


@app.route('/api/products', methods=['GET'])
def get_products():
    """Отримати всі товари з категоріями"""
    product_list, status_code = ProductService.get_all_products()
    return jsonify(product_list), status_code


@app.route('/api/product/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Отримати товар за ID"""
    product_data, status_code = ProductService.get_product_by_id(product_id)
    return jsonify(product_data), status_code


@app.route('/api/product', methods=['POST'])
def create_and_purchase_product():
    """Створити новий продукт і обробити закупку"""
    data = request.get_json()
    result, status_code = ProductService.create_product(data)
    return jsonify(result), status_code


# Реєструємо Blueprint для продуктів
app.register_blueprint(product_bp)

# Реєструємо Blueprint для історії продукту
app.register_blueprint(product_history_bp)

# Реєструємо Blueprint для категорій
app.register_blueprint(category_bp)

app.register_blueprint(supplier_bp)

app.register_blueprint(customer_bp)

logging.basicConfig(filename='/home/aleksandrForUpwork/crm_back_end/webhook.log', level=logging.INFO)


@app.route('/update_server', methods=['POST'])
def webhook():
    if request.method == 'POST':
        logging.info('Отримано POST-запит на /update_server')
        try:
            result = subprocess.run(['git', 'pull', 'origin', 'main'], cwd='/home/aleksandrForUpwork/crm_back_end', capture_output=True, text=True)
            logging.info(f'Результат git pull: {result.stdout}')
            return 'Updated PythonAnywhere successfully', 200
        except Exception as e:
            logging.error(f'Помилка під час виконання git pull: {e}')
            return 'Internal Server Error', 500
    else:
        logging.warning('Отримано некоректний метод запиту на /update_server')
        return 'Method Not Allowed', 405


if __name__ == '__main__':
    app.run(debug=True)
