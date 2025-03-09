from flask import Flask, jsonify, request, Blueprint
from sqlalchemy.orm import joinedload
from datetime import datetime

from models import db, SaleHistory, Product, Customer, PackagingSaleHistory

sales_history_services_bp = Blueprint('sales_history', __name__)


@sales_history_services_bp.route('/api/get_all_sales_history', methods=['GET'])
def get_sales_history():
    from postgreSQLConnect import db_session

    query = db_session.query(SaleHistory).join(Product).join(Customer)

    # Отримуємо всі записи без сортування
    sales_history = query.all()

    # Підготовка даних для фронтенду
    sales_data = []
    for sale in sales_history:
        # Знаходимо відповідне пакування для кожного запису в історії продажу
        packaging_sale = db_session.query(PackagingSaleHistory).filter(
            PackagingSaleHistory.sale_id == sale.id,
            PackagingSaleHistory.packaging_material_id == sale.packaging_material_id
        ).first()

        # Підготовка інформації про пакування (якщо воно є)
        packaging_details = {}
        if packaging_sale:
            packaging_details = {
                'package_id': packaging_sale.packaging_material_id,
                'packaging_name': packaging_sale.packaging_material.name,
                'quantity_sold': packaging_sale.packaging_quantity,
                'unit_price': str(packaging_sale.packaging_material.purchase_price_per_unit),
                'total_price': str(packaging_sale.total_packaging_cost)
            }

        product_data = {
            'sale_history_id': sale.id,
            'product_name': sale.product.name,
            'categories': [{
                'id': category.id,
                'name': category.name
            } for category in sale.product.categories],  # Повертати категорії як об'єкти
            'supplier': {
                'id': sale.product.supplier.id if sale.product.supplier else None,
                'name': sale.product.supplier.name if sale.product.supplier else ''
            },  # Повертати постачальника як об'єкт
            'customer': {
                'id': sale.customer.id,
                'name': sale.customer.name
            },  # Повертати клієнта як об'єкт
            'quantity_sold': sale.quantity_sold,
            'unit_price': str(sale.selling_price_per_item),
            'total_price': str(sale.selling_total_price),
            'sale_date': sale.sale_date.strftime('%Y-%m-%d %H:%M:%S'),
            'packaging_details': [packaging_details],  # Повертаємо один запис про пакування
        }
        sales_data.append(product_data)

    return jsonify(sales_data)
