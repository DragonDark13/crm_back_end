import subprocess
import logging

from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_login import login_user, login_required, logout_user
from flask_login import LoginManager
from flask_security import SQLAlchemyUserDatastore, Security
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import uuid

from method import verify_product_sale_history

from flask_cors import CORS

from models import db, User, Role
from services.category_routes import category_bp
from services.customer_routes import customer_bp
from services.product_service import ProductService, product_bp, product_history_bp
from services.supplier_routes import supplier_bp

# INCLUDE FROM blueprint


app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret'
app.config['SECURITY_PASSWORD_SALT'] = 'some_salt'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop_crm.db'  # Update the URI for SQLAlchemy
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable track modifications to save resources
CORS(app)

# Initialize the database
db.init_app(app)

# Initialize Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

# Verify product sale history (as defined in the provided method)
verify_product_sale_history()

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)

# Optional: set login view if needed
login_manager.login_view = 'login'

app.config['JWT_SECRET_KEY'] = 'your_secret_key'  # Set a secure secret key for JWT
jwt = JWTManager(app)

# Session setup
engine = create_engine('sqlite:///shop_crm.db', echo=True)
Session = sessionmaker(bind=engine)
db_session = scoped_session(Session)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)  # Use SQLAlchemy to get the user by ID


@app.route('/api/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()  # Get user info from the JWT
    return jsonify(logged_in_as=current_user), 200


@app.route('/api/products', methods=['GET'])
def get_products():
    """Get all products with categories"""
    product_list, status_code = ProductService.get_all_products()
    return jsonify(product_list), status_code


@app.route('/api/product/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Get product by ID"""
    product_data, status_code = ProductService.get_product_by_id(product_id)
    return jsonify(product_data), status_code


@app.route('/api/product', methods=['POST'])
def create_and_purchase_product():
    """Create a new product and process purchase"""
    data = request.get_json()
    result, status_code = ProductService.create_product(data)
    return jsonify(result), status_code


# Register Blueprints
app.register_blueprint(product_bp)
app.register_blueprint(product_history_bp)
app.register_blueprint(category_bp)
app.register_blueprint(supplier_bp)
app.register_blueprint(customer_bp)


@app.route('/update_server', methods=['POST'])
def webhook():
    if request.method == 'POST':
        logging.info('POST request received on /update_server')
        try:
            subprocess.run(['git', 'fetch', 'origin'], cwd='/home/aleksandrForUpwork/crm_back_end')
            subprocess.run(['git', 'pull', 'origin', 'main'], cwd='/home/aleksandrForUpwork/crm_back_end',
                           capture_output=True, text=True)

            return 'Updated PythonAnywhere successfully', 200
        except Exception as e:
            return 'Internal Server Error', 500
    else:
        return 'Method Not Allowed', 405


# Function to create standard roles and users
def create_roles_and_users():
    db.create_all()  # Creates tables in the database

    # Create standard roles
    guest_role = Role.query.filter_by(name='guest').first()
    if not guest_role:
        guest_role = Role(name='guest', description='Read-only access')
        db.session.add(guest_role)
        db.session.commit()

    manager_role = Role.query.filter_by(name='manager').first()
    if not manager_role:
        manager_role = Role(name='manager', description='Full access to manage resources')
        db.session.add(manager_role)
        db.session.commit()

    # Create standard users
    if not User.query.filter_by(username='guest').first():
        guest_user = User(username='guest', email='guest@example.com')
        guest_user.set_password('guestpassword')  # Hash password
        guest_user.fs_uniquifier = str(uuid.uuid4())  # Set fs_uniquifier to a unique UUID
        db.session.add(guest_user)
        db.session.commit()
        guest_user.roles.append(guest_role)
        db.session.commit()

    if not User.query.filter_by(username='manager').first():
        manager_user = User(username='manager', email='manager@example.com')
        manager_user.set_password('managerpassword')  # Hash password
        manager_user.fs_uniquifier = str(uuid.uuid4())  # Set fs_uniquifier to a unique UUID
        db.session.add(manager_user)
        db.session.commit()
        manager_user.roles.append(manager_role)
        db.session.commit()


# Call the function to create roles and users on app startup
with app.app_context():
    create_roles_and_users()


# Login route
@app.route('/api/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.verify_password(password):  # Verify password
        access_token = create_access_token(identity={'username': user.username, 'id': user.id})
        return jsonify(message="Login successful", token=access_token), 200

    return jsonify(message="Invalid credentials"), 401


# Logout route
@app.route('/api/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify(message="Logout successful"), 200


if __name__ == '__main__':
    app.run(debug=True)
