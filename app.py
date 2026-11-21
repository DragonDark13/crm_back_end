import subprocess
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, get_jwt, get_jwt_identity, jwt_required, verify_jwt_in_request
from flask_login import LoginManager
import uuid
import logging
import hmac
import threading
import time

from flask_cors import CORS
from sqlalchemy import case
from sqlalchemy.dialects.postgresql import insert as postgresql_insert

from api.categories_api import categories_ns
from api.customer_api import customers_ns
from api.investment_api import investments_ns
from api.packaging_routes import packaging_ns
from api.supplier_routes import supplier_ns
from models import db, RevokedToken, User, Role, LoginAttempt, LoginIPAttempt
from services.category_routes import category_bp
from services.customer_routes import customer_bp
from services.export_to_excel_services import export_to_excel_bp
from services.financial_journal_services import financial_journal_bp
from services.gift_box_services import gift_box_services_bp
from services.other_investments_services import investments_bp
from services.package_services import package_bp
from services.product_service import ProductService, product_bp, product_history_bp
from services.purchase_history_bp import purchase_history_bp
from services.sales_history_services import sales_history_services_bp
from services.statistics_services import statistics_services_bp
from services.supplier_routes import supplier_bp

from flask_restx import Api, Resource
from api.products_api import products_ns

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
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,https://aleksandrforupwork.pythonanywhere.com"
    ).split(",")
    if origin.strip()
]
CORS(app, resources={r"/api/*": {"origins": allowed_origins}})
api = Api(
    app,
    title="CRM API",
    version="1.0",
    description="Документація CRM API"
)


# Configure database and application secrets from the environment.
database_url = os.getenv('DATABASE_URL')
if not database_url:
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    if not all([db_name, db_user, db_password]):
        raise RuntimeError(
            'DATABASE_URL or DB_NAME, DB_USER and DB_PASSWORD environment variables are required'
        )
    from urllib.parse import quote_plus
    database_url = (
        f"postgresql://{quote_plus(db_user)}:{quote_plus(db_password)}"
        f"@{db_host}:{db_port}/{db_name}"
    )

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise RuntimeError('SECRET_KEY environment variable is required')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY') or app.config['SECRET_KEY']
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

# Initialize extensions
db.init_app(app)
jwt = JWTManager(app)


@jwt.token_in_blocklist_loader
def is_token_revoked(jwt_header, jwt_payload):
    token_jti = jwt_payload.get("jti")
    if not token_jti:
        return True
    return db.session.query(RevokedToken.id).filter_by(jti=token_jti).scalar() is not None


@jwt.unauthorized_loader
def custom_unauthorized_response(err):
    print(f"Unauthorized: {err}")
    return jsonify(msg="Missing or invalid token"), 401


@jwt.invalid_token_loader
def custom_invalid_token_response(err):
    print(f"Invalid token: {err}")
    return jsonify(msg="Invalid token"), 422


@jwt.expired_token_loader
def custom_expired_token_response(jwt_header, jwt_payload):
    print("Token expired")
    return jsonify(msg="Token has expired"), 401


login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/api/me', methods=['GET'])
@jwt_required()
def current_user_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or not user.active:
        return jsonify(message="User is inactive or does not exist"), 401
    return jsonify(id=user.id, username=user.username, roles=sorted(role.name for role in user.roles)), 200


@app.before_request
def enforce_api_authorization():
    if not request.path.startswith('/api/'):
        return None

    if request.method == 'OPTIONS' or request.path in {
        '/api/login',
        '/api/me',
        '/api/logout',
    }:
        return None

    verify_jwt_in_request()
    user = User.query.get(get_jwt_identity())

    if not user or not user.active:
        return jsonify(message="User is inactive or does not exist"), 401

    role_names = {role.name for role in user.roles}
    if 'manager' in role_names:
        if request.path.startswith('/api/delete_all_') or request.path.startswith('/api/delete-history/'):
            return jsonify(message="Administrator role required"), 403
        return None

    is_catalog_read = (
        request.method == 'GET'
        and (
            request.path.rstrip('/') == '/api/get_all_products'
            or (request.path.startswith('/api/product/') and len(request.path.strip('/').split('/')) == 3)
            or request.path == '/api/categories/get_all_categories'
            or request.path == '/api/suppliers/get_suppliers_list'
        )
    )
    if 'guest' in role_names and is_catalog_read:
        return None

    return jsonify(message="Insufficient permissions"), 403


JWT_BLOCKLIST_CLEANUP_INTERVAL_SECONDS = max(
    60,
    int(os.getenv("JWT_BLOCKLIST_CLEANUP_INTERVAL_SECONDS", "86400"))
)
_revoked_token_cleanup_lock = threading.Lock()
_revoked_token_last_cleanup = 0.0


def cleanup_expired_revoked_tokens():
    now = datetime.now(timezone.utc)
    deleted_count = db.session.query(RevokedToken).filter(
        RevokedToken.expires_at <= now
    ).delete(synchronize_session=False)
    db.session.commit()
    return deleted_count


@app.before_request
def cleanup_expired_revoked_tokens_periodically():
    global _revoked_token_last_cleanup

    if not request.path.startswith('/api/'):
        return None

    now_monotonic = time.monotonic()
    if now_monotonic - _revoked_token_last_cleanup < JWT_BLOCKLIST_CLEANUP_INTERVAL_SECONDS:
        return None

    if not _revoked_token_cleanup_lock.acquire(blocking=False):
        return None

    try:
        now_monotonic = time.monotonic()
        if now_monotonic - _revoked_token_last_cleanup >= JWT_BLOCKLIST_CLEANUP_INTERVAL_SECONDS:
            _revoked_token_last_cleanup = now_monotonic
            try:
                deleted_count = cleanup_expired_revoked_tokens()
                if deleted_count:
                    logger.info("Removed %s expired JWT revocation entries", deleted_count)
            except Exception:
                db.session.rollback()
                logger.exception("Failed to clean expired JWT revocation entries")
    finally:
        _revoked_token_cleanup_lock.release()

    return None


@app.route('/api/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200





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
app.register_blueprint(product_bp, url_prefix='/api')
app.register_blueprint(product_history_bp, url_prefix='/api')
app.register_blueprint(category_bp, url_prefix='/api')
app.register_blueprint(supplier_bp, url_prefix='/api')
app.register_blueprint(customer_bp, url_prefix='/api')
app.register_blueprint(package_bp, url_prefix='/api')
app.register_blueprint(investments_bp, url_prefix='/api')
app.register_blueprint(purchase_history_bp, url_prefix='/api')
app.register_blueprint(export_to_excel_bp, url_prefix='/api')
app.register_blueprint(financial_journal_bp, url_prefix='/api')
app.register_blueprint(sales_history_services_bp, url_prefix='/api')
app.register_blueprint(gift_box_services_bp, url_prefix='/api')
app.register_blueprint(statistics_services_bp,url_prefix='/api/statistics')

@app.route('/update_server', methods=['POST'])
def webhook():
    webhook_secret = os.getenv('WEBHOOK_SECRET')
    if not webhook_secret:
        return 'Webhook is disabled', 503
    if not hmac.compare_digest(request.headers.get('X-Webhook-Secret', ''), webhook_secret):
        return 'Unauthorized', 401
    logging.info('Authorized POST request received on /update_server')
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

        # --- ROLES ---
        guest_role = Role.query.filter_by(name="guest").first()
        if not guest_role:
            guest_role = Role(name="guest", description="Read-only access")
            db.session.add(guest_role)

        manager_role = Role.query.filter_by(name="manager").first()
        if not manager_role:
            manager_role = Role(name="manager", description="Full access")
            db.session.add(manager_role)

        db.session.flush()  # ролі вже в сесії, але без commit

        # --- USERS ---
        guest_password = os.getenv("GUEST_PASSWORD")
        if not User.query.filter_by(email="guest@example.com").first():
            if guest_password:
                guest_user = User()
                guest_user.username = "guest_user"
                guest_user.email = "guest@example.com"
                guest_user.active = 1
                guest_user.fs_uniquifier = str(uuid.uuid4())
                guest_user.set_password(guest_password)
                guest_user.roles.append(guest_role)
                db.session.add(guest_user)
            else:
                logger.warning("GUEST_PASSWORD is not configured; default guest user was not created.")

        manager_password = os.getenv("MANAGER_PASSWORD")
        if not User.query.filter_by(email="manager@example.com").first():
            if manager_password:
                manager_user = User(
                    username="manager",
                    email="manager@example.com",
                    fs_uniquifier=str(uuid.uuid4()),
                    active=1,
                )
                manager_user.set_password(manager_password)
                manager_user.roles.append(manager_role)
                db.session.add(manager_user)
            else:
                logger.warning("MANAGER_PASSWORD is not configured; default manager user was not created.")

        # --- ONE COMMIT ---
        db.session.commit()


# Initialize database with roles and users
with app.app_context():
    create_roles_and_users()


LOGIN_WINDOW = timedelta(minutes=15)
LOGIN_LOCKOUT = timedelta(minutes=15)
LOGIN_USERNAME_MAX_ATTEMPTS = int(os.getenv("LOGIN_USERNAME_MAX_ATTEMPTS", "5"))
LOGIN_IP_MAX_ATTEMPTS = int(os.getenv("LOGIN_IP_MAX_ATTEMPTS", "30"))
LOGIN_ACCOUNT_MAX_ATTEMPTS = int(os.getenv("LOGIN_ACCOUNT_MAX_ATTEMPTS", "20"))
LOGIN_ACCOUNT_IP_KEY = "__all_ips__"


def _is_login_locked(attempt, now):
    locked_until = attempt.locked_until if attempt else None
    if locked_until and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    return bool(locked_until and locked_until > now)


def _increment_login_counter(model, key_values, now, max_attempts):
    table = model.__table__

    if db.engine.dialect.name == "postgresql":
        window_expired = table.c.window_started_at <= now - LOGIN_WINDOW
        next_attempts = case((window_expired, 1), else_=table.c.attempts + 1)
        statement = postgresql_insert(table).values(
            **key_values,
            attempts=1,
            window_started_at=now,
            locked_until=None
        )

        conflict_columns = (
            [table.c.username, table.c.ip_address]
            if model is LoginAttempt else [table.c.ip_address]
        )
        statement = statement.on_conflict_do_update(
            index_elements=conflict_columns,
            set_={
                "attempts": next_attempts,
                "window_started_at": case(
                    (window_expired, now),
                    else_=table.c.window_started_at
                ),
                "locked_until": case(
                    (window_expired, None),
                    (next_attempts >= max_attempts, now + LOGIN_LOCKOUT),
                    else_=table.c.locked_until
                )
            }
        )
        db.session.execute(statement)
        return

    # Portable fallback for SQLite-based tests and local development.
    attempt = model.query.filter_by(**key_values).with_for_update().first()
    if attempt is None:
        attempt = model(**key_values, attempts=1, window_started_at=now)
    else:
        window_started_at = attempt.window_started_at
        if window_started_at.tzinfo is None:
            window_started_at = window_started_at.replace(tzinfo=timezone.utc)
        if window_started_at <= now - LOGIN_WINDOW:
            attempt.attempts = 1
            attempt.window_started_at = now
            attempt.locked_until = None
        else:
            attempt.attempts += 1
    if attempt.attempts >= max_attempts:
        attempt.locked_until = now + LOGIN_LOCKOUT
    db.session.add(attempt)


@app.route('/api/login', methods=['POST'])
def login():
    credentials = request.get_json(silent=True) or {}
    username = credentials.get('username')
    password = credentials.get('password')

    if not isinstance(username, str) or not username.strip() or not isinstance(password, str) or not password:
        return jsonify(message="Invalid credentials"), 401

    normalized_username = username.strip()
    client_ip = request.remote_addr or "unknown"
    now = datetime.now(timezone.utc)

    username_attempt = LoginAttempt.query.filter_by(
        username=normalized_username,
        ip_address=client_ip
    ).first()
    ip_attempt = LoginIPAttempt.query.filter_by(ip_address=client_ip).first()
    account_attempt = LoginAttempt.query.filter_by(
        username=normalized_username,
        ip_address=LOGIN_ACCOUNT_IP_KEY
    ).first()

    if (
        _is_login_locked(username_attempt, now)
        or _is_login_locked(ip_attempt, now)
        or _is_login_locked(account_attempt, now)
    ):
        return jsonify(message="Too many failed login attempts. Try again later."), 429

    user = User.query.filter_by(username=normalized_username).first()
    if user and user.active and user.verify_password(password):
        if username_attempt:
            db.session.delete(username_attempt)
        if account_attempt:
            db.session.delete(account_attempt)
        db.session.commit()
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                "username": user.username,
                "roles": sorted(role.name for role in user.roles)
            }
        )
        return jsonify(message="Login successful", token=access_token), 200

    _increment_login_counter(
        LoginAttempt,
        {"username": normalized_username, "ip_address": client_ip},
        now,
        LOGIN_USERNAME_MAX_ATTEMPTS
    )
    _increment_login_counter(
        LoginIPAttempt,
        {"ip_address": client_ip},
        now,
        LOGIN_IP_MAX_ATTEMPTS
    )
    _increment_login_counter(
        LoginAttempt,
        {"username": normalized_username, "ip_address": LOGIN_ACCOUNT_IP_KEY},
        now,
        LOGIN_ACCOUNT_MAX_ATTEMPTS
    )
    db.session.commit()
    return jsonify(message="Invalid credentials"), 401


@app.route('/api/logout', methods=['POST'])
@jwt_required()
def logout():
    token_data = get_jwt()
    revoked_token = RevokedToken(
        jti=token_data["jti"],
        token_type=token_data.get("type", "access"),
        user_identity=str(get_jwt_identity()),
        revoked_at=datetime.now(timezone.utc),
        expires_at=datetime.fromtimestamp(token_data["exp"], tz=timezone.utc),
    )
    db.session.add(revoked_token)
    db.session.commit()
    return jsonify(message="Logout successful"), 200


@app.before_request
def log_request_info():
    # Never log request bodies or query strings: they may contain credentials or personal data.
    logger.info("Request method: %s, path: %s", request.method, request.path)



api.add_namespace(products_ns, path="/api/get_all_products")
api.add_namespace(supplier_ns, path="/api/suppliers")
api.add_namespace(categories_ns, path="/api/categories")
api.add_namespace(investments_ns, path="/api/investments")
api.add_namespace(customers_ns, path="/api/customers")
api.add_namespace(packaging_ns, path="/api/packaging")


if __name__ == '__main__':
    app.run(debug=True)
