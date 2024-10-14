from flask import Blueprint, jsonify, request
from models import Customer, SaleHistory
from playhouse.shortcuts import model_to_dict
from peewee import IntegrityError

# Створюємо Blueprint для покупців
customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/api/customers', methods=['POST'])
def create_customer():
    data = request.get_json()
    required_fields = ['name', 'email']

    # Перевірка на обов'язкові поля
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

    try:
        # Створення нового покупця
        customer = Customer.create(
            name=data['name'],
            contact_info=data.get('contact_info'),
            address=data.get('address'),
            email=data['email'],
            phone_number=data.get('phone_number')
        )
        return jsonify({'message': 'Customer created successfully', 'customer': model_to_dict(customer)}), 201
    except IntegrityError:
        return jsonify({'error': 'Customer with this email already exists'}), 400


@customer_bp.route('/api/customers', methods=['GET'])
def get_all_customers():
    customers = Customer.select()
    customer_list = [model_to_dict(customer) for customer in customers]
    return jsonify(customer_list), 200


@customer_bp.route('/api/customers/<int:customer_id>', methods=['GET'])
def get_customer_details(customer_id):
    try:
        customer = Customer.get_by_id(customer_id)
        customer_data = model_to_dict(customer)

        # Отримуємо продажі, пов'язані з покупцем
        sales = SaleHistory.select().where(SaleHistory.customer == customer)
        customer_data['sales'] = [model_to_dict(sale) for sale in sales]

        return jsonify(customer_data), 200
    except Customer.DoesNotExist:
        return jsonify({'error': 'Customer not found'}), 404
