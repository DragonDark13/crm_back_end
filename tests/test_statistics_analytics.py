"""Regression tests for period-based analytics and accounting scopes."""

import importlib
import unittest
from datetime import date, datetime
from decimal import Decimal

auth_module = importlib.import_module("test_auth")

from models import (  # noqa: E402
    Customer,
    GiftSet,
    GiftSetSalesHistory,
    OtherInvestment,
    PackagingMaterial,
    PackagingPurchaseHistory,
    Product,
    PurchaseHistory,
    ReturnHistory,
    SaleHistory,
    Supplier,
    db,
)


class AnalyticsOverviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_module = auth_module.crm_app_module
        cls.app_module.app.config.update(TESTING=True)
        cls.client = cls.app_module.app.test_client()

    def setUp(self):
        with self.app_module.app.app_context():
            db.drop_all()
            db.create_all()
            self.app_module.create_roles_and_users()

            supplier = Supplier(name="Analytics supplier")
            customer = Customer(name="Analytics customer")
            product = Product(
                name="Analytics product",
                supplier=supplier,
                total_quantity=10,
                available_quantity=4,
                sold_quantity=2,
                purchase_total_price=Decimal("100.00"),
                purchase_price_per_item=Decimal("10.00"),
                selling_price_per_item=Decimal("30.00"),
                reorder_level=5,
                article="ANALYTICS-001",
                product_description="",
            )
            packaging = PackagingMaterial(
                name="Analytics packaging",
                total_quantity=10,
                available_quantity=3,
                purchase_price_per_unit=Decimal("2.00"),
                reorder_level=5,
            )
            gift_set = GiftSet(name="Analytics gift set")
            db.session.add_all([supplier, customer, product, packaging, gift_set])
            db.session.flush()

            sale = SaleHistory(
                product_id=product.id,
                customer_id=customer.id,
                quantity_sold=2,
                selling_price_per_item=Decimal("30.00"),
                selling_total_price=Decimal("60.00"),
                sale_date=datetime(2026, 11, 10, 12, 0),
                profit=Decimal("25.00"),
                total_packaging_cost=Decimal("5.00"),
            )
            db.session.add(sale)
            db.session.flush()

            db.session.add_all([
                ReturnHistory(
                    product_id=product.id,
                    customer_id=customer.id,
                    sale_id=sale.id,
                    quantity_returned=1,
                    return_amount=Decimal("30.00"),
                    return_date=datetime(2026, 11, 12, 12, 0),
                ),
                GiftSetSalesHistory(
                    gift_set_id=gift_set.id,
                    customer_id=customer.id,
                    sold_at=datetime(2026, 11, 15, 12, 0),
                    sold_price=50.00,
                    quantity=1,
                ),
                PurchaseHistory(
                    product_id=product.id,
                    supplier_id=supplier.id,
                    purchase_price_per_item=Decimal("10.00"),
                    purchase_total_price=Decimal("100.00"),
                    purchase_date=date(2026, 11, 2),
                    quantity_purchase=10,
                ),
                PackagingPurchaseHistory(
                    material_id=packaging.id,
                    quantity_purchased=10,
                    purchase_price_per_unit=Decimal("2.00"),
                    purchase_total_price=Decimal("20.00"),
                    purchase_date=datetime(2026, 11, 3, 9, 0),
                ),
                OtherInvestment(
                    type_name="Delivery",
                    supplier="Courier",
                    cost=10.00,
                    date=date(2026, 11, 4),
                ),
            ])
            db.session.commit()

        login = self.client.post(
            "/api/login",
            json={"username": "manager", "password": "test-manager-password"},
        )
        self.assertEqual(login.status_code, 200, login.get_json())
        self.headers = {"Authorization": f"Bearer {login.get_json()['token']}"}

    def test_overview_includes_returns_gift_set_revenue_and_all_expenses(self):
        response = self.client.get(
            "/api/statistics/overview?start_date=2026-11-01&end_date=2026-11-30",
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200, response.get_json())
        payload = response.get_json()
        summary = payload["summary"]

        self.assertEqual(summary["product_sales"], 60.0)
        self.assertEqual(summary["gift_set_sales"], 50.0)
        self.assertEqual(summary["gross_sales"], 110.0)
        self.assertEqual(summary["returns"], 30.0)
        self.assertEqual(summary["net_sales"], 80.0)
        # Stored sale profit includes packaging. On return, only product margin
        # for the returned unit is reversed; packaging remains a consumed cost.
        self.assertEqual(summary["product_gross_profit"], 10.0)
        self.assertEqual(summary["purchase_expenses"], 120.0)
        self.assertEqual(summary["other_expenses"], 10.0)
        self.assertEqual(summary["total_expenses"], 130.0)
        self.assertEqual(summary["restock_count"], 2)

        self.assertEqual(len(payload["top_products"]), 1)
        self.assertEqual(payload["top_products"][0]["net_quantity"], 1)
        self.assertEqual(payload["top_products"][0]["gross_profit"], 10.0)
        self.assertEqual(
            {item["type"] for item in payload["restock"]},
            {"product", "packaging"},
        )
        self.assertIn("прибуток гіфтбоксів не розраховується", payload["profit_scope_note"])

    def test_overview_rejects_invalid_or_reversed_dates(self):
        invalid = self.client.get(
            "/api/statistics/overview?start_date=not-a-date&end_date=2026-11-30",
            headers=self.headers,
        )
        reversed_range = self.client.get(
            "/api/statistics/overview?start_date=2026-12-01&end_date=2026-11-01",
            headers=self.headers,
        )

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(reversed_range.status_code, 400)

    def test_overview_requires_authentication(self):
        response = self.client.get(
            "/api/statistics/overview?start_date=2026-11-01&end_date=2026-11-30"
        )
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
