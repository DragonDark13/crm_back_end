"""Regression tests for product name updates and uniqueness."""

import importlib
import unittest

auth_module = importlib.import_module("test_auth")

from models import Category, Product, ProductAuditHistory, Supplier, db, product_categories_table  # noqa: E402
from postgreSQLConnect import db_session  # noqa: E402


class ProductNameValidationTests(unittest.TestCase):
    def setUp(self):
        self.app_module = auth_module.crm_app_module
        db_session.remove()

        with self.app_module.app.app_context():
            db.drop_all()
            db.create_all()
            self.app_module.create_roles_and_users()

            supplier = Supplier(name="Product name test supplier")
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

    def _create_payload(self, name):
        return {
            "name": name,
            "category_ids": [],
            "created_date": "2026-11-20",
            "product_description": "Product name validation test",
            "available_quantity": 5,
            "purchase_price_per_item": "12.50",
            "purchase_total_price": "62.50",
            "selling_price_per_item": "20.00",
            "supplier_id": self.supplier_id,
        }

    def _create_product(self, name):
        response = self.client.post(
            "/api/add_new_product",
            headers=self.headers,
            json=self._create_payload(name),
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()["id"]

    def _update_payload(self, name):
        return {
            "name": name,
            "created_date": "2026-11-20",
            "available_quantity": 5,
            "purchase_price_per_item": "12.50",
            "purchase_total_price": "62.50",
            "selling_price_per_item": "20.00",
            "category_ids": [],
        }

    def test_update_saves_name_and_audits_old_and_new_values(self):
        product_id = self._create_product("Old product name")

        response = self.client.put(
            f"/api/product/{product_id}",
            headers=self.headers,
            json=self._update_payload("New product name"),
        )

        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["name"], "New product name")

        db_session.expire_all()
        product = db_session.query(Product).filter_by(id=product_id).one()
        audit = db_session.query(ProductAuditHistory).filter_by(
            product_id=product_id,
            field_name="name",
        ).one()
        self.assertEqual(product.name, "New product name")
        self.assertEqual(audit.old_value, "Old product name")
        self.assertEqual(audit.new_value, "New product name")

    def test_update_audits_purchase_total_price_changes(self):
        product_id = self._create_product("Purchase total audit")

        payload = self._update_payload("Purchase total audit")
        payload["purchase_total_price"] = "75.00"
        response = self.client.put(
            f"/api/product/{product_id}",
            headers=self.headers,
            json=payload,
        )

        self.assertEqual(response.status_code, 200, response.get_json())
        db_session.expire_all()
        audit = db_session.query(ProductAuditHistory).filter_by(
            product_id=product_id,
            field_name="purchase_total_price",
        ).one()
        self.assertEqual(audit.old_value, "62.50")
        self.assertEqual(audit.new_value, "75.00")

    def test_update_clears_categories_when_empty_list_is_submitted(self):
        category = Category(name="Category to clear")
        db.session.add(category)
        db.session.commit()
        product_id = self._create_product("Product with category")

        db_session.execute(
            product_categories_table.insert().values(
                product_id=product_id,
                category_id=category.id,
            )
        )
        db_session.commit()

        response = self.client.put(
            f"/api/product/{product_id}",
            headers=self.headers,
            json=self._update_payload("Product with category"),
        )

        self.assertEqual(response.status_code, 200, response.get_json())
        remaining_links = db_session.execute(
            product_categories_table.select().where(
                product_categories_table.c.product_id == product_id
            )
        ).fetchall()
        self.assertEqual(remaining_links, [])

    def test_create_rejects_name_duplicate_ignoring_case_and_outer_spaces(self):
        self._create_product("Whole milk")

        response = self.client.post(
            "/api/add_new_product",
            headers=self.headers,
            json=self._create_payload("  WHOLE MILK  "),
        )

        self.assertEqual(response.status_code, 409, response.get_json())

    def test_update_rejects_name_used_by_another_product(self):
        product_id = self._create_product("First product")
        self._create_product("Second product")

        response = self.client.put(
            f"/api/product/{product_id}",
            headers=self.headers,
            json=self._update_payload(" second PRODUCT "),
        )

        self.assertEqual(response.status_code, 409, response.get_json())

        db_session.expire_all()
        self.assertEqual(
            db_session.query(Product).filter_by(id=product_id).one().name,
            "First product",
        )

    def test_update_rejects_empty_name(self):
        product_id = self._create_product("Valid product")

        response = self.client.put(
            f"/api/product/{product_id}",
            headers=self.headers,
            json=self._update_payload("   "),
        )

        self.assertEqual(response.status_code, 400, response.get_json())

    def test_update_rejects_name_longer_than_255_characters(self):
        product_id = self._create_product("Valid product")

        response = self.client.put(
            f"/api/product/{product_id}",
            headers=self.headers,
            json=self._update_payload("x" * 256),
        )

        self.assertEqual(response.status_code, 400, response.get_json())


if __name__ == "__main__":
    unittest.main()
