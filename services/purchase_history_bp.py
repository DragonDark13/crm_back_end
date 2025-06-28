from datetime import datetime, date

from flask import Blueprint
from sqlalchemy import select, func
from sqlalchemy import String

from models import PurchaseHistory, Supplier, Product, Category, product_categories_table, PackagingMaterial, \
    OtherInvestment, PackagingPurchaseHistory, PackagingMaterialSupplier

purchase_history_bp = Blueprint('purchase_history', __name__)


@purchase_history_bp.route('/get_all_purchase_history', methods=['GET'])
def get_purchase_history_data():
    """
    Отримує дані про історію закупівель для сторінки.
    :param session: Поточна сесія бази даних.
    :return: Список словників із даними про історію закупівель.
    """
    from postgreSQLConnect import db_session

    product_purchase_history_query = (
        select(
            PurchaseHistory.id.label('purchase_id'),
            Product.id.label('product_id'),
            Product.name.label('product_name'),
            func.string_agg(Category.id.cast(String), ', ').label('product_categories'),
            # Використовуємо string_agg для PostgreSQL
            Supplier.id.label('supplier_id'),
            Supplier.name.label('supplier_name'),
            PurchaseHistory.quantity_purchase.label('quantity'),
            PurchaseHistory.purchase_price_per_item.label('price_per_item'),
            PurchaseHistory.purchase_total_price.label('total_price'),
            PurchaseHistory.purchase_date.label('date')
        )
            .join(Product, PurchaseHistory.product_id == Product.id)
            .join(Supplier, PurchaseHistory.supplier_id == Supplier.id)
            .outerjoin(product_categories_table, product_categories_table.c.product_id == Product.id)
            .outerjoin(Category, product_categories_table.c.category_id == Category.id)
            .group_by(
            PurchaseHistory.id,
            Product.id,
            Supplier.id
        )
    )
    # 2. Історія всіх закупівель пакування
    packaging_purchase_history_query = (
        select(
            PackagingPurchaseHistory.id.label('purchase_history_id'),
            PackagingMaterial.id.label('packaging_material_id'),
            PackagingMaterial.name.label('packaging_material_name'),
            PackagingMaterialSupplier.name.label('supplier_name'),  # Ім'я постачальника
            # З'єднання імен постачальників у рядок
            PackagingPurchaseHistory.quantity_purchased.label('quantity'),
            PackagingPurchaseHistory.purchase_price_per_unit.label('price_per_unit'),
            PackagingPurchaseHistory.purchase_total_price.label('total_price'),
            PackagingPurchaseHistory.purchase_date.label('purchase_date')
        )
            .join(PackagingMaterial, PackagingPurchaseHistory.material_id == PackagingMaterial.id)
            .join(PackagingMaterialSupplier, PackagingPurchaseHistory.supplier_id == PackagingMaterialSupplier.id)
            .group_by(
            PackagingPurchaseHistory.id,
            PackagingMaterial.id,
            PackagingMaterialSupplier.id
        )  # Групування для уникнення дублювання
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

    def unify_date(date):
        if isinstance(date, datetime):
            return date.date()  # Повертає тільки дату
        elif isinstance(date, str):
            return datetime.fromisoformat(date).date()  # Перетворює ISO-строку в дату
        return date  # Якщо це вже дата, повертаємо її без змін

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
            "date": unify_date(item["date"]),
            "type": "Product",
        })

    # Обробка пакування
    for item in packaging_results:
        combined_data.append({
            "id": item["purchase_history_id"],
            "name": item['packaging_material_name'],
            "categories": [],
            "supplier_name": item["supplier_name"],
            "quantity": item["quantity"],
            "price_per_item": item["price_per_unit"],
            "total_price": item["total_price"],
            "date": unify_date(item["purchase_date"]),
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
            "date": unify_date(item["expense_date"]),
            "type": "Other Investment",
        })

    # Повернення комбінованого масиву з сортуванням за датою
    combined_data_sorted = sorted(
        combined_data,
        key=lambda x: x["date"],
        reverse=True  # Сортування у спадному порядку (останні дати на початку)
    )

    # Приводимо дати до формату dd-mm-yyyy
    for item in combined_data_sorted:
        item["date"] = item["date"].strftime("%Y-%m-%d")  # Формат dd-mm-yyyy

    return combined_data_sorted
