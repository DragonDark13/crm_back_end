import io
import unittest
from unittest.mock import patch

from flask import Flask

from services.product_import_routes import product_import_bp


class ProductPurchaseImportApiTests(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.register_blueprint(product_import_bp, url_prefix="/api")
        self.client = app.test_client()

    def test_requires_csv_file(self):
        response = self.client.post("/api/imports/products/purchases")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Оберіть CSV-файл", response.get_json()["error"])

    def test_rejects_non_csv_file(self):
        response = self.client.post(
            "/api/imports/products/purchases",
            data={"file": (io.BytesIO(b"not csv"), "purchases.xlsx")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("лише файли", response.get_json()["error"])

    @patch("services.product_import_routes.load_products_from_csv")
    def test_imports_uploaded_csv(self, import_mock):
        import_mock.return_value = {
            "status": "imported",
            "file_name": "purchases.csv",
            "rows_imported": 3,
        }

        response = self.client.post(
            "/api/imports/products/purchases",
            data={"file": (io.BytesIO(b"csv content"), "purchases.csv")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["rows_imported"], 3)
        import_mock.assert_called_once()

    @patch("services.product_import_routes.load_products_from_csv")
    def test_returns_conflict_for_previously_imported_file(self, import_mock):
        import_mock.return_value = {
            "status": "already_imported",
            "file_name": "purchases.csv",
            "rows_imported": 3,
        }

        response = self.client.post(
            "/api/imports/products/purchases",
            data={"file": (io.BytesIO(b"same csv"), "purchases.csv")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("уже імпортовано", response.get_json()["error"])


    @patch("services.product_import_routes.preview_products_from_csv")
    def test_previews_uploaded_csv(self, preview_mock):
        preview_mock.return_value = {
            "status": "preview",
            "file_name": "new-stock.csv",
            "rows_total": 5,
            "existing_product_rows": 3,
            "new_product_rows": 2,
            "existing_products_count": 2,
            "existing_product_names": ["Товар А", "Товар Б"],
            "new_products_count": 1,
            "new_product_names": ["Новий товар"],
            "rows_to_import": 4,
            "duplicate_rows": 1,
        }

        response = self.client.post(
            "/api/imports/products/purchases/preview",
            data={"file": (io.BytesIO(b"csv content"), "new-stock.csv")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["new_products_count"], 1)
        self.assertEqual(response.get_json()["existing_product_rows"], 3)
        self.assertEqual(
            response.get_json()["existing_product_names"],
            ["Товар А", "Товар Б"],
        )
        self.assertEqual(response.get_json()["duplicate_rows"], 1)
        self.assertEqual(response.get_json()["rows_to_import"], 4)
        preview_mock.assert_called_once()

    @patch("services.product_import_routes.preview_products_from_csv")
    def test_preview_returns_conflict_for_previously_imported_file(self, preview_mock):
        preview_mock.return_value = {
            "status": "already_imported",
            "file_name": "old-name.csv",
            "rows_imported": 5,
        }

        response = self.client.post(
            "/api/imports/products/purchases/preview",
            data={"file": (io.BytesIO(b"same csv"), "renamed.csv")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("уже імпортовано", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
