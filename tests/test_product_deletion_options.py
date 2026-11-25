"""Regression tests for explicit product deletion modes."""

import importlib
import unittest

auth_module = importlib.import_module("test_auth")

from models import (  # noqa: E402
    Product,
    ProductAuditHistory,
    PurchaseHistory,
    SaleHistory,
    StockHistory,
    Supplier,
    db,
)
from postgreSQLConnect import db_session  # noqa: E402


class ProductDeletionOptionsTests(unittest.TestCase):
    def setUp(self):
        self.app_module = auth_module.crm_app_module
        db_session.remove()

        with self.app_module.app.app_context():
            db.drop_all()
            db.create_all()
            self.app_module.create_roles_and_users()

            supplier = Supplier(name="Product deletion test supplier")
            db.session.add(supplier)
            db.session.commit()
            self.supplier_id = supplier.id

        self.client = self.app_module.app.test_client()
        login = self.client.post(
            "/api/login",
            json={"username": "manager", "password": "test-manager-password"},
        )
        self.assertEqual(login.status_code, 200, login.get_json())
        self.headers = {"Authorization": f"Bearer {login.get_json()['token']}"}

    def tearDown(self):
        db_session.rollback()
        db_session.remove()

    def _create_product(self):
        response = self.client.post(
            "/api/add_new_product",
            headers=self.headers,
            json={
                "name": "Product to delete",
                "category_ids": [],
                "created_date": "2026-11-20",
                "product_description": "Deletion test",
                "available_quantity": 5,
                "purchase_price_per_item": "12.50",
                "purchase_total_price": "62.50",
                "selling_price_per_item": "20.00",
                "supplier_id": self.supplier_id,
            },
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()["id"]

    def test_default_mode_refuses_to_delete_product_with_history(self):
        product_id = self._create_product()

        response = self.client.delete(
            f"/api/product/{product_id}",
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 409, response.get_json())
        self.assertIsNotNone(db_session.query(Product).filter_by(id=product_id).one_or_none())
        self.assertEqual(db_session.query(PurchaseHistory).filter_by(product_id=product_id).count(), 1)
        self.assertEqual(db_session.query(StockHistory).filter_by(product_id=product_id).count(), 1)
        self.assertGreater(db_session.query(ProductAuditHistory).filter_by(product_id=product_id).count(), 0)

    def test_all_related_mode_deletes_product_and_its_product_history(self):
        product_id = self._create_product()

        response = self.client.delete(
            f"/api/product/{product_id}?mode=all_related",
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertIsNone(db_session.query(Product).filter_by(id=product_id).one_or_none())
        self.assertEqual(db_session.query(PurchaseHistory).filter_by(product_id=product_id).count(), 0)
        self.assertEqual(db_session.query(StockHistory).filter_by(product_id=product_id).count(), 0)
        self.assertEqual(db_session.query(SaleHistory).filter_by(product_id=product_id).count(), 0)
        self.assertEqual(db_session.query(ProductAuditHistory).filter_by(product_id=product_id).count(), 0)
        self.assertIsNotNone(db_session.query(Supplier).filter_by(id=self.supplier_id).one_or_none())

    def test_invalid_deletion_mode_is_rejected(self):
        product_id = self._create_product()

        response = self.client.delete(
            f"/api/product/{product_id}?mode=unknown",
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 400, response.get_json())
        self.assertIsNotNone(db_session.query(Product).filter_by(id=product_id).one_or_none())


if __name__ == "__main__":
    unittest.main()
