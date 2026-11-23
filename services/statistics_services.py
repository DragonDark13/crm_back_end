from flask import Blueprint
from sqlalchemy import func, extract

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from flask import Blueprint, jsonify, request
from sqlalchemy import func, extract

from models import (
    SaleHistory,
    PurchaseHistory,
    Product,
    ReturnHistory,
    GiftSetSalesHistory,
    PackagingPurchaseHistory,
    PackagingMaterial,
    OtherInvestment,
)

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


def _as_decimal(value):
    return Decimal(str(value or 0))


def _money(value):
    return float(_as_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _record_date(value):
    if isinstance(value, datetime):
        return value.date()
    return value


@statistics_services_bp.route("/overview", methods=["GET"])
def get_analytics_overview():
    """Return period-based sales, returns, profitability, expenses and restock alerts."""
    from postgreSQLConnect import db_session

    today = date.today()
    try:
        start_date = date.fromisoformat(request.args.get("start_date", (today.replace(day=1)).isoformat()))
        end_date = date.fromisoformat(request.args.get("end_date", today.isoformat()))
    except (TypeError, ValueError):
        return jsonify({"error": "Дати мають бути у форматі YYYY-MM-DD"}), 400

    if start_date > end_date:
        return jsonify({"error": "Початкова дата не може бути пізніше кінцевої"}), 400

    def in_period(value):
        current_date = _record_date(value)
        return current_date is not None and start_date <= current_date <= end_date

    def month_bucket(months, value):
        key = _record_date(value).strftime("%Y-%m")
        return months.setdefault(key, {
            "month": key,
            "product_sales": Decimal("0"),
            "gift_set_sales": Decimal("0"),
            "returns": Decimal("0"),
            "net_sales": Decimal("0"),
            "product_profit": Decimal("0"),
            "purchase_expenses": Decimal("0"),
            "other_expenses": Decimal("0"),
        })

    try:
        sales = db_session.query(SaleHistory).filter(
            func.date(SaleHistory.sale_date) >= start_date,
            func.date(SaleHistory.sale_date) <= end_date,
        ).all()
        gift_set_sales = db_session.query(GiftSetSalesHistory).filter(
            func.date(GiftSetSalesHistory.sold_at) >= start_date,
            func.date(GiftSetSalesHistory.sold_at) <= end_date,
        ).all()
        returns = db_session.query(ReturnHistory).filter(
            func.date(ReturnHistory.return_date) >= start_date,
            func.date(ReturnHistory.return_date) <= end_date,
        ).all()
        purchases = db_session.query(PurchaseHistory).filter(
            PurchaseHistory.purchase_date >= start_date,
            PurchaseHistory.purchase_date <= end_date,
        ).all()
        packaging_purchases = db_session.query(PackagingPurchaseHistory).filter(
            func.date(PackagingPurchaseHistory.purchase_date) >= start_date,
            func.date(PackagingPurchaseHistory.purchase_date) <= end_date,
        ).all()
        other_expenses = db_session.query(OtherInvestment).filter(
            OtherInvestment.date >= start_date,
            OtherInvestment.date <= end_date,
        ).all()

        months = {}
        product_sales_total = Decimal("0")
        gift_set_sales_total = Decimal("0")
        returns_total = Decimal("0")
        product_profit_total = Decimal("0")
        sold_quantity_total = 0
        returned_quantity_total = 0
        top_products = {}

        sales_by_id = {sale.id: sale for sale in sales}
        for sale in sales:
            revenue = _as_decimal(sale.selling_total_price)
            profit = _as_decimal(sale.profit)
            quantity = int(sale.quantity_sold or 0)
            product_sales_total += revenue
            sold_quantity_total += quantity
            bucket = month_bucket(months, sale.sale_date)
            bucket["product_sales"] += revenue
            bucket["product_profit"] += profit

            product = sale.product
            product_id = sale.product_id
            item = top_products.setdefault(product_id, {
                "product_id": product_id,
                "name": product.name if product else "Видалений товар",
                "sold_quantity": 0,
                "returned_quantity": 0,
                "sales": Decimal("0"),
                "refunds": Decimal("0"),
                "profit": Decimal("0"),
            })
            item["sold_quantity"] += quantity
            item["sales"] += revenue
            item["profit"] += profit

        for gift_sale in gift_set_sales:
            # sold_price is already the total transaction amount in the current sale flow.
            revenue = _as_decimal(gift_sale.sold_price)
            gift_set_sales_total += revenue
            month_bucket(months, gift_sale.sold_at)["gift_set_sales"] += revenue

        for return_record in returns:
            refund = _as_decimal(return_record.return_amount)
            sale = return_record.sale
            if return_record.return_amount is None and sale:
                refund = _as_decimal(sale.selling_price_per_item) * int(return_record.quantity_returned or 0)
            returns_total += refund
            returned_quantity = int(return_record.quantity_returned or 0)
            returned_quantity_total += returned_quantity
            bucket = month_bucket(months, return_record.return_date)
            bucket["returns"] += refund

            # SaleHistory.profit is a historical snapshot. Add back the recorded
            # packaging cost to isolate the product margin before allocating returns.
            if sale and sale.quantity_sold:
                packaging_cost = _as_decimal(sale.total_packaging_cost)
                product_margin = _as_decimal(sale.profit) + packaging_cost
                returned_margin = product_margin * Decimal(returned_quantity) / Decimal(sale.quantity_sold)
                bucket["product_profit"] -= returned_margin
                if sale.id in sales_by_id:
                    product_item = top_products.get(sale.product_id)
                    if product_item:
                        product_item["returned_quantity"] += returned_quantity
                        product_item["refunds"] += refund
                        product_item["profit"] -= returned_margin

        purchase_expenses_total = Decimal("0")
        for purchase in purchases:
            amount = _as_decimal(purchase.purchase_total_price)
            purchase_expenses_total += amount
            month_bucket(months, purchase.purchase_date)["purchase_expenses"] += amount

        for purchase in packaging_purchases:
            amount = _as_decimal(purchase.purchase_total_price)
            purchase_expenses_total += amount
            month_bucket(months, purchase.purchase_date)["purchase_expenses"] += amount

        other_expenses_total = Decimal("0")
        for expense in other_expenses:
            amount = _as_decimal(expense.cost)
            other_expenses_total += amount
            month_bucket(months, expense.date)["other_expenses"] += amount

        product_profit_total = sum(
            (bucket["product_profit"] for bucket in months.values()),
            Decimal("0"),
        )
        for bucket in months.values():
            bucket["net_sales"] = (
                bucket["product_sales"] + bucket["gift_set_sales"] - bucket["returns"]
            )
            bucket["gross_sales"] = bucket["product_sales"] + bucket["gift_set_sales"]
            bucket["total_expenses"] = bucket["purchase_expenses"] + bucket["other_expenses"]

        restock_items = []
        for product in db_session.query(Product).all():
            available = _as_decimal(product.available_quantity)
            threshold = _as_decimal(product.reorder_level)
            if threshold > 0 and available <= threshold:
                restock_items.append({
                    "id": product.id,
                    "name": product.name,
                    "type": "product",
                    "available_quantity": float(available),
                    "reorder_level": float(threshold),
                    "unit": product.unit_of_measure or "од.",
                })

        for material in db_session.query(PackagingMaterial).all():
            available = _as_decimal(material.available_quantity)
            threshold = _as_decimal(material.reorder_level)
            if threshold > 0 and available <= threshold:
                restock_items.append({
                    "id": material.id,
                    "name": material.name,
                    "type": "packaging",
                    "available_quantity": float(available),
                    "reorder_level": float(threshold),
                    "unit": "од.",
                })

        restock_items.sort(key=lambda item: item["available_quantity"] / item["reorder_level"])

        top_products_result = []
        for item in top_products.values():
            net_quantity = item["sold_quantity"] - item["returned_quantity"]
            top_products_result.append({
                "product_id": item["product_id"],
                "name": item["name"],
                "sold_quantity": item["sold_quantity"],
                "returned_quantity": item["returned_quantity"],
                "net_quantity": net_quantity,
                "sales": _money(item["sales"]),
                "refunds": _money(item["refunds"]),
                "net_sales": _money(item["sales"] - item["refunds"]),
                "gross_profit": _money(item["profit"]),
            })
        top_products_result.sort(
            key=lambda item: (item["net_quantity"], item["net_sales"]),
            reverse=True,
        )

        monthly_result = []
        for key in sorted(months):
            bucket = months[key]
            monthly_result.append({
                "month": key,
                "product_sales": _money(bucket["product_sales"]),
                "gift_set_sales": _money(bucket["gift_set_sales"]),
                "gross_sales": _money(bucket["gross_sales"]),
                "returns": _money(bucket["returns"]),
                "net_sales": _money(bucket["net_sales"]),
                "product_gross_profit": _money(bucket["product_profit"]),
                "purchase_expenses": _money(bucket["purchase_expenses"]),
                "other_expenses": _money(bucket["other_expenses"]),
                "total_expenses": _money(bucket["total_expenses"]),
            })

        return jsonify({
            "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            "summary": {
                "product_sales": _money(product_sales_total),
                "gift_set_sales": _money(gift_set_sales_total),
                "gross_sales": _money(product_sales_total + gift_set_sales_total),
                "returns": _money(returns_total),
                "net_sales": _money(product_sales_total + gift_set_sales_total - returns_total),
                "product_gross_profit": _money(product_profit_total),
                "sold_quantity": sold_quantity_total,
                "returned_quantity": returned_quantity_total,
                "purchase_expenses": _money(purchase_expenses_total),
                "other_expenses": _money(other_expenses_total),
                "total_expenses": _money(purchase_expenses_total + other_expenses_total),
                "restock_count": len(restock_items),
            },
            "monthly": monthly_result,
            "top_products": top_products_result[:10],
            "restock": restock_items,
            "profit_scope_note": (
                "Валовий прибуток охоплює звичайні товарні продажі. "
                "Виручка гіфтбоксів включена в продажі, але їхній прибуток не розраховується, "
                "оскільки історія не зберігає собівартість компонентів на момент продажу."
            ),
        }), 200
    finally:
        db_session.close()
