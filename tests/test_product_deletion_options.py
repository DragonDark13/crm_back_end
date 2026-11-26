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

    def test_default_mode_archives_product_with_history(self):
        product_id = self._create_product()

        response = self.client.delete(
            f"/api/product/{product_id}",
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200, response.get_json())
        product = db_session.query(Product).filter_by(id=product_id).one_or_none()
        self.assertIsNotNone(product)
        self.assertTrue(product.is_archived)
        self.assertEqual(db_session.query(PurchaseHistory).filter_by(product_id=product_id).count(), 1)
        self.assertEqual(db_session.query(StockHistory).filter_by(product_id=product_id).count(), 1)
        self.assertGreater(db_session.query(ProductAuditHistory).filter_by(product_id=product_id).count(), 0)

    def test_all_related_mode_archives_without_deleting_history(self):
        product_id = self._create_product()

        response = self.client.delete(
            f"/api/product/{product_id}?mode=all_related",
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200, response.get_json())
        product = db_session.query(Product).filter_by(id=product_id).one_or_none()
        self.assertIsNotNone(product)
        self.assertTrue(product.is_archived)
        self.assertEqual(db_session.query(PurchaseHistory).filter_by(product_id=product_id).count(), 1)
        self.assertEqual(db_session.query(StockHistory).filter_by(product_id=product_id).count(), 1)
        self.assertEqual(db_session.query(SaleHistory).filter_by(product_id=product_id).count(), 0)
        self.assertGreater(db_session.query(ProductAuditHistory).filter_by(product_id=product_id).count(), 0)
        self.assertIsNotNone(db_session.query(Supplier).filter_by(id=self.supplier_id).one_or_none())

    def test_archived_product_can_be_restored_without_losing_history(self):
        product_id = self._create_product()
        archive_response = self.client.delete(
            f"/api/product/{product_id}",
            headers=self.headers,
        )
        self.assertEqual(archive_response.status_code, 200, archive_response.get_json())

        catalog_response = self.client.get("/api/get_all_products/", headers=self.headers)
        self.assertEqual(catalog_response.status_code, 200, catalog_response.get_json())
        self.assertNotIn(product_id, [item["id"] for item in catalog_response.get_json()])

        restore_response = self.client.post(
            f"/api/product/{product_id}/restore",
            headers=self.headers,
        )
        self.assertEqual(restore_response.status_code, 200, restore_response.get_json())

        product = db_session.query(Product).filter_by(id=product_id).one()
        self.assertFalse(product.is_archived)
        self.assertEqual(db_session.query(PurchaseHistory).filter_by(product_id=product_id).count(), 1)
        self.assertEqual(db_session.query(StockHistory).filter_by(product_id=product_id).count(), 1)

    def test_inventory_audit_records_previous_and_actual_quantity(self):
        product_id = self._create_product()

        response = self.client.post(
            f"/api/product/{product_id}/inventory",
            headers=self.headers,
            json={"actual_quantity": 4, "reason": "Inventory audit regression"},
        )

        self.assertEqual(response.status_code, 200, response.get_json())
        db_session.expire_all()
        audit = db_session.query(ProductAuditHistory).filter_by(
            product_id=product_id,
            action="inventory",
            field_name="available_quantity",
        ).one()
        self.assertEqual(audit.old_value, "5")
        self.assertEqual(audit.new_value, "4")

        stock_record = db_session.query(StockHistory).filter_by(
            product_id=product_id,
            change_type="inventory",
        ).one()
        self.assertEqual(stock_record.quantity_before, 5)
        self.assertEqual(stock_record.quantity_after, 4)

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
