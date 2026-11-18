"""Integration tests for purchase and sale financial operations."""

import importlib
from datetime import datetime
from decimal import Decimal

import pytest

# Initialize the isolated SQLite database and Flask app used by backend tests.
auth_module = importlib.import_module("test_authorization")

from models import (  # noqa: E402
    Customer,
    PackagingMaterial,
    PackagingSaleHistory,
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
    db_session.query(PackagingSaleHistory).delete()
    db_session.query(SaleHistory).delete()
    db_session.query(PurchaseHistory).delete()
    db_session.query(PackagingMaterial).delete()
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
    product_id = product_id
    supplier_id = supplier_id

    response = client.post(
        f"/api/product/{product_id}/purchase",
        headers=_manager_headers(auth_tokens),
        json={
            "quantity": 5,
            "purchase_price_per_item": "12.50",
            "purchase_total_price": "62.50",
            "supplier_id": supplier_id,
            "purchase_date": "2026-11-18",
        },
    )

    assert response.status_code == 201

    db_session.expire_all()
    updated_product = db_session.query(Product).filter_by(id=product_id).one()
    purchase = db_session.query(PurchaseHistory).filter_by(product_id=product_id).one()

    assert updated_product.total_quantity == 15
    assert updated_product.available_quantity == 15
    assert updated_product.purchase_total_price == Decimal("162.50")
    assert updated_product.purchase_price_per_item == Decimal("12.50")

    assert purchase.quantity_purchase == 5
    assert purchase.purchase_price_per_item == Decimal("12.50")
    assert purchase.purchase_total_price == Decimal("62.50")
    assert purchase.supplier_id == supplier_id


def test_sale_updates_stock_revenue_and_profit(
    client, auth_tokens, financial_dependencies
):
    product, _supplier, customer = financial_dependencies
    product_id = product_id
    customer_id = customer_id

    response = client.post(
        f"/api/product/{product_id}/sale",
        headers=_manager_headers(auth_tokens),
        json={
            "customer": customer_id,
            "quantity": 3,
            "selling_price_per_item": "20.00",
            "selling_total_price": "60.00",
            "sale_date": "2026-11-18",
        },
    )

    assert response.status_code == 201

    db_session.expire_all()
    updated_product = db_session.query(Product).filter_by(id=product_id).one()
    sale = db_session.query(SaleHistory).filter_by(product_id=product_id).one()

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
    product_id = product_id
    customer_id = customer_id
    product.purchase_price_per_item = Decimal("10.01")
    db_session.commit()

    response = client.post(
        f"/api/product/{product_id}/sale",
        headers=_manager_headers(auth_tokens),
        json={
            "customer": customer_id,
            "quantity": 3,
            "selling_price_per_item": "19.99",
            "selling_total_price": "59.97",
            "sale_date": "2026-11-18",
        },
    )

    assert response.status_code == 201

    db_session.expire_all()
    sale = db_session.query(SaleHistory).filter_by(product_id=product_id).one()

    assert sale.selling_total_price == Decimal("59.97")
    assert sale.profit == Decimal("29.94")


def test_sale_rejects_quantity_above_available_stock_without_changing_stock(
    client, auth_tokens, financial_dependencies
):
    product, _supplier, customer = financial_dependencies
    product_id = product_id
    customer_id = customer_id

    response = client.post(
        f"/api/product/{product_id}/sale",
        headers=_manager_headers(auth_tokens),
        json={
            "customer": customer_id,
            "quantity": 11,
            "selling_price_per_item": "20.00",
            "selling_total_price": "220.00",
            "sale_date": "2026-11-18",
        },
    )

    assert response.status_code == 400

    db_session.expire_all()
    updated_product = db_session.query(Product).filter_by(id=product_id).one()

    assert updated_product.available_quantity == 10
    assert updated_product.sold_quantity == 0
    assert updated_product.selling_total_price == Decimal("0.00")
    assert db_session.query(SaleHistory).filter_by(product_id=product_id).count() == 0



def test_repeated_purchases_accumulate_purchase_cost_without_increasing_sales_revenue(
    client, auth_tokens, financial_dependencies
):
    product, supplier, _customer = financial_dependencies
    product_id = product_id
    supplier_id = supplier_id

    purchases = [
        {
            "quantity": 2,
            "purchase_price_per_item": "12.50",
            "purchase_total_price": "25.00",
            "supplier_id": supplier_id,
            "purchase_date": "2026-11-18",
        },
        {
            "quantity": 3,
            "purchase_price_per_item": "13.00",
            "purchase_total_price": "39.00",
            "supplier_id": supplier_id,
            "purchase_date": "2026-11-19",
        },
    ]

    for purchase_data in purchases:
        response = client.post(
            f"/api/product/{product_id}/purchase",
            headers=_manager_headers(auth_tokens),
            json=purchase_data,
        )
        assert response.status_code == 201

    db_session.expire_all()
    updated_product = db_session.query(Product).filter_by(id=product_id).one()
    purchase_history = (
        db_session.query(PurchaseHistory)
        .filter_by(product_id=product_id)
        .order_by(PurchaseHistory.id)
        .all()
    )

    assert updated_product.total_quantity == 15
    assert updated_product.available_quantity == 15
    assert updated_product.purchase_total_price == Decimal("164.00")
    assert updated_product.purchase_price_per_item == Decimal("13.00")
    assert updated_product.selling_total_price == Decimal("0.00")
    assert len(purchase_history) == 2
    assert [item.purchase_total_price for item in purchase_history] == [
        Decimal("25.00"),
        Decimal("39.00"),
    ]


def test_sequential_purchases_and_sale_keep_stock_and_financial_totals_consistent(
    client, auth_tokens, financial_dependencies
):
    product, supplier, customer = financial_dependencies

    first_purchase = client.post(
        f"/api/product/{product_id}/purchase",
        headers=_manager_headers(auth_tokens),
        json={
            "quantity": 2,
            "purchase_price_per_item": "12.50",
            "purchase_total_price": "25.00",
            "supplier_id": supplier.id,
            "purchase_date": "2026-11-18",
        },
    )
    second_purchase = client.post(
        f"/api/product/{product_id}/purchase",
        headers=_manager_headers(auth_tokens),
        json={
            "quantity": 3,
            "purchase_price_per_item": "13.00",
            "purchase_total_price": "39.00",
            "supplier_id": supplier.id,
            "purchase_date": "2026-11-19",
        },
    )

    assert first_purchase.status_code == 201
    assert second_purchase.status_code == 201

    sale_response = client.post(
        f"/api/product/{product_id}/sale",
        headers=_manager_headers(auth_tokens),
        json={
            "customer": customer_id,
            "quantity": 4,
            "selling_price_per_item": "20.00",
            "selling_total_price": "80.00",
            "sale_date": "2026-11-20",
        },
    )
    assert sale_response.status_code == 201

    db_session.expire_all()
    updated_product = db_session.query(Product).filter_by(id=product_id).one()
    sale = db_session.query(SaleHistory).filter_by(product_id=product_id).one()

    assert updated_product.total_quantity == 15
    assert updated_product.available_quantity == 11
    assert updated_product.sold_quantity == 4
    assert updated_product.purchase_total_price == Decimal("164.00")
    assert updated_product.selling_total_price == Decimal("80.00")
    assert sale.profit == Decimal("28.00")


def test_sale_profit_includes_packaging_cost_and_updates_packaging_stock(
    client, auth_tokens, financial_dependencies
):
    product, _supplier, customer = financial_dependencies
    product_id = product_id
    customer_id = customer_id
    product.purchase_price_per_item = Decimal("10.01")
    packaging = PackagingMaterial(
        name="Financial test packaging",
        total_quantity=10,
        available_quantity=10,
        purchase_price_per_unit=Decimal("1.50"),
        total_purchase_cost=Decimal("15.00"),
        available_stock_cost=Decimal("15.00"),
    )
    db_session.add(packaging)
    db_session.commit()
    packaging_id = packaging.id

    response = client.post(
        f"/api/product/{product_id}/sale",
        headers=_manager_headers(auth_tokens),
        json={
            "customer": customer_id,
            "quantity": 3,
            "selling_price_per_item": "19.99",
            "selling_total_price": "59.97",
            "packaging_id": packaging_id,
            "packaging_quantity": 2,
            "total_packaging_cost": "3.00",
            "sale_date": "2026-11-18",
        },
    )

    assert response.status_code == 201

    db_session.expire_all()
    sale = db_session.query(SaleHistory).filter_by(product_id=product_id).one()
    updated_packaging = db_session.query(PackagingMaterial).filter_by(id=packaging_id).one()
    packaging_history = db_session.query(PackagingSaleHistory).filter_by(sale_id=sale.id).one()

    assert sale.selling_total_price == Decimal("59.97")
    assert sale.profit == Decimal("26.94")
    assert sale.total_packaging_cost == 3.0
    assert updated_packaging.available_quantity == 8
    assert updated_packaging.available_stock_cost == Decimal("12.00")
    assert packaging_history.packaging_quantity == 2
    assert packaging_history.total_packaging_cost == Decimal("3.00")
