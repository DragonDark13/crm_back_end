"""Regression tests for atomic product creation."""

import importlib
import unittest
from decimal import Decimal

from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError

auth_module = importlib.import_module("test_auth")

from models import (  # noqa: E402
    Product,
    PurchaseHistory,
    StockHistory,
    Supplier,
    db,
)
from postgreSQLConnect import db_session  # noqa: E402


class ProductCreationAtomicityTests(unittest.TestCase):
    def setUp(self):
        self.app_module = auth_module.crm_app_module
        db_session.remove()

        with self.app_module.app.app_context():
            db.drop_all()
            db.create_all()
            self.app_module.create_roles_and_users()

            supplier = Supplier(name="Product creation test supplier")
            db.session.add(supplier)
            db.session.commit()
            self.supplier_id = supplier.id

        login = self.app_module.app.test_client().post(
            "/api/login",
            json={"username": "manager", "password": "test-manager-password"},
        )
        self.assertEqual(login.status_code, 200, login.get_json())
        self.headers = {"Authorization": f"Bearer {login.get_json()['token']}"}
        self.client = self.app_module.app.test_client()

    def tearDown(self):
        db_session.rollback()
        db_session.remove()

    def _payload(self):
        return {
            "name": "Atomic product creation",
            "category_ids": [],
            "created_date": "2026-11-20",
            "product_description": "Product creation transaction test",
            "available_quantity": 5,
            "purchase_price_per_item": "12.50",
            "purchase_total_price": "62.50",
            "selling_price_per_item": "20.00",
            "supplier_id": self.supplier_id,
        }

    def test_product_and_histories_are_created_together(self):
        response = self.client.post(
            "/api/add_new_product",
            headers=self.headers,
            json=self._payload(),
        )

        self.assertEqual(response.status_code, 201, response.get_json())
        product_id = response.get_json()["id"]

        db_session.expire_all()
        product = db_session.query(Product).filter_by(id=product_id).one()
        purchase = db_session.query(PurchaseHistory).filter_by(product_id=product_id).one()
        stock = db_session.query(StockHistory).filter_by(product_id=product_id).one()

        self.assertEqual(product.total_quantity, 5)
        self.assertEqual(product.available_quantity, 5)
        self.assertEqual(product.purchase_total_price, Decimal("62.50"))
        self.assertEqual(purchase.quantity_purchase, 5)
        self.assertEqual(stock.change_amount, 5)

    def test_product_creation_rolls_back_when_purchase_history_write_fails(self):
        session = db_session()
        def fail_purchase_history(session, flush_context, instances):
            if any(isinstance(item, PurchaseHistory) for item in session.new):
                raise SQLAlchemyError("simulated purchase history write failure")

        event.listen(session, "before_flush", fail_purchase_history)
        try:
            response = self.client.post(
                "/api/add_new_product",
                headers=self.headers,
                json=self._payload(),
            )
        finally:
            event.remove(session, "before_flush", fail_purchase_history)

        self.assertEqual(response.status_code, 500)
        db_session.expire_all()
        self.assertEqual(
            db_session.query(Product).filter_by(name="Atomic product creation").count(),
            0,
        )
        self.assertEqual(db_session.query(PurchaseHistory).count(), 0)
        self.assertEqual(db_session.query(StockHistory).count(), 0)


if __name__ == "__main__":
    unittest.main()
