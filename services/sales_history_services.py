from uuid import uuid4

from flask import Flask, jsonify, request, Blueprint

from decimal import Decimal

from models import db, SaleHistory, Product, Customer, PackagingSaleHistory, GiftSetSalesHistory

sales_history_services_bp = Blueprint('sales_history', __name__)


# Функція для додавання унікального sale_history_id
def add_sale_history_id(sales_data):
    for sale in sales_data:
        # Додаємо унікальний sale_history_id для кожного елемента
        sale['sale_history_id'] = str(uuid4())
    return sales_data


@sales_history_services_bp.route('/api/get_all_sales_history', methods=['GET'])
def get_sales_history():
    from postgreSQLConnect import db_session

    # Отримуємо всі записи історії продажів одиничних товарів
    query = db_session.query(SaleHistory).join(Product).join(Customer)
    sales_history = query.all()

    # Отримуємо всі записи історії продажів подарункових наборів
    gift_set_sales_history = db_session.query(GiftSetSalesHistory).all()

    # Функція для обчислення собівартості товару
    def calculate_product_cost(item):
        return Decimal(item.gift_set_product.product.purchase_price_per_item) * Decimal(item.quantity)

    # Функція для обчислення собівартості пакування
    def calculate_packaging_cost(item):
        return Decimal(item.gift_set_packaging.packaging.purchase_price_per_unit) * Decimal(item.quantity)

    # Функція для створення даних про товар
    def create_product_data(item):
        return {
            "product_id": item.gift_set_product.product_id,
            "name": item.gift_set_product.product.name,
            "quantity": item.quantity,
            "unit_price": str(item.gift_set_product.product.purchase_price_per_item),
            "total_price": str(calculate_product_cost(item)),
            "supplier": {
                "id": item.gift_set_product.product.supplier.id if item.gift_set_product.product.supplier else None,
                "name": item.gift_set_product.product.supplier.name if item.gift_set_product.product.supplier else ''
            }
        }

    # Функція для створення даних про пакування
    def create_packaging_data(item):
        return {
            "packaging_id": item.gift_set_packaging.packaging_id,
            "packaging_name": item.gift_set_packaging.packaging.name,
            "quantity": item.quantity,
            "unit_price": str(item.gift_set_packaging.packaging.purchase_price_per_unit),
            "total_price": str(calculate_packaging_cost(item)),
            "supplier": {
                "id": item.gift_set_packaging.packaging.packaging_material_supplier.id if item.gift_set_packaging.packaging.packaging_material_supplier else None,
                "name": item.gift_set_packaging.packaging.packaging_material_supplier.name if item.gift_set_packaging.packaging.packaging_material_supplier else ''
            }
        }

    # Підготовка даних для одиничних товарів
    sales_data = []
    for sale in sales_history:
        # Знаходимо відповідне пакування для кожного запису в історії продажу
        packaging_sale = db_session.query(PackagingSaleHistory).filter(
            PackagingSaleHistory.sale_id == sale.id,
            PackagingSaleHistory.packaging_material_id == sale.packaging_material_id
        ).first()

        # Собівартість товару (ціна закупівлі)
        product_cost = sale.product.purchase_price_per_item * sale.quantity_sold

        # Собівартість пакування (якщо є)
        packaging_cost = 0
        if packaging_sale:
            packaging_cost = packaging_sale.packaging_material.purchase_price_per_unit * Decimal(
                packaging_sale.packaging_quantity)

        # Загальна собівартість (товар + пакування)
        total_cost = product_cost + packaging_cost

        # Вигода (прибуток)
        profit = sale.selling_total_price - total_cost

        # Підготовка інформації про пакування (якщо воно є)
        packaging_details = {}
        if packaging_sale:
            packaging_details = {
                'package_id': packaging_sale.packaging_material_id,
                'packaging_name': packaging_sale.packaging_material.name,
                'quantity_sold': packaging_sale.packaging_quantity,
                'unit_price': str(packaging_sale.packaging_material.purchase_price_per_unit),
                'total_price': str(packaging_sale.total_packaging_cost),
                'supplier': {
                    'id': packaging_sale.packaging_material.packaging_material_supplier.id if packaging_sale.packaging_material.packaging_material_supplier else None,
                    'name': packaging_sale.packaging_material.packaging_material_supplier.name if packaging_sale.packaging_material.packaging_material_supplier else ''
                }  # Додаємо постачальника пакування
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
            'sale_date': sale.sale_date.strftime('%Y-%m-%d'),
            'packaging_details': [packaging_details] if packaging_sale else [],  # Повертаємо один запис про пакування
            'type': 'product_with_packaging' if packaging_sale else 'product',  # Зміна типу, якщо є пакування
            'cost_price': str(total_cost),  # Собівартість
            'profit': str(profit),  # Вигода
        }
        sales_data.append(product_data)

    # Додавання даних про продажі подарункових наборів
    for sale in gift_set_sales_history:
        gift_set_name = sale.gift_set.name if sale.gift_set else 'Unknown'

        # Обчислення собівартості подарункового набору
        cost_price = sum(calculate_product_cost(item) for item in sale.sales_history_products) + \
                     sum(calculate_packaging_cost(item) for item in sale.sales_history_packagings)

        products_data = [create_product_data(item) for item in sale.sales_history_products]
        packagings_data = [create_packaging_data(item) for item in sale.sales_history_packagings]

        # Розрахунок вигоди
        profit = Decimal(sale.sold_price) - cost_price

        # Підготовка даних про продаж подарункового набору
        gift_set_sale_data = {
            "id": sale.id,
            "gift_set_id": sale.gift_set_id,
            "product_name": gift_set_name,
            "sale_date": sale.sold_at.strftime('%Y-%m-%d'),
            "total_price": str(sale.sold_price),
            "cost_price": str(cost_price),
            "profit": str(profit),
            "quantity": sale.quantity,
            "customer": {
                'id': sale.customer.id,
                'name': sale.customer.name
            },
            "products": products_data,
            "packagings": packagings_data,
            'type': 'gift_set'
        }
        sales_data.append(gift_set_sale_data)

        # Додаємо унікальні sale_history_id до кожного елемента
    combined_sales_data_with_id = add_sale_history_id(sales_data)

    return jsonify(combined_sales_data_with_id)
