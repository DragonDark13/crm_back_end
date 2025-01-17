from flask import Blueprint, jsonify, request, abort
from flask_sqlalchemy.session import Session

from models import Customer, SaleHistory
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

# Create Blueprint for customers
customer_bp = Blueprint('customer', __name__)


# Create customer
@customer_bp.route('/api/customers', methods=['POST'])
def create_customer():
    from database import db_session  # Assuming `db_session` is the SQLAlchemy session

    data = request.get_json()
    required_fields = ['name']

    # Check for required fields
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

    # Check for unique name
    existing_customer = db_session.query(Customer).filter_by(name=data['name']).first()
    if existing_customer:
        return jsonify({'error': 'Customer with this name already exists'}), 400

    try:
        # Create a new customer
        customer = Customer(
            name=data['name'],
            contact_info=data.get('contact_info'),
            address=data.get('address'),
            email=data.get('email'),  # Email is no longer checked for uniqueness
            phone_number=data.get('phone_number')
        )
        db_session.add(customer)
        db_session.commit()
        return jsonify({'message': 'Customer created successfully', 'customer': customer.to_dict()}), 201
    except IntegrityError as e:
        db_session.rollback()
        return jsonify({'error': f'Failed to create customer: {str(e)}'}), 500
    except Exception as e:
        db_session.rollback()
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500


# Get all customers
@customer_bp.route('/api/get_all_customers', methods=['GET'])
def get_all_customers():
    from database import db_session  # Assuming `db_session` is the SQLAlchemy session

    customers = db_session.query(Customer).all()
    customer_list = [customer.to_dict() for customer in customers]
    return jsonify(customer_list), 200


# Get customer details by ID
@customer_bp.route('/api/customers_details/<int:customer_id>', methods=['GET'])
def get_customer_details(customer_id):
    from database import db_session  # Assuming `db_session` is the SQLAlchemy session

    try:
        customer = db_session.query(Customer).filter_by(id=customer_id).one()
        customer_data = customer.to_dict()

        # Get related sales for the customer
        sales = db_session.query(SaleHistory).filter_by(customer_id=customer_id).all()
        customer_data['sales'] = [sale.to_dict() for sale in sales]

        return jsonify(customer_data), 200
    except Exception as e:
        return jsonify({'error': f'Customer not found: {str(e)}'}), 404


@customer_bp.route('/update_customers/<int:customer_id>', methods=['PUT'])
def edit_customer(customer_id: int):
    customer_data = request.get_json()
    from database import db_session  # Assuming `db_session` is the SQLAlchemy session

    if not customer_data:
        abort(400, description="Invalid data provided")

    updated_customer = update_customer(db_session, customer_id, customer_data)

    if not updated_customer:
        abort(404, description="Customer not found")

    return jsonify(updated_customer.to_dict())


def update_customer(session: Session, customer_id: int, customer_data: dict):
    customer = session.query(Customer).get(customer_id)
    if not customer:
        return None  # Клієнт не знайдений

    # Оновлюємо поля, якщо вони є в customer_data
    for key, value in customer_data.items():
        if hasattr(customer, key):
            setattr(customer, key, value)

    try:
        session.commit()
        return customer
    except Exception as e:
        session.rollback()
        raise e


@customer_bp.route('/api/delete_customers/<int:customer_id>', methods=['DELETE'])
def delete_customer_route(customer_id: int):
    from database import db_session  # Assuming `db_session` is the SQLAlchemy session

    success = delete_customer(db_session, customer_id)

    if not success:
        abort(404, description="Customer not found")

    return jsonify({"message": "Customer deleted successfully"}), 204


def delete_customer(session: Session, customer_id: int):
    customer = session.query(Customer).get(customer_id)
    if not customer:
        return None  # Клієнт не знайдений

    try:
        session.delete(customer)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
