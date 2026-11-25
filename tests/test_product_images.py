"""Regression tests for product image upload, display, and deletion."""

import importlib
import io
import unittest

auth_module = importlib.import_module("test_auth")

from models import ProductImage, Supplier, db  # noqa: E402
from postgreSQLConnect import db_session  # noqa: E402


class ProductImageTests(unittest.TestCase):
    def setUp(self):
        self.app_module = auth_module.crm_app_module
        db_session.remove()

        with self.app_module.app.app_context():
            db.drop_all()
            db.create_all()
            self.app_module.create_roles_and_users()
            supplier = Supplier(name="Product image test supplier")
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

        response = self.client.post(
            "/api/add_new_product",
            headers=self.headers,
            json={
                "name": "Product with image",
                "category_ids": [],
                "created_date": "2026-11-20",
                "product_description": "Image test",
                "available_quantity": 5,
                "purchase_price_per_item": "12.50",
                "purchase_total_price": "62.50",
                "selling_price_per_item": "20.00",
                "supplier_id": self.supplier_id,
            },
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        self.product_id = response.get_json()["id"]

    def tearDown(self):
        db_session.rollback()
        db_session.remove()

    def test_upload_and_display_product_image(self):
        response = self.client.post(
            f"/api/product/{self.product_id}/images",
            headers=self.headers,
            data={"images": (io.BytesIO(b"\x89PNG\r\n\x1a\nimage-data"), "product.png")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 201, response.get_json())
        image = response.get_json()["images"][0]
        self.assertEqual(image["mime_type"], "image/png")
        self.assertEqual(image["file_name"], "product.png")

        product_response = self.client.get(
            f"/api/product/{self.product_id}",
            headers=self.headers,
        )
        self.assertEqual(product_response.status_code, 200)
        self.assertEqual(product_response.get_json()["images"][0]["id"], image["id"])

        image_response = self.client.get(image["url"], headers=self.headers)
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response.mimetype, "image/png")
        self.assertTrue(image_response.data.startswith(b"\x89PNG"))

    def test_unsupported_file_is_rejected(self):
        response = self.client.post(
            f"/api/product/{self.product_id}/images",
            headers=self.headers,
            data={"images": (io.BytesIO(b"not-an-image"), "document.txt")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(db_session.query(ProductImage).count(), 0)

    def test_product_deletion_cascades_only_its_images(self):
        upload = self.client.post(
            f"/api/product/{self.product_id}/images",
            headers=self.headers,
            data={"images": (io.BytesIO(b"\\xff\\xd8\\xffimage-data"), "product.jpg")},
            content_type="multipart/form-data",
        )
        self.assertEqual(upload.status_code, 201)
        image_id = upload.get_json()["images"][0]["id"]

        response = self.client.delete(
            f"/api/product/{self.product_id}?mode=all_related",
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertIsNone(db_session.query(ProductImage).filter_by(id=image_id).one_or_none())

    def test_image_can_be_deleted_without_touching_product_history(self):
        upload = self.client.post(
            f"/api/product/{self.product_id}/images",
            headers=self.headers,
            data={"images": (io.BytesIO(b"\xff\xd8\xffimage-data"), "product.jpg")},
            content_type="multipart/form-data",
        )
        self.assertEqual(upload.status_code, 201)
        image_id = upload.get_json()["images"][0]["id"]

        response = self.client.delete(
            f"/api/product/{self.product_id}/images/{image_id}",
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(db_session.query(ProductImage).filter_by(id=image_id).one_or_none())
        self.assertEqual(db_session.query(ProductImage).filter_by(product_id=self.product_id).count(), 0)


if __name__ == "__main__":
    unittest.main()
