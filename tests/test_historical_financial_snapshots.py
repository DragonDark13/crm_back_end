"""Regression tests for immutable historical cost and profit snapshots."""

import importlib
import unittest
from decimal import Decimal
from datetime import datetime

auth_module = importlib.import_module("test_auth")

from postgreSQLConnect import db_session  # noqa: E402

from models import (  # noqa: E402
    Customer,
    GiftSet,
    GiftSetProduct,
    GiftSetSalesHistory,
    Product,
    SaleHistory,
    StockHistory,
    db,
)


class HistoricalFinancialSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.app_module = auth_module.crm_app_module
        db_session.remove()
        with self.app_module.app.app_context():
            db.drop_all()
            db.create_all()
            self.app_module.create_roles_and_users()

            product = Product(
                name="Historical snapshot product",
                total_quantity=10,
                available_quantity=8,
                reserved_quantity=0,
                sold_quantity=2,
                purchase_price_per_item=Decimal("8.000"),
                selling_price_per_item=Decimal("20.00"),
                article="SNAPSHOT-001",
                product_description="Financial snapshot test",
            )
            customer = Customer(name="Historical snapshot customer")
            db.session.add_all([product, customer])
            db.session.flush()

            self.product_id = product.id
            self.customer_id = customer.id

            db.session.add(SaleHistory(
                product_id=product.id,
                customer_id=customer.id,
                quantity_sold=2,
                selling_price_per_item=Decimal("20.00"),
                selling_total_price=Decimal("40.00"),
                sale_date=datetime(2026, 11, 20, 12, 0),
                profit=Decimal("12.00"),
            ))
            db.session.commit()

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
        with self.app_module.app.app_context():
            db.session.remove()

    def test_product_sale_profit_is_not_recomputed_from_current_product_cost(self):
        with self.app_module.app.app_context():
            product = db.session.get(Product, self.product_id)
            product.purchase_price_per_item = Decimal("99.000")
            db.session.commit()

        response = self.client.get("/api/get_all_sales_history", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.get_json())

        sale = next(item for item in response.get_json() if item["type"] == "product")
        self.assertEqual(sale["cost_price"], "28.00")
        self.assertEqual(sale["profit"], "12.00")

    def test_gift_set_sale_keeps_cost_and_profit_after_product_price_change(self):
        with self.app_module.app.app_context():
            product = db.session.get(Product, self.product_id)
            product.available_quantity = 0
            product.reserved_quantity = 2

            gift_set = GiftSet(
                name="Historical snapshot gift set",
                total_price=16.0,
                gift_selling_price=25.0,
                is_sold=False,
            )
            db.session.add(gift_set)
            db.session.flush()
            db.session.add(GiftSetProduct(
                gift_set_id=gift_set.id,
                product_id=product.id,
                quantity=2,
            ))
            db.session.commit()
            gift_set_id = gift_set.id

        response = self.client.post(
            f"/api/sell_gift_set/{gift_set_id}",
            headers=self.headers,
            json={"customer_id": self.customer_id, "selling_price": "25.00"},
        )
        self.assertEqual(response.status_code, 200, response.get_json())

        with self.app_module.app.app_context():
            product = db.session.get(Product, self.product_id)
            product.purchase_price_per_item = Decimal("99.000")
            sale = db.session.query(GiftSetSalesHistory).one()
            db.session.commit()

            self.assertEqual(sale.cost_price, Decimal("16.000"))
            self.assertEqual(sale.profit, Decimal("9.00"))
            self.assertEqual(
                db.session.query(StockHistory).filter_by(
                    product_id=self.product_id,
                    change_type="gift_set_sale",
                ).count(),
                1,
            )

        history_response = self.client.get(
            "/api/get_all_sales_history",
            headers=self.headers,
        )
        self.assertEqual(history_response.status_code, 200, history_response.get_json())

        gift_sale = next(item for item in history_response.get_json() if item["type"] == "gift_set")
        self.assertEqual(gift_sale["cost_price"], "16.000")
        self.assertEqual(gift_sale["profit"], "9.00")
        self.assertEqual(gift_sale["products"][0]["unit_price"], "8.000")

        analytics_response = self.client.get(
            "/api/statistics/overview?start_date=2026-11-01&end_date=2026-11-30",
            headers=self.headers,
        )
        self.assertEqual(analytics_response.status_code, 200, analytics_response.get_json())
        summary = analytics_response.get_json()["summary"]
        self.assertEqual(summary["product_gross_profit"], 12.0)
        self.assertEqual(summary["gift_set_gross_profit"], 9.0)
        self.assertEqual(summary["gross_profit"], 21.0)


if __name__ == "__main__":
    unittest.main()
