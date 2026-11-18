"""Database-backed regression tests for monthly financial statistics."""

import importlib
from datetime import date, datetime
from decimal import Decimal

import pytest

# Initialize the isolated SQLite database and Flask app used by backend tests.
importlib.import_module("test_authorization")

from models import Product, PurchaseHistory, SaleHistory, db  # noqa: E402
from postgreSQLConnect import db_session, engine  # noqa: E402
from services.statistics_services import (  # noqa: E402
    get_monthly_sales_statistics,
    get_monthly_purchases_statistics,
    get_profit_expense_by_month,
)

db.metadata.create_all(
    bind=engine,
    tables=[Product.__table__, PurchaseHistory.__table__, SaleHistory.__table__],
)


@pytest.fixture(autouse=True)
def clean_financial_records():
    db_session.remove()
    db_session.query(SaleHistory).delete()
    db_session.query(PurchaseHistory).delete()
    db_session.commit()
    yield
    db_session.rollback()
    db_session.remove()


def _purchase(amount, quantity, unit_price, purchased_on):
    db_session.add(
        PurchaseHistory(
            product_id=None,
            supplier_id=None,
            purchase_total_price=Decimal(amount),
            purchase_price_per_item=Decimal(unit_price),
            quantity_purchase=quantity,
            purchase_date=purchased_on,
        )
    )


def _sale(amount, quantity, profit, sold_on):
    db_session.add(
        SaleHistory(
            product_id=None,
            customer_id=None,
            selling_total_price=Decimal(amount),
            selling_price_per_item=Decimal(amount) / Decimal(quantity),
            quantity_sold=quantity,
            profit=Decimal(profit),
            sale_date=datetime.combine(sold_on, datetime.min.time()),
        )
    )


def test_monthly_sales_statistics_aggregate_amount_quantity_and_profit():
    _sale("59.97", 3, "15.00", date(2026, 11, 5))
    _sale("20.00", 1, "5.00", date(2026, 11, 28))
    _sale("10.00", 1, "2.00", date(2026, 12, 1))
    db_session.commit()

    result = get_monthly_sales_statistics()

    assert result == [
        {
            "year": 2026,
            "month": 11,
            "total_sales": 79.97,
            "total_quantity": 4,
            "total_profit": 20.00,
        },
        {
            "year": 2026,
            "month": 12,
            "total_sales": 10.00,
            "total_quantity": 1,
            "total_profit": 2.00,
        },
    ]


def test_monthly_purchase_statistics_aggregate_spending_quantity_and_average():
    _purchase("30.00", 3, "10.00", date(2026, 11, 2))
    _purchase("25.00", 2, "12.50", date(2026, 11, 20))
    _purchase("10.01", 1, "10.01", date(2026, 12, 1))
    db_session.commit()

    result = get_monthly_purchases_statistics()

    assert result[0]["year"] == 2026
    assert result[0]["month"] == 11
    assert result[0]["total_spent"] == 55.00
    assert result[0]["total_quantity"] == 5.0
    assert result[0]["avg_price"] == 11.25
    assert result[1]["total_spent"] == 10.01


def test_profit_expense_statistics_include_purchase_only_months():
    _sale("100.00", 2, "30.00", date(2026, 11, 15))
    _purchase("45.50", 3, "15.1667", date(2026, 11, 3))
    _purchase("20.00", 2, "10.00", date(2026, 12, 8))
    db_session.commit()

    result = get_profit_expense_by_month()

    assert result == [
        {"year": 2026, "month": 11, "sales": 100.0, "profit": 30.0, "expenses": 45.5},
        {"year": 2026, "month": 12, "sales": 0, "profit": 0, "expenses": 20.0},
    ]


def test_financial_statistics_keep_cent_precision_for_aggregated_values():
    _sale("0.10", 1, "0.03", date(2026, 11, 1))
    _sale("0.20", 1, "0.06", date(2026, 11, 2))
    _purchase("0.10", 1, "0.10", date(2026, 11, 1))
    _purchase("0.20", 1, "0.20", date(2026, 11, 2))
    db_session.commit()

    sales = get_monthly_sales_statistics()[0]
    purchases = get_monthly_purchases_statistics()[0]

    assert sales["total_sales"] == 0.30
    assert sales["total_profit"] == 0.09
    assert purchases["total_spent"] == 0.30
