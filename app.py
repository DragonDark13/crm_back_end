import subprocess
import logging

from flask import Flask, jsonify, request
from flask_login import login_user, login_required, logout_user
from flask_login import LoginManager
from flask_security import PeeweeUserDatastore, Security
from peewee import SqliteDatabase

from method import verify_product_sale_history

from flask_cors import CORS

from models import User, Role, UserRoles
from services.category_routes import category_bp
from services.customer_routes import customer_bp
from services.product_service import ProductService, product_bp, product_history_bp
from services.supplier_routes import supplier_bp

# INCLUDE FROM blueprint


app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret'
app.config['SECURITY_PASSWORD_SALT'] = 'some_salt'
CORS(app)

# Підключаємо базу даних
db = SqliteDatabase('shop_crm.db')

# Налаштування Flask-Security-Too
user_datastore = PeeweeUserDatastore(db, User, Role, UserRoles)
security = Security()

verify_product_sale_history()

# Ініціалізація LoginManager
login_manager = LoginManager()
login_manager.init_app(app)

# Опціонально: налаштуйте сторінку входу
login_manager.login_view = 'login'  # Назва вашої функції, яка обробляє логін


@login_manager.user_loader
def load_user(user_id):
    return User.get_or_none(User.id == user_id)  # Припускаємо, що у вас є модель `User` із полем `id`


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


@app.route('/update_server', methods=['POST'])
def webhook():
    if request.method == 'POST':
        logging.info('Отримано POST-запит на /update_server')
        try:
            subprocess.run(['git', 'fetch', 'origin'], cwd='/home/aleksandrForUpwork/crm_back_end')
            subprocess.run(['git', 'pull', 'origin', 'main'], cwd='/home/aleksandrForUpwork/crm_back_end',
                           capture_output=True, text=True)

            return 'Updated PythonAnywhere successfully', 200
        except Exception as e:
            return 'Internal Server Error', 500
    else:
        return 'Method Not Allowed', 405


# Функція для створення стандартних ролей та користувачів
def create_roles_and_users():
    db.create_tables([Role, User, UserRoles], safe=True)

    # Create standard roles
    guest_role, _ = Role.get_or_create(name='guest', description='Read-only access')
    manager_role, _ = Role.get_or_create(name='manager', description='Full access to manage resources')

    # Create standard users
    if not User.select().where(User.username == 'guest').exists():
        guest_user = User(username='guest', email='guest@example.com')
        guest_user.set_password('guestpassword')  # Хешуємо пароль
        guest_user.save()  # Зберігаємо користувача в базу
        UserRoles.create(user=guest_user, role=guest_role)

    if not User.select().where(User.username == 'manager').exists():
        manager_user = User(username='manager', email='manager@example.com')
        manager_user.set_password('managerpassword')  # Хешуємо пароль
        manager_user.save()  # Зберігаємо користувача в базу
        UserRoles.create(user=manager_user, role=manager_role)


# Виклик функції створення ролей та користувачів під час запуску програми
with app.app_context():
    create_roles_and_users()


# Login route
@app.route('/api/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')

    user = User.get_by_username(username)  # Викликаємо метод `get_by_username`

    if user and user.verify_password(password):  # Перевірка пароля
        login_user(user)
        return jsonify(message="Login successful"), 200

    return jsonify(message="Invalid credentials"), 401


# Logout route
@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify(message="Logout successful"), 200


if __name__ == '__main__':
    app.run(debug=True)
