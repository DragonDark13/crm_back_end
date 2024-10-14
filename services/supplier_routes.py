from flask import Blueprint, jsonify, request
from models import Supplier, PurchaseHistory, Product
from playhouse.shortcuts import model_to_dict

# Створюємо Blueprint для постачальників
supplier_bp = Blueprint('supplier', __name__)

@supplier_bp.route('/api/supplier', methods=['POST'])
def create_supplier():
    """Додати нового постачальника"""
    data = request.get_json()

    # Перевірка наявності обов'язкового поля
    if 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400

    supplier, created = Supplier.get_or_create(name=data['name'], defaults={'contact_info': data.get('contact_info')})

    if created:
        return jsonify({'message': 'Supplier created successfully', 'supplier_id': supplier.id}), 201
    else:
        return jsonify({'error': 'Supplier already exists'}), 409


@supplier_bp.route('/api/suppliers', methods=['GET'])
def get_suppliers():
    """Отримати список усіх постачальників"""
    suppliers = Supplier.select()
    suppliers_list = [model_to_dict(supplier) for supplier in suppliers]

    return jsonify(suppliers_list), 200


def get_supplier_purchase_history(supplier_id):
    supplier = Supplier.get_by_id(supplier_id)

    # Отримання історії закупівель
    purchase_history = (PurchaseHistory
                        .select(PurchaseHistory, Product)
                        .join(Product)
                        .where(PurchaseHistory.supplier == supplier))

    products = set()  # Унікальний список продуктів

    for purchase in purchase_history:
        products.add(purchase.product)

    return {
        "supplier": supplier.name,
        "purchase_history": purchase_history,
        "products": list(products)
    }


@supplier_bp.route('/api/supplier/<int:supplier_id>/purchase-history', methods=['GET'])
def get_supplier_purchase_history_api(supplier_id):
    supplier_data = get_supplier_purchase_history(supplier_id)  # Використовуємо раніше створену функцію
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


def get_supplier_products(supplier_id):
    supplier = Supplier.get_by_id(supplier_id)

    # Отримання продуктів, пов'язаних із постачальником
    products = Product.select().where(Product.supplier == supplier)

    return {
        "supplier": supplier.name,
        "products": products
    }


@supplier_bp.route('/api/supplier/<int:supplier_id>/products', methods=['GET'])
def get_supplier_products_api(supplier_id):
    supplier_data = get_supplier_products(supplier_id)  # Використовуємо функцію для отримання продуктів
    return jsonify({
        "supplier": supplier_data['supplier'],
        "products": [{"id": product.id, "name": product.name} for product in supplier_data['products']]
    })