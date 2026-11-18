from flask import Blueprint
from sqlalchemy import func, extract

from models import SaleHistory, PurchaseHistory, Product

statistics_services_bp = Blueprint('statistics_services', __name__)


@statistics_services_bp.route("/sales/monthly", methods=["GET"])
def get_monthly_sales_statistics():
    from postgreSQLConnect import db_session

    results = (
        db_session.query(
            extract('year', SaleHistory.sale_date).label("year"),
            extract('month', SaleHistory.sale_date).label("month"),
            func.sum(SaleHistory.selling_total_price).label("total_sales"),
            func.sum(SaleHistory.quantity_sold).label("total_quantity"),
            func.sum(SaleHistory.profit).label("total_profit")
        )
        .group_by(extract('year', SaleHistory.sale_date), extract('month', SaleHistory.sale_date))
        .order_by(extract('year', SaleHistory.sale_date), extract('month', SaleHistory.sale_date))
        .all()
    )

    # Формуємо у зручний формат для фронтенду
    return [
        {
            "year": int(r.year),
            "month": int(r.month),
            "total_sales": float(r.total_sales),
            "total_quantity": int(r.total_quantity),
            "total_profit": float(r.total_profit)
        }
        for r in results
    ]


@statistics_services_bp.route("/purchases/monthly", methods=["GET"])
def get_monthly_purchases_statistics():
    from postgreSQLConnect import db_session

    results = (
        db_session.query(
            extract('year', PurchaseHistory.purchase_date).label("year"),
            extract('month', PurchaseHistory.purchase_date).label("month"),
            func.sum(PurchaseHistory.purchase_total_price).label("total_spent"),
            func.sum(PurchaseHistory.quantity_purchase).label("total_quantity"),
            func.avg(PurchaseHistory.purchase_price_per_item).label("avg_price")
        )
        .group_by(extract('year', PurchaseHistory.purchase_date), extract('month', PurchaseHistory.purchase_date))
        .order_by(extract('year', PurchaseHistory.purchase_date), extract('month', PurchaseHistory.purchase_date))
        .all()
    )

    # Форматуємо результат для фронтенду
    return [
        {
            "year": int(r.year),
            "month": int(r.month),
            "total_spent": float(r.total_spent),
            "total_quantity": float(r.total_quantity),
            "avg_price": float(r.avg_price)
        }
        for r in results
    ]


@statistics_services_bp.route("/stock", methods=["GET"])
def get_stock_levels():
    from postgreSQLConnect import db_session

    products = db_session.query(Product).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "available_quantity": p.available_quantity,
            "total_quantity": p.total_quantity
        }
        for p in products
    ]


@statistics_services_bp.route("/profit-expense", methods=["GET"])
def get_profit_expense_by_month():
    from postgreSQLConnect import db_session

    # Продажі по місяцях
    sales = (
        db_session.query(
            extract('year', SaleHistory.sale_date).label("year"),
            extract('month', SaleHistory.sale_date).label("month"),
            func.sum(SaleHistory.selling_total_price).label("total_sales"),
            func.sum(SaleHistory.profit).label("total_profit")
        )
        .group_by(extract('year', SaleHistory.sale_date), extract('month', SaleHistory.sale_date))
        .all()
    )

    # Закупки по місяцях
    purchases = (
        db_session.query(
            extract('year', PurchaseHistory.purchase_date).label("year"),
            extract('month', PurchaseHistory.purchase_date).label("month"),
            func.sum(PurchaseHistory.purchase_total_price).label("total_spent")
        )
        .group_by(extract('year', PurchaseHistory.purchase_date), extract('month', PurchaseHistory.purchase_date))
        .all()
    )

    # Об'єднуємо за ключем (рік, місяць), включно з місяцями лише із закупівлями.
    stats_by_month = {}

    for sale in sales:
        month_key = (int(sale.year), int(sale.month))
        stats_by_month[month_key] = {
            "year": month_key[0],
            "month": month_key[1],
            "sales": float(sale.total_sales or 0),
            "profit": float(sale.total_profit or 0),
            "expenses": 0
        }

    for purchase in purchases:
        month_key = (int(purchase.year), int(purchase.month))
        month_stats = stats_by_month.setdefault(month_key, {
            "year": month_key[0],
            "month": month_key[1],
            "sales": 0,
            "profit": 0,
            "expenses": 0
        })
        month_stats["expenses"] = float(purchase.total_spent or 0)

    return [
        stats_by_month[month_key]
        for month_key in sorted(stats_by_month)
    ]

@statistics_services_bp.route("/customer-activity", methods=["GET"])
def get_customer_activity():
    from postgreSQLConnect import db_session

    results = (
        db_session.query(
            func.date(SaleHistory.sale_date).label("day"),
            func.count(SaleHistory.customer_id.distinct()).label("active_customers")
        )
        .group_by(func.date(SaleHistory.sale_date))
        .order_by(func.date(SaleHistory.sale_date))
        .all()
    )
    return [{"day": r.day.strftime("%Y-%m-%d"), "active_customers": r.active_customers} for r in results]


@statistics_services_bp.route("/top-products", methods=["GET"])
def get_top_10_products():
    # Агрегуємо продажі по товару
    from postgreSQLConnect import db_session

    results = (
        db_session.query(
            SaleHistory.product_id,
            Product.name,
            func.sum(SaleHistory.quantity_sold).label("total_sold"),
            func.sum(SaleHistory.selling_total_price).label("total_sales")
        )
        .join(Product, Product.id == SaleHistory.product_id)
        .group_by(SaleHistory.product_id, Product.name)
        .order_by(func.sum(SaleHistory.quantity_sold).desc())  # Сортуємо за кількістю проданих одиниць
        .limit(10)
        .all()
    )

    # Перетворюємо у список словників
    return [
        {
            "product_id": r.product_id,
            "name": r.name,
            "total_sold": int(r.total_sold),
            "total_sales": float(r.total_sales)
        }
        for r in results
    ]
