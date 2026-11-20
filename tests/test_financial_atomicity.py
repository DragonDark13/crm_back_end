"""Regression tests for atomic purchase and sale transactions."""

import importlib
from decimal import Decimal

import pytest
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError

auth_module = importlib.import_module("test_auth")

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
from postgreSQLConnect import db_session  # noqa: E402


@pytest.fixture
def financial_setup():
    app_module = auth_module.crm_app_module
    db_session.remove()

    with app_module.app.app_context():
        db.drop_all()
        db.create_all()
        app_module.create_roles_and_users()

        supplier = Supplier(name="Atomicity test supplier")
        customer = Customer(name="Atomicity test customer")
        product = Product(
            name="Atomicity test product",
            supplier=supplier,
            total_quantity=10,
            available_quantity=10,
            sold_quantity=0,
            purchase_total_price=Decimal("100.00"),
            purchase_price_per_item=Decimal("10.00"),
            selling_total_price=Decimal("0.00"),
            selling_price_per_item=Decimal("20.00"),
            selling_quantity=0,
            article="ATOMIC-0001",
            product_description="Atomicity integration test",
        )
        packaging = PackagingMaterial(
            name="Atomicity test packaging",
            total_quantity=10,
            available_quantity=10,
            purchase_price_per_unit=Decimal("1.50"),
            total_purchase_cost=Decimal("15.00"),
            available_stock_cost=Decimal("15.00"),
        )
        db.session.add_all([supplier, customer, product, packaging])
        db.session.commit()

        product_id = product.id
        supplier_id = supplier.id
        customer_id = customer.id
        packaging_id = packaging.id

    login = app_module.app.test_client().post(
        "/api/login",
        json={"username": "manager", "password": "test-manager-password"},
    )
    assert login.status_code == 200, login.get_json()
    token = login.get_json()["token"]

    yield {
        "app": app_module.app,
        "client": app_module.app.test_client(),
        "product_id": product_id,
        "supplier_id": supplier_id,
        "customer_id": customer_id,
        "packaging_id": packaging_id,
        "headers": {"Authorization": f"Bearer {token}"},
    }

    db_session.rollback()
    db_session.remove()


def _fail_when_model_added(model_class):
    def fail_before_flush(session, flush_context, instances):
        if any(isinstance(item, model_class) for item in session.new):
            raise SQLAlchemyError("simulated history write failure")
    return fail_before_flush


def test_purchase_rolls_back_stock_and_cost_when_history_write_fails(financial_setup):
    session = db_session()
    handler = _fail_when_model_added(PurchaseHistory)
    event.listen(session, "before_flush", handler)
    try:
        response = financial_setup["client"].post(
            f"/api/product/{financial_setup['product_id']}/purchase",
            headers=financial_setup["headers"],
            json={
                "quantity": 5,
                "purchase_price_per_item": "12.50",
                "purchase_total_price": "62.50",
                "supplier_id": financial_setup["supplier_id"],
                "purchase_date": "2026-11-18",
            },
        )
    finally:
        event.remove(session, "before_flush", handler)

    assert response.status_code == 500
    db_session.expire_all()
    product = db_session.query(Product).filter_by(id=financial_setup["product_id"]).one()
    assert product.total_quantity == 10
    assert product.available_quantity == 10
    assert product.purchase_total_price == Decimal("100.00")
    assert product.purchase_price_per_item == Decimal("10.00")
    assert db_session.query(PurchaseHistory).filter_by(product_id=product.id).count() == 0


def test_sale_rolls_back_stock_and_revenue_when_history_write_fails(financial_setup):
    session = db_session()
    handler = _fail_when_model_added(SaleHistory)
    event.listen(session, "before_flush", handler)
    try:
        response = financial_setup["client"].post(
            f"/api/product/{financial_setup['product_id']}/sale",
            headers=financial_setup["headers"],
            json={
                "customer": financial_setup["customer_id"],
                "quantity": 3,
                "selling_price_per_item": "20.00",
                "selling_total_price": "60.00",
                "sale_date": "2026-11-18",
            },
        )
    finally:
        event.remove(session, "before_flush", handler)

    assert response.status_code == 500
    db_session.expire_all()
    product = db_session.query(Product).filter_by(id=financial_setup["product_id"]).one()
    assert product.available_quantity == 10
    assert product.sold_quantity == 0
    assert product.selling_quantity == 0
    assert product.selling_total_price == Decimal("0.00")
    assert db_session.query(SaleHistory).filter_by(product_id=product.id).count() == 0


def test_sale_rolls_back_product_and_packaging_when_packaging_history_fails(financial_setup):
    session = db_session()
    handler = _fail_when_model_added(PackagingSaleHistory)
    event.listen(session, "before_flush", handler)
    try:
        response = financial_setup["client"].post(
            f"/api/product/{financial_setup['product_id']}/sale",
            headers=financial_setup["headers"],
            json={
                "customer": financial_setup["customer_id"],
                "quantity": 3,
                "selling_price_per_item": "20.00",
                "selling_total_price": "60.00",
                "packaging_id": financial_setup["packaging_id"],
                "packaging_quantity": 2,
                "total_packaging_cost": "3.00",
                "sale_date": "2026-11-18",
            },
        )
    finally:
        event.remove(session, "before_flush", handler)

    assert response.status_code == 500
    db_session.expire_all()
    product = db_session.query(Product).filter_by(id=financial_setup["product_id"]).one()
    packaging = db_session.query(PackagingMaterial).filter_by(id=financial_setup["packaging_id"]).one()

    assert product.available_quantity == 10
    assert product.sold_quantity == 0
    assert product.selling_quantity == 0
    assert product.selling_total_price == Decimal("0.00")
    assert packaging.available_quantity == 10
    assert packaging.available_stock_cost == Decimal("15.00")
    assert db_session.query(SaleHistory).filter_by(product_id=product.id).count() == 0
    assert db_session.query(PackagingSaleHistory).count() == 0
