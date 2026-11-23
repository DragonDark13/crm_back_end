"""Regression tests for the inventory reconciliation date."""

import importlib
import unittest
from datetime import date

auth_module = importlib.import_module("test_auth")

from models import Product, StockHistory, db  # noqa: E402
from postgreSQLConnect import db_session  # noqa: E402


class ProductInventoryDateTests(unittest.TestCase):
    def setUp(self):
        self.app_module = auth_module.crm_app_module
        db_session.remove()

        with self.app_module.app.app_context():
            db.drop_all()
            db.create_all()
            self.app_module.create_roles_and_users()

            product = Product(
                name="Inventory date test product",
                article="INV-DATE-01",
                total_quantity=10,
                available_quantity=10,
                reserved_quantity=0,
                product_description="",
            )
            db.session.add(product)
            db.session.commit()
            self.product_id = product.id

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

    def test_inventory_saves_reconciliation_date_separately_from_recorded_timestamp(self):
        response = self.client.post(
            f"/api/product/{self.product_id}/inventory",
            headers=self.headers,
            json={
                "actual_quantity": 8,
                "reason": "Перерахунок на ярмарку",
                "inventory_date": "2026-11-20",
            },
        )

        self.assertEqual(response.status_code, 200, response.get_json())
        stock_history = response.get_json()["stock_history"]
        self.assertEqual(stock_history["inventory_date"], "2026-11-20")

        db_session.expire_all()
        record = db_session.query(StockHistory).filter_by(
            product_id=self.product_id,
            change_type="inventory",
        ).one()
        self.assertEqual(record.inventory_date, date(2026, 11, 20))
        self.assertIsNotNone(record.timestamp)

    def test_inventory_rejects_invalid_reconciliation_date_without_changing_stock(self):
        response = self.client.post(
            f"/api/product/{self.product_id}/inventory",
            headers=self.headers,
            json={"actual_quantity": 8, "inventory_date": "2026-02-31"},
        )

        self.assertEqual(response.status_code, 400)
        db_session.expire_all()
        product = db_session.query(Product).filter_by(id=self.product_id).one()
        self.assertEqual(product.available_quantity, 10)
        self.assertEqual(
            db_session.query(StockHistory).filter_by(product_id=self.product_id).count(),
            0,
        )


if ( __name__ == "__main__" ):
    unittest.main()
