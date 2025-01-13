from flask import Blueprint
from sqlalchemy import select, func

from database import db_session
from models import PurchaseHistory, Supplier, Product, Category, product_categories_table, PackagingMaterial, \
    OtherInvestment

purchase_history_bp = Blueprint('purchase_history', __name__)


@purchase_history_bp.route('/api/get_all_purchase_history', methods=['GET'])
def get_purchase_history_data():
    """
    Отримує дані про історію закупівель для сторінки.
    :param session: Поточна сесія бази даних.
    :return: Список словників із даними про історію закупівель.
    """
    product_purchase_history_query = (
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

    # 2. Історія всіх закупівель пакування
    packaging_purchase_history_query = (
        select(
            PurchaseHistory.id.label('purchase_id'),
            PackagingMaterial.id.label('packaging_id'),
            PackagingMaterial.name.label('packaging_name'),
            Supplier.id.label('supplier_id'),
            Supplier.name.label('supplier_name'),
            PurchaseHistory.quantity_purchase.label('quantity'),
            PurchaseHistory.purchase_price_per_item.label('price_per_item'),
            PurchaseHistory.purchase_total_price.label('total_price'),
            PurchaseHistory.purchase_date.label('date')
        )
            .join(PackagingMaterial, PurchaseHistory.product_id == PackagingMaterial.id)
            .join(Supplier, PurchaseHistory.supplier_id == Supplier.id)
            .group_by(
            PurchaseHistory.id,
            PackagingMaterial.id,
            Supplier.id
        )
    )

    # 3. Інші витрати (OtherInvestments table)
    other_investments_query = (
        select(
            OtherInvestment.id.label('expense_id'),
            OtherInvestment.type_name.label('expense_name'),
            OtherInvestment.supplier.label('supplier'),
            OtherInvestment.cost.label('expense_amount'),
            OtherInvestment.date.label('expense_date')
        )
            .group_by(OtherInvestment.id)
    )

    # Виконання запитів
    product_results = db_session.execute(product_purchase_history_query).mappings().fetchall()
    packaging_results = db_session.execute(packaging_purchase_history_query).mappings().fetchall()
    other_investments_results = db_session.execute(other_investments_query).mappings().fetchall()

    # Форматування даних для продуктів
    # Перетворення масивів в один уніфікований масив
    combined_data = []

    # Обробка продуктів
    for item in product_results:
        combined_data.append({
            "id": item["purchase_id"],
            "name": item["product_name"],
            "categories": [int(cat_id) for cat_id in item["product_categories"].split(', ')] if item[
                "product_categories"] else [],
            "supplier_id": item["supplier_id"],
            "supplier_name": item["supplier_name"],
            "quantity": item["quantity"],
            "price_per_item": item["price_per_item"],
            "total_price": item["total_price"],
            "date": item["date"],
            "type": "Product",
        })

    # Обробка пакування
    for item in packaging_results:
        combined_data.append({
            "id": item["purchase_id"],
            "name": item["packaging_name"],
            "categories": [],
            "supplier_id": item["supplier_id"],
            "supplier_name": item["supplier_name"],
            "quantity": item["quantity"],
            "price_per_item": item["price_per_item"],
            "total_price": item["total_price"],
            "date": item["date"],
            "type": "Packaging",
        })

    # Обробка інших витрат
    for item in other_investments_results:
        combined_data.append({
            "id": item["expense_id"],
            "name": item["expense_name"],
            "categories": [],
            "supplier_id": None,
            "supplier_name": item["supplier"],
            "quantity": None,
            "price_per_item": None,
            "total_price": item["expense_amount"],
            "date": item["expense_date"],
            "type": "Other Investment",
        })

        # Повернення комбінованого масиву з сортуванням за датою
        combined_data_sorted = sorted(
            combined_data,
            key=lambda x: x["date"],  # Сортуємо за ключем "date"
            reverse=True  # Сортування у спадному порядку (останні дати на початку)
        )

    # Повернення комбінованого масиву
    return combined_data_sorted
