from flask import Blueprint
from sqlalchemy import select, func

from database import db_session
from models import PurchaseHistory, Supplier, Product, Category, product_categories_table

purchase_history_bp = Blueprint('purchase_history', __name__)


@purchase_history_bp.route('/api/get_all_purchase_history', methods=['GET'])
def get_purchase_history_data():
    """
    Отримує дані про історію закупівель для сторінки.
    :param session: Поточна сесія бази даних.
    :return: Список словників із даними про історію закупівель.
    """
    query = (
        select(
            PurchaseHistory.id.label('purchase_id'),
            Product.id.label('product_id'),
            Product.name.label('product_name'),
            func.group_concat(Category.id, ', ').label('product_categories'),  # З'єднання ід категорій у рядок
            Supplier.id.label('supplier_id'),
            Supplier.name.label('supplier_name'),
            PurchaseHistory.quantity_purchase.label('quantity'),
            PurchaseHistory.purchase_price_per_item.label('price_per_item'),
            PurchaseHistory.purchase_total_price.label('total_price'),
            PurchaseHistory.purchase_date.label('date')
        )
            .join(Product, PurchaseHistory.product_id == Product.id)
            .join(Supplier, PurchaseHistory.supplier_id == Supplier.id)
            .join(product_categories_table,
                  product_categories_table.c.product_id == Product.id)  # Зв'язок продуктів і категорій
            .join(Category, product_categories_table.c.category_id == Category.id)
            .group_by(
            PurchaseHistory.id,
            Product.id,
            Supplier.id
        )  # Групування, щоб уникнути дублювання
    )

    results = db_session.execute(query).fetchall()

    # Форматування даних для зручного використання у фронтенді
    purchase_history_data = []
    for row in results:
        purchase_history_data.append({
            "purchase_id": row.purchase_id,
            "product_id": row.product_id,
            "product_name": row.product_name,

            "product_categories": [int(cat_id) for cat_id in
                                   row.product_categories.split(', ')] if row.product_categories else [],
            # Перетворення в масив ід
            # Додавання категорії            "product_name": row.product_name,
            "supplier_id": row.supplier_id,
            "supplier_name": row.supplier_name,
            "quantity": row.quantity,
            "price_per_item": float(row.price_per_item or 0),
            "total_price": float(row.total_price or 0),
            "date": row.date.strftime('%Y-%m-%d')
        })

    return purchase_history_data
