"""Regression coverage for durable order status transitions and inventory handling."""

import importlib
import unittest
from decimal import Decimal

auth_module = importlib.import_module("test_auth")

from models import Customer, Product, SaleHistory, StockHistory, db
from models.order import Order


class OrderStatusWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.app_module = auth_module.crm_app_module
        with self.app_module.app.app_context():
            db.drop_all()
            db.create_all()
            self.app_module.create_roles_and_users()
            product = Product(
                name="Order workflow product",
                total_quantity=10,
                available_quantity=10,
                reserved_quantity=0,
                sold_quantity=0,
                purchase_price_per_item=Decimal("8.00"),
                selling_price_per_item=Decimal("20.00"),
                article="ORDER-0001",
                product_description="Order workflow test",
            )
            db.session.add(product)
            db.session.commit()
            self.product_id = product.id

        self.client = self.app_module.app.test_client()
        login = self.client.post(
            "/api/login",
            json={"username": "manager", "password": "test-manager-password"},
        )
        self.assertEqual(login.status_code, 200, login.get_json())
        self.headers = {"Authorization": f"Bearer {login.get_json()['token']}"}

    def tearDown(self):
        with self.app_module.app.app_context():
            db.session.remove()

    def create_order(self):
        response = self.client.post(
            "/api/store/orders",
            json={
                "customer_name": "Order workflow customer",
                "customer_phone": "+380501234567",
                "items": [{"product_id": self.product_id, "quantity": 3}],
            },
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()["order"]["id"]

    def change_status(self, order_id, status):
        return self.client.patch(
            f"/api/orders/{order_id}/status",
            headers=self.headers,
            json={"status": status},
        )

    def test_order_reserves_stock_and_creates_sale_only_when_completed(self):
        order_id = self.create_order()
        with self.app_module.app.app_context():
            product = db.session.get(Product, self.product_id)
            product.purchase_price_per_item = Decimal("99.00")
            db.session.commit()

        confirmed = self.change_status(order_id, "confirmed")
        self.assertEqual(confirmed.status_code, 200, confirmed.get_json())
        with self.app_module.app.app_context():
            product = db.session.get(Product, self.product_id)
            self.assertEqual(product.available_quantity, 7)
            self.assertEqual(product.reserved_quantity, 3)
            self.assertEqual(db.session.query(SaleHistory).count(), 0)

        for status in ("awaiting_payment", "paid", "shipped", "completed"):
            response = self.change_status(order_id, status)
            self.assertEqual(response.status_code, 200, response.get_json())

        with self.app_module.app.app_context():
            product = db.session.get(Product, self.product_id)
            sale = db.session.query(SaleHistory).one()
            order = db.session.get(Order, order_id)
            self.assertEqual(order.status, "completed")
            self.assertEqual(product.available_quantity, 7)
            self.assertEqual(product.reserved_quantity, 0)
            self.assertEqual(product.sold_quantity, 3)
            self.assertEqual(sale.quantity_sold, 3)
            self.assertEqual(sale.selling_total_price, Decimal("60.00"))
            self.assertEqual(sale.profit, Decimal("36.00"))
            self.assertEqual(order.items[0].unit_cost, Decimal("8.000"))
            self.assertEqual(
                db.session.query(StockHistory).filter_by(change_type="order_reservation").count(),
                1,
            )


    def test_order_without_cost_snapshot_cannot_be_completed(self):
        order_id = self.create_order()
        with self.app_module.app.app_context():
            order = db.session.get(Order, order_id)
            order.items[0].unit_cost = None
            db.session.commit()

        self.assertEqual(self.change_status(order_id, "confirmed").status_code, 200)
        for status in ("awaiting_payment", "paid", "shipped"):
            self.assertEqual(self.change_status(order_id, status).status_code, 200)

        response = self.change_status(order_id, "completed")
        self.assertEqual(response.status_code, 409)
        self.assertIn("snapshot собівартості", response.get_json()["error"])

        with self.app_module.app.app_context():
            product = db.session.get(Product, self.product_id)
            order = db.session.get(Order, order_id)
            self.assertEqual(order.status, "shipped")
            self.assertEqual(product.reserved_quantity, 3)
            self.assertEqual(db.session.query(SaleHistory).count(), 0)

    def test_cancellation_releases_reservation_without_creating_sale(self):
        order_id = self.create_order()
        self.assertEqual(self.change_status(order_id, "confirmed").status_code, 200)
        cancelled = self.change_status(order_id, "cancelled")
        self.assertEqual(cancelled.status_code, 200, cancelled.get_json())

        with self.app_module.app.app_context():
            product = db.session.get(Product, self.product_id)
            order = db.session.get(Order, order_id)
            self.assertEqual(order.status, "cancelled")
            self.assertEqual(product.available_quantity, 10)
            self.assertEqual(product.reserved_quantity, 0)
            self.assertEqual(db.session.query(SaleHistory).count(), 0)

    def test_invalid_transition_is_rejected(self):
        order_id = self.create_order()
        response = self.change_status(order_id, "completed")
        self.assertEqual(response.status_code, 409)

    def test_store_order_creation_is_public_but_order_management_is_protected(self):
        order_id = self.create_order()
        response = self.client.get("/api/orders")
        self.assertEqual(response.status_code, 401)
        manager_response = self.client.get("/api/orders", headers=self.headers)
        self.assertEqual(manager_response.status_code, 200)
        self.assertTrue(any(order["id"] == order_id for order in manager_response.get_json()))
