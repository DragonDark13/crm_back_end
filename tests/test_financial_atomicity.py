"""Regression tests for atomic purchase and sale transactions."""

import unittest
import importlib
from decimal import Decimal

from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError

auth_module = importlib.import_module("test_auth")

from models import (  # noqa: E402
    Customer,
    PackagingMaterial,
    PackagingSaleHistory,
    Product,
    PurchaseHistory,
    SaleHistory,
    Supplier,
    db,
)
from postgreSQLConnect import db_session  # noqa: E402


class FinancialAtomicityTests(unittest.TestCase):
    def setUp(self):
        self.app_module = auth_module.crm_app_module
        db_session.remove()

        with self.app_module.app.app_context():
            db.drop_all()
            db.create_all()
            self.app_module.create_roles_and_users()

            supplier = Supplier(name="Atomicity test supplier")
            customer = Customer(name="Atomicity test customer")
            product = Product(
                name="Atomicity test product",
                supplier=supplier,
                total_quantity=10,
                available_quantity=10,
                sold_quantity=0,
                purchase_total_price=Decimal("100.00"),
                purchase_price_per_item=Decimal("10.00"),
                selling_total_price=Decimal("0.00"),
                selling_price_per_item=Decimal("20.00"),
                selling_quantity=0,
                article="ATOMIC-0001",
                product_description="Atomicity integration test",
            )
            packaging = PackagingMaterial(
                name="Atomicity test packaging",
                total_quantity=10,
                available_quantity=10,
                purchase_price_per_unit=Decimal("1.50"),
                total_purchase_cost=Decimal("15.00"),
                available_stock_cost=Decimal("15.00"),
            )
            db.session.add_all([supplier, customer, product, packaging])
            db.session.commit()

            self.product_id = product.id
            self.supplier_id = supplier.id
            self.customer_id = customer.id
            self.packaging_id = packaging.id

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

    @staticmethod
    def _fail_when_model_added(model_class):
        def fail_before_flush(session, flush_context, instances):
            if any(isinstance(item, model_class) for item in session.new):
                raise SQLAlchemyError("simulated history write failure")
        return fail_before_flush

    def _install_failure(self, model_class):
        session = db_session()
        handler = self._fail_when_model_added(model_class)
        event.listen(session, "before_flush", handler)
        return session, handler

    def test_purchase_rolls_back_stock_and_cost_when_history_write_fails(self):
        session, handler = self._install_failure(PurchaseHistory)
        try:
            response = self.client.post(
                f"/api/product/{self.product_id}/purchase",
                headers=self.headers,
                json={
                    "quantity": 5,
                    "purchase_price_per_item": "12.50",
                    "purchase_total_price": "62.50",
                    "supplier_id": self.supplier_id,
                    "purchase_date": "2026-11-18",
                },
            )
        finally:
            event.remove(session, "before_flush", handler)

        self.assertEqual(response.status_code, 500)
        db_session.expire_all()
        product = db_session.query(Product).filter_by(id=self.product_id).one()
        self.assertEqual(product.total_quantity, 10)
        self.assertEqual(product.available_quantity, 10)
        self.assertEqual(product.purchase_total_price, Decimal("100.00"))
        self.assertEqual(product.purchase_price_per_item, Decimal("10.00"))
        self.assertEqual(db_session.query(PurchaseHistory).filter_by(product_id=product.id).count(), 0)

    def test_sale_rolls_back_stock_and_revenue_when_history_write_fails(self):
        session, handler = self._install_failure(SaleHistory)
        try:
            response = self.client.post(
                f"/api/product/{self.product_id}/sale",
                headers=self.headers,
                json={
                    "customer": self.customer_id,
                    "quantity": 3,
                    "selling_price_per_item": "20.00",
                    "selling_total_price": "60.00",
                    "sale_date": "2026-11-18",
                },
            )
        finally:
            event.remove(session, "before_flush", handler)

        self.assertEqual(response.status_code, 500)
        db_session.expire_all()
        product = db_session.query(Product).filter_by(id=self.product_id).one()
        self.assertEqual(product.available_quantity, 10)
        self.assertEqual(product.sold_quantity, 0)
        self.assertEqual(product.selling_quantity, 0)
        self.assertEqual(product.selling_total_price, Decimal("0.00"))
        self.assertEqual(db_session.query(SaleHistory).filter_by(product_id=product.id).count(), 0)

    def test_sale_rolls_back_product_and_packaging_when_packaging_history_fails(self):
        session, handler = self._install_failure(PackagingSaleHistory)
        try:
            response = self.client.post(
                f"/api/product/{self.product_id}/sale",
                headers=self.headers,
                json={
                    "customer": self.customer_id,
                    "quantity": 3,
                    "selling_price_per_item": "20.00",
                    "selling_total_price": "60.00",
                    "packaging_id": self.packaging_id,
                    "packaging_quantity": 2,
                    "total_packaging_cost": "3.00",
                    "sale_date": "2026-11-18",
                },
            )
        finally:
            event.remove(session, "before_flush", handler)

        self.assertEqual(response.status_code, 500)
        db_session.expire_all()
        product = db_session.query(Product).filter_by(id=self.product_id).one()
        packaging = db_session.query(PackagingMaterial).filter_by(id=self.packaging_id).one()

        self.assertEqual(product.available_quantity, 10)
        self.assertEqual(product.sold_quantity, 0)
        self.assertEqual(product.selling_quantity, 0)
        self.assertEqual(product.selling_total_price, Decimal("0.00"))
        self.assertEqual(packaging.available_quantity, 10)
        self.assertEqual(packaging.available_stock_cost, Decimal("15.00"))
        self.assertEqual(db_session.query(SaleHistory).filter_by(product_id=product.id).count(), 0)
        self.assertEqual(db_session.query(PackagingSaleHistory).count(), 0)


if __name__ == "__main__":
    unittest.main()
