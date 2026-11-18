"""Integration tests for atomic product creation and purchase history."""

import importlib

import pytest

# Reuse the isolated SQLite database initialized by the authorization tests.
# app.py imports postgreSQLConnect during that setup, so both test modules
# must share the same engine and database file.
importlib.import_module("test_authorization")

from models import (  # noqa: E402
    Category,
    Product,
    PurchaseHistory,
    StockHistory,
    Supplier,
    db,
    product_categories_table,
)
from postgreSQLConnect import db_session, engine  # noqa: E402
from services.product_service import ProductService  # noqa: E402

db.metadata.create_all(
    bind=engine,
    tables=[
        Supplier.__table__,
        Category.__table__,
        Product.__table__,
        product_categories_table,
        PurchaseHistory.__table__,
        StockHistory.__table__,
    ],
)

@pytest.fixture(autouse=True)
def clean_database():
    db_session.remove()
    db_session.query(StockHistory).delete()
    db_session.query(PurchaseHistory).delete()
    db_session.execute(product_categories_table.delete())
    db_session.query(Product).delete()
    db_session.query(Category).delete()
    db_session.query(Supplier).delete()
    db_session.commit()
    yield
    db_session.rollback()
    db_session.remove()


@pytest.fixture
def product_dependencies():
    supplier = Supplier(name="Test supplier")
    category = Category(name="Test category")
    db_session.add_all([supplier, category])
    db_session.commit()
    return supplier, category


def _product_data(supplier_id, category_id):
    return {
        "name": "Test product",
        "category_ids": [category_id],
        "created_date": "2026-11-18",
        "available_quantity": 5,
        "purchase_price_per_item": "12.50",
        "purchase_total_price": "62.50",
        "supplier_id": supplier_id,
        "selling_price_per_item": "20.00",
        "product_description": "Created by integration test",
    }


def test_create_product_persists_product_and_both_history_records(product_dependencies):
    supplier, category = product_dependencies

    result, status_code = ProductService.create_product(
        _product_data(supplier.id, category.id)
    )

    assert status_code == 201
    product = db_session.query(Product).filter_by(id=result["id"]).one()
    purchase = db_session.query(PurchaseHistory).filter_by(product_id=product.id).one()
    stock = db_session.query(StockHistory).filter_by(product_id=product.id).one()

    assert product.name == "Test product"
    assert product.supplier_id == supplier.id
    assert [item.id for item in product.categories] == [category.id]
    assert product.total_quantity == 5
    assert product.available_quantity == 5
    assert float(product.purchase_price_per_item) == 12.50
    assert float(product.purchase_total_price) == 62.50

    assert purchase.supplier_id == supplier.id
    assert purchase.quantity_purchase == 5
    assert purchase.purchase_date == date(2026, 11, 18)
    assert float(purchase.purchase_price_per_item) == 12.50
    assert float(purchase.purchase_total_price) == 62.50

    assert stock.change_amount == 5
    assert stock.change_type == "create"


def test_create_product_returns_404_when_supplier_does_not_exist(product_dependencies):
    _supplier, category = product_dependencies

    result, status_code = ProductService.create_product(
        _product_data(999999, category.id)
    )

    assert status_code == 404
    assert result == {"error": "Supplier not found"}
    assert db_session.query(Product).count() == 0
    assert db_session.query(PurchaseHistory).count() == 0
    assert db_session.query(StockHistory).count() == 0


def test_create_product_returns_404_when_category_does_not_exist(product_dependencies):
    supplier, _category = product_dependencies

    result, status_code = ProductService.create_product(
        _product_data(supplier.id, 999999)
    )

    assert status_code == 404
    assert result == {"error": "Some categories were not found"}
    assert db_session.query(Product).count() == 0
    assert db_session.query(PurchaseHistory).count() == 0
    assert db_session.query(StockHistory).count() == 0


def test_create_product_rolls_back_all_records_when_commit_fails(
    product_dependencies, monkeypatch
):
    supplier, category = product_dependencies

    def fail_commit():
        raise RuntimeError("Simulated commit failure")

    monkeypatch.setattr(db_session, "commit", fail_commit)

    result, status_code = ProductService.create_product(
        _product_data(supplier.id, category.id)
    )

    assert status_code == 500
    assert "Simulated commit failure" in result["error"]
    assert db_session.query(Product).count() == 0
    assert db_session.query(PurchaseHistory).count() == 0
    assert db_session.query(StockHistory).count() == 0


def test_create_product_rejects_missing_required_purchase_fields(product_dependencies):
    supplier, category = product_dependencies
    data = _product_data(supplier.id, category.id)
    del data["purchase_total_price"]

    result, status_code = ProductService.create_product(data)

    assert status_code == 400
    assert "purchase_total_price" in result["error"]
    assert db_session.query(Product).count() == 0
