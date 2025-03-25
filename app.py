import subprocess
import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_login import LoginManager
import uuid
import logging

from flask_cors import CORS

from models import db, User, Role
from services.category_routes import category_bp
from services.customer_routes import customer_bp
from services.export_to_excel_services import export_to_excel_bp
from services.gift_box_services import gift_box_services_bp
from services.other_investments_services import investments_bp
from services.package_services import package_bp
from services.product_service import ProductService, product_bp, product_history_bp
from services.purchase_history_bp import purchase_history_bp
from services.sales_history_services import sales_history_services_bp
from services.supplier_routes import supplier_bp

# Load environment variables
load_dotenv()

# Logger setup
logger = logging.getLogger("app_logger")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("app.log")
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Flask app initialization
app = Flask(__name__)
CORS(app)

# Configure database (PostgreSQL)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL','postgresql://postgres:admin@localhost:5432/shop_crm_post')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# JWT Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

# Initialize extensions
db.init_app(app)
jwt = JWTManager(app)
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/api/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200


@app.route('/api/products', methods=['GET'])
def get_products():
    product_list, status_code = ProductService.get_all_products()
    return jsonify(product_list), status_code


@app.route('/api/product/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product_data, status_code = ProductService.get_product_by_id(product_id)
    return jsonify(product_data), status_code


@app.route('/api/add_new_product', methods=['POST'])
def create_and_purchase_product():
    data = request.get_json()
    result, status_code = ProductService.create_product(data)
    return jsonify(result), status_code


# Register Blueprints
app.register_blueprint(product_bp)
app.register_blueprint(product_history_bp)
app.register_blueprint(category_bp)
app.register_blueprint(supplier_bp)
app.register_blueprint(customer_bp)
app.register_blueprint(package_bp)
app.register_blueprint(investments_bp)
app.register_blueprint(purchase_history_bp)
app.register_blueprint(export_to_excel_bp)
app.register_blueprint(sales_history_services_bp)
app.register_blueprint(gift_box_services_bp)


@app.route('/update_server', methods=['POST'])
def webhook():
    logging.info('POST request received on /update_server')
    try:
        subprocess.run(['git', 'fetch', 'origin'], cwd='/home/aleksandrForUpwork/crm_back_end')
        subprocess.run(['git', 'pull', 'origin', 'main'], cwd='/home/aleksandrForUpwork/crm_back_end',
                       capture_output=True, text=True)
        return 'Updated PythonAnywhere successfully', 200
    except Exception as e:
        return 'Internal Server Error', 500


# Function to create standard roles and users
def create_roles_and_users():
    with app.app_context():
        db.create_all()
        guest_role = Role.query.filter_by(name='guest').first()
        if not guest_role:
            guest_role = Role(name='guest', description='Read-only access')
            db.session.add(guest_role)
            db.session.commit()
        manager_role = Role.query.filter_by(name='manager').first()
        if not manager_role:
            manager_role = Role(name='manager', description='Full access')
            db.session.add(manager_role)
            db.session.commit()
        if not User.query.filter_by(username='guest').first():
            guest_user = User(username='guest', email='guest@example.com')
            guest_user.set_password('guestpassword')
            guest_user.fs_uniquifier = str(uuid.uuid4())
            db.session.add(guest_user)
            guest_user.roles.append(guest_role)
            db.session.commit()
        if not User.query.filter_by(username='manager').first():
            manager_user = User(username='manager', email='manager@example.com')
            manager_user.set_password('managerpassword')
            manager_user.fs_uniquifier = str(uuid.uuid4())
            db.session.add(manager_user)
            manager_user.roles.append(manager_role)
            db.session.commit()


# Initialize database with roles and users
with app.app_context():
    create_roles_and_users()


@app.route('/api/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    user = User.query.filter_by(username=username).first()
    if user and user.verify_password(password):
        access_token = create_access_token(identity={'username': user.username, 'id': user.id})
        return jsonify(message="Login successful", token=access_token), 200
    return jsonify(message="Invalid credentials"), 401


@app.route('/api/logout', methods=['POST'])
@jwt_required()
def logout():
    current_user = get_jwt_identity()  # Це повинно повернути правильний ідентифікатор користувача
    if not isinstance(current_user, str):
        raise Exception("Subject must be a string")
    print(f"User {current_user} logged out")
    return jsonify(message="Logout successful"), 200


@app.before_request
def log_request_info():
    logger.info(f"Request method: {request.method}, URL: {request.url}")
    if request.method in ["POST", "PUT", "PATCH"]:
        logger.info(f"Body: {request.get_data(as_text=True)}")


if __name__ == '__main__':
    app.run(debug=True)
