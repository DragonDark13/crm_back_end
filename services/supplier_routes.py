from flask import Blueprint, jsonify, request
from models import Supplier, PurchaseHistory, Product, PackagingMaterialSupplier
from sqlalchemy.exc import IntegrityError

# Create Blueprint for suppliers

supplier_bp = Blueprint('supplier', __name__)


# Create a new supplier
@supplier_bp.route('/create_supplier', methods=['POST'])
def create_supplier():
    """Add a new supplier"""
    from postgreSQLConnect import db_session

    data = request.get_json()

    # Check for required fields
    if 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400

    # Check if the supplier already exists
    existing_supplier = db_session.query(Supplier).filter_by(name=data['name']).first()
    if existing_supplier:
        return jsonify({'error': 'Supplier already exists'}), 409

    try:
        # Create the supplier
        supplier = Supplier(
            name=data['name'],
            contact_info=data.get('contact_info'),
            email=data.get('email'),
            phone_number=data.get('phone_number'),
            address=data.get('address')
        )
        db_session.add(supplier)
        db_session.commit()

        return jsonify({'message': 'Supplier created successfully', 'supplier_id': supplier.id}), 201
    except IntegrityError as e:
        db_session.rollback()
        return jsonify({'error': f'Failed to create supplier: {str(e)}'}), 500
    except Exception as e:
        db_session.rollback()
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500


# Get all suppliers
@supplier_bp.route('/suppliers/list', methods=['GET'])
def get_suppliers():
    from postgreSQLConnect import db_session

    """Отримати список всіх постачальників (товарів і пакування)"""
    product_suppliers = db_session.query(Supplier).order_by(Supplier.name).all()
    packaging_suppliers = db_session.query(PackagingMaterialSupplier).order_by(PackagingMaterialSupplier.name).all()

    product_suppliers_list = [
        {**supplier.to_dict(), "type": "product"} for supplier in product_suppliers
    ]

    packaging_suppliers_list = [
        {**supplier.to_dict(), "type": "packaging"} for supplier in packaging_suppliers
    ]

    combined_suppliers = product_suppliers_list + packaging_suppliers_list

    return jsonify(combined_suppliers), 200


# Get supplier purchase history
def get_supplier_purchase_history(supplier_id):
    from postgreSQLConnect import db_session

    supplier = db_session.query(Supplier).filter_by(id=supplier_id).one_or_none()

    if not supplier:
        return None

    # Get purchase history with products
    purchase_history = db_session.query(PurchaseHistory).join(Product).filter(
        PurchaseHistory.supplier == supplier).all()

    products = {purchase.product for purchase in purchase_history}

    return {
        "supplier": supplier.name,
        "purchase_history": purchase_history,
        "products": list(products)
    }


# Get supplier purchase history through API endpoint
@supplier_bp.route('/supplier/<int:supplier_id>/purchase-history', methods=['GET'])
def get_supplier_purchase_history_api(supplier_id):
    supplier_data = get_supplier_purchase_history(supplier_id)

    if not supplier_data:
        return jsonify({'error': 'Supplier not found'}), 404

    return jsonify({
        "supplier": supplier_data['supplier'],
        "purchase_history": [{
            "product": purchase.product.name,
            "quantity_purchase": purchase.quantity_purchase,
            "purchase_date": purchase.purchase_date,
            "purchase_price_per_item": purchase.purchase_price_per_item,
            "purchase_total_price": purchase.purchase_total_price
        } for purchase in supplier_data['purchase_history']],
        "products": [{"id": product.id, "name": product.name} for product in supplier_data['products']]
    })


# Get supplier products
def get_supplier_products(supplier_id):
    from postgreSQLConnect import db_session

    supplier = db_session.query(Supplier).filter_by(id=supplier_id).one_or_none()

    if not supplier:
        return None

    products = db_session.query(Product).filter_by(supplier_id=supplier.id).all()

    return {
        "supplier": supplier.name,
        "products": products
    }


# Get supplier products through API endpoint
@supplier_bp.route('/supplier/<int:supplier_id>/products', methods=['GET'])
def get_supplier_products_api(supplier_id):
    supplier_data = get_supplier_products(supplier_id)

    if not supplier_data:
        return jsonify({'error': 'Supplier not found'}), 404

    return jsonify({
        "supplier": supplier_data['supplier'],
        "products": [{"id": product.id, "name": product.name} for product in supplier_data['products']]
    })


# Delete a supplier
@supplier_bp.route('/delete_supplier/<int:supplier_id>', methods=['DELETE'])
def delete_supplier(supplier_id):
    from postgreSQLConnect import db_session

    """Delete a supplier by ID"""
    supplier = db_session.query(Supplier).filter_by(id=supplier_id).one_or_none()

    if not supplier:
        return jsonify({'error': 'Supplier not found'}), 404

    try:
        db_session.delete(supplier)
        db_session.commit()
        return jsonify({'message': 'Supplier deleted successfully'}), 200
    except Exception as e:
        db_session.rollback()
        return jsonify({'error': f'Failed to delete supplier: {str(e)}'}), 500


# Update supplier data
@supplier_bp.route('/supplier_edit/<int:supplier_id>', methods=['PUT'])
def update_supplier(supplier_id):
    """Update supplier information"""
    data = request.get_json()
    from postgreSQLConnect import db_session

    supplier = db_session.query(Supplier).filter_by(id=supplier_id).one_or_none()

    if not supplier:
        return jsonify({'error': 'Supplier not found'}), 404

    # Update fields based on request data
    supplier.name = data.get('name', supplier.name)
    supplier.contact_info = data.get('contact_info', supplier.contact_info)
    supplier.email = data.get('email', supplier.email)
    supplier.phone_number = data.get('phone_number', supplier.phone_number)
    supplier.address = data.get('address', supplier.address)

    # Додано: оновлення is_active, якщо воно передано
    if 'is_active' in data:
        supplier.is_active = bool(data['is_active'])

    try:
        db_session.commit()
        return jsonify({'message': 'Supplier updated successfully'}), 200
    except IntegrityError as e:
        db_session.rollback()
        return jsonify({'error': f'Failed to update supplier: {str(e)}'}), 500
    except Exception as e:
        db_session.rollback()
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500
