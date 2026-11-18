"""Integration tests for purchase and sale financial operations."""

import importlib
from datetime import datetime
from decimal import Decimal

import pytest

# Initialize the isolated SQLite database and Flask app used by backend tests.
auth_module = importlib.import_module("test_authorization")

from models import (  # noqa: E402
    Customer,
    Product,
    PurchaseHistory,
    SaleHistory,
    Supplier,
    db,
)
from postgreSQLConnect import db_session, engine  # noqa: E402

db.metadata.create_all(bind=engine)


@pytest.fixture
def client():
    with auth_module.app.test_client() as test_client:
        yield test_client


@pytest.fixture
def auth_tokens():
    return auth_module.auth_tokens.__wrapped__()


@pytest.fixture(autouse=True)
def clean_financial_operation_records():
    db_session.remove()
    db_session.query(SaleHistory).delete()
    db_session.query(PurchaseHistory).delete()
    db_session.query(Product).delete()
    db_session.query(Customer).delete()
    db_session.query(Supplier).delete()
    db_session.commit()
    yield
    db_session.rollback()
    db_session.remove()


@pytest.fixture
def financial_dependencies():
    supplier = Supplier(name="Financial test supplier")
    customer = Customer(name="Financial test customer")
    db_session.add_all([supplier, customer])
    db_session.flush()

    product = Product(
        name="Financial test product",
        supplier_id=supplier.id,
        total_quantity=10,
        available_quantity=10,
        sold_quantity=0,
        purchase_total_price=Decimal("100.00"),
        purchase_price_per_item=Decimal("10.00"),
        selling_total_price=Decimal("0.00"),
        selling_price_per_item=Decimal("20.00"),
        selling_quantity=0,
        article="FIN-0001",
        product_description="Financial integration test",
    )
    db_session.add(product)
    db_session.commit()
    return product, supplier, customer


def _manager_headers(auth_tokens):
    return {"Authorization": f"Bearer {auth_tokens['manager']}"}


def test_purchase_updates_stock_cost_and_purchase_history(
    client, auth_tokens, financial_dependencies
):
    product, supplier, _customer = financial_dependencies

    response = client.post(
        f"/api/product/{product.id}/purchase",
        headers=_manager_headers(auth_tokens),
        json={
            "quantity": 5,
            "purchase_price_per_item": "12.50",
            "purchase_total_price": "62.50",
            "supplier_id": supplier.id,
            "purchase_date": "2026-11-18",
        },
    )

    assert response.status_code == 201

    db_session.expire_all()
    updated_product = db_session.query(Product).filter_by(id=product.id).one()
    purchase = db_session.query(PurchaseHistory).filter_by(product_id=product.id).one()

    assert updated_product.total_quantity == 15
    assert updated_product.available_quantity == 15
    assert updated_product.purchase_total_price == Decimal("162.50")
    assert updated_product.purchase_price_per_item == Decimal("12.50")

    assert purchase.quantity_purchase == 5
    assert purchase.purchase_price_per_item == Decimal("12.50")
    assert purchase.purchase_total_price == Decimal("62.50")
    assert purchase.supplier_id == supplier.id


def test_sale_updates_stock_revenue_and_profit(
    client, auth_tokens, financial_dependencies
):
    product, _supplier, customer = financial_dependencies

    response = client.post(
        f"/api/product/{product.id}/sale",
        headers=_manager_headers(auth_tokens),
        json={
            "customer": customer.id,
            "quantity": 3,
            "selling_price_per_item": "20.00",
            "selling_total_price": "60.00",
            "sale_date": "2026-11-18",
        },
    )

    assert response.status_code == 201

    db_session.expire_all()
    updated_product = db_session.query(Product).filter_by(id=product.id).one()
    sale = db_session.query(SaleHistory).filter_by(product_id=product.id).one()

    assert updated_product.available_quantity == 7
    assert updated_product.sold_quantity == 3
    assert updated_product.selling_quantity == 3
    assert updated_product.selling_total_price == Decimal("60.00")

    assert sale.quantity_sold == 3
    assert sale.selling_total_price == Decimal("60.00")
    assert sale.profit == Decimal("30.00")


def test_sale_calculates_profit_to_cent_precision(
    client, auth_tokens, financial_dependencies
):
    product, _supplier, customer = financial_dependencies
    product.purchase_price_per_item = Decimal("10.01")
    db_session.commit()

    response = client.post(
        f"/api/product/{product.id}/sale",
        headers=_manager_headers(auth_tokens),
        json={
            "customer": customer.id,
            "quantity": 3,
            "selling_price_per_item": "19.99",
            "selling_total_price": "59.97",
            "sale_date": "2026-11-18",
        },
    )

    assert response.status_code == 201

    db_session.expire_all()
    sale = db_session.query(SaleHistory).filter_by(product_id=product.id).one()

    assert sale.selling_total_price == Decimal("59.97")
    assert sale.profit == Decimal("29.94")


def test_sale_rejects_quantity_above_available_stock_without_changing_stock(
    client, auth_tokens, financial_dependencies
):
    product, _supplier, customer = financial_dependencies

    response = client.post(
        f"/api/product/{product.id}/sale",
        headers=_manager_headers(auth_tokens),
        json={
            "customer": customer.id,
            "quantity": 11,
            "selling_price_per_item": "20.00",
            "selling_total_price": "220.00",
            "sale_date": "2026-11-18",
        },
    )

    assert response.status_code == 400

    db_session.expire_all()
    updated_product = db_session.query(Product).filter_by(id=product.id).one()

    assert updated_product.available_quantity == 10
    assert updated_product.sold_quantity == 0
    assert updated_product.selling_total_price == Decimal("0.00")
    assert db_session.query(SaleHistory).filter_by(product_id=product.id).count() == 0
