from flask import Blueprint, jsonify, request
from models import Customer, SaleHistory, db_session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

# Create Blueprint for customers
customer_bp = Blueprint('customer', __name__)


# Create customer
@customer_bp.route('/api/customers', methods=['POST'])
def create_customer():
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
@customer_bp.route('/api/customers', methods=['GET'])
def get_all_customers():
    customers = db_session.query(Customer).all()
    customer_list = [customer.to_dict() for customer in customers]
    return jsonify(customer_list), 200


# Get customer details by ID
@customer_bp.route('/api/customers/<int:customer_id>', methods=['GET'])
def get_customer_details(customer_id):
    try:
        customer = db_session.query(Customer).filter_by(id=customer_id).one()
        customer_data = customer.to_dict()

        # Get related sales for the customer
        sales = db_session.query(SaleHistory).filter_by(customer_id=customer_id).all()
        customer_data['sales'] = [sale.to_dict() for sale in sales]

        return jsonify(customer_data), 200
    except Exception as e:
        return jsonify({'error': f'Customer not found: {str(e)}'}), 404
