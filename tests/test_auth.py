import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

os.environ["DATABASE_URL"] = "sqlite:////tmp/crm_backend_auth_tests.db"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key"
os.environ["GUEST_PASSWORD"] = "test-guest-password"
os.environ["MANAGER_PASSWORD"] = "test-manager-password"

from flask import Flask

from models import db, Role, User, RevokedToken, Product, Customer, SaleHistory

# Create the SQLite schema before importing app.py, whose current startup
# sequence creates the default users immediately.
_database_app = Flask("crm_auth_test_database")
_database_app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
_database_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(_database_app)
with _database_app.app_context():
    db.create_all()

import app as crm_app_module


class AuthenticationApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        crm_app_module.app.config.update(TESTING=True)
        cls.client = crm_app_module.app.test_client()

    def setUp(self):
        with crm_app_module.app.app_context():
            db.drop_all()
            db.create_all()
            crm_app_module.create_roles_and_users()

            self.guest = self._create_user("test_guest", "guest")
            self.manager = self._create_user("test_manager", "manager")
            self.inactive = self._create_user("test_inactive", "manager", active=0)

    def _create_user(self, username, role_name, active=1):
        role = Role.query.filter_by(name=role_name).first()
        user = User(
            username=username,
            email=f"{username}@example.test",
            fs_uniquifier=str(uuid4()),
            active=active,
        )
        user.set_password("test-password")
        user.roles.append(role)
        db.session.add(user)
        db.session.commit()
        return user

    def _login(self, username):
        response = self.client.post(
            "/api/login",
            json={"username": username, "password": "test-password"},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()["token"]

    def _headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_unauthenticated_user_cannot_access_protected_api(self):
        response = self.client.get("/api/protected")
        self.assertEqual(response.status_code, 401)

    def test_guest_can_read_catalog_but_cannot_access_manager_api(self):
        token = self._login("test_guest")
        headers = self._headers(token)

        with patch.object(
            crm_app_module.ProductService,
            "get_product_by_id",
            return_value=({"id": 1}, 200),
        ):
            catalog_response = self.client.get(
                "/api/product/1",
                headers=headers,
            )
        self.assertEqual(catalog_response.status_code, 200)

        protected_response = self.client.get("/api/protected", headers=headers)
        self.assertEqual(protected_response.status_code, 403)

    def test_manager_can_access_protected_api(self):
        token = self._login("test_manager")
        response = self.client.get(
            "/api/protected",
            headers=self._headers(token),
        )
        self.assertEqual(response.status_code, 200)


    def test_full_database_reset_is_manager_only_and_recreates_bootstrap_accounts(self):
        manager_headers = self._headers(self._login("test_manager"))
        guest_headers = self._headers(self._login("test_guest"))

        with patch.object(crm_app_module, "reset_database") as reset_mock, patch.object(
            crm_app_module, "create_roles_and_users"
        ) as bootstrap_mock:
            missing_confirmation = self.client.post(
                "/api/reset-database",
                headers=manager_headers,
                json={},
            )
            manager_response = self.client.post(
                "/api/reset-database",
                headers=manager_headers,
                json={"confirmation": "ОЧИСТИТИ БАЗУ"},
            )

        self.assertEqual(missing_confirmation.status_code, 400)
        self.assertEqual(manager_response.status_code, 200)
        reset_mock.assert_called_once_with()
        bootstrap_mock.assert_called_once_with()

        guest_response = self.client.post(
            "/api/reset-database",
            headers=guest_headers,
            json={"confirmation": "ОЧИСТИТИ БАЗУ"},
        )
        unauthenticated_response = self.client.post("/api/reset-database")

        self.assertEqual(guest_response.status_code, 403)
        self.assertEqual(unauthenticated_response.status_code, 401)

    def test_inactive_user_cannot_login_or_access_api(self):
        login_response = self.client.post(
            "/api/login",
            json={"username": "test_inactive", "password": "test-password"},
        )
        self.assertEqual(login_response.status_code, 401)

        with crm_app_module.app.app_context():
            user = User.query.filter_by(username="test_inactive").first()
            user.active = 1
            db.session.commit()
        token = self._login("test_inactive")

        with crm_app_module.app.app_context():
            user = User.query.filter_by(username="test_inactive").first()
            user.active = 0
            db.session.commit()

        response = self.client.get(
            "/api/protected",
            headers=self._headers(token),
        )
        self.assertEqual(response.status_code, 401)

    def test_logout_revokes_access_token(self):
        token = self._login("test_manager")
        headers = self._headers(token)

        logout_response = self.client.post("/api/logout", headers=headers)
        self.assertEqual(logout_response.status_code, 200)

        protected_response = self.client.get("/api/protected", headers=headers)
        self.assertEqual(protected_response.status_code, 401)

    def test_me_rejects_revoked_token(self):
        token = self._login("test_manager")
        headers = self._headers(token)

        self.client.post("/api/logout", headers=headers)
        response = self.client.get("/api/me", headers=headers)
        self.assertEqual(response.status_code, 401)


    def test_login_response_matches_frontend_contract(self):
        response = self.client.post(
            "/api/login",
            json={"username": "test_manager", "password": "test-password"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["message"], "Login successful")
        self.assertIsInstance(payload["token"], str)
        self.assertTrue(payload["token"])

    def test_me_response_matches_frontend_role_contract(self):
        token = self._login("test_manager")
        response = self.client.get("/api/me", headers=self._headers(token))

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(set(payload), {"id", "username", "roles"})
        self.assertEqual(payload["username"], "test_manager")
        self.assertEqual(payload["roles"], ["manager"])


    def test_access_token_is_invalidated_when_user_identity_is_recreated(self):
        token = self._login("test_manager")
        with crm_app_module.app.app_context():
            user = User.query.filter_by(username="test_manager").first()
            user.fs_uniquifier = str(uuid4())
            db.session.commit()

        response = self.client.get(
            "/api/protected",
            headers=self._headers(token),
        )
        self.assertEqual(response.status_code, 401)

    def test_guest_cannot_mutate_catalog(self):
        token = self._login("test_guest")
        response = self.client.post(
            "/api/add_new_product",
            json={"name": "Forbidden product"},
            headers=self._headers(token),
        )

        self.assertEqual(response.status_code, 403)

    def test_expired_access_token_is_rejected(self):
        from datetime import timedelta
        from flask_jwt_extended import create_access_token

        with crm_app_module.app.app_context():
            user = User.query.filter_by(username="test_manager").first()
            token = create_access_token(
                identity=str(user.id),
                expires_delta=timedelta(seconds=-1),
            )

        response = self.client.get(
            "/api/protected",
            headers=self._headers(token),
        )
        self.assertEqual(response.status_code, 401)

    def test_logout_cannot_be_replayed_with_revoked_token(self):
        token = self._login("test_manager")
        headers = self._headers(token)

        first_logout = self.client.post("/api/logout", headers=headers)
        second_logout = self.client.post("/api/logout", headers=headers)

        self.assertEqual(first_logout.status_code, 200)
        self.assertEqual(second_logout.status_code, 401)


    def test_login_throttling_locks_after_five_failed_attempts(self):
        for _ in range(5):
            response = self.client.post(
                "/api/login",
                json={"username": "test_manager", "password": "wrong-password"},
            )
            self.assertEqual(response.status_code, 401)

        locked_response = self.client.post(
            "/api/login",
            json={"username": "test_manager", "password": "test-password"},
        )
        self.assertEqual(locked_response.status_code, 429)

    def test_manager_cannot_bulk_delete_or_delete_history(self):
        token = self._login("test_manager")
        headers = self._headers(token)

        bulk_delete = self.client.delete("/api/delete_all_products", headers=headers)
        history_delete = self.client.delete(
            "/api/delete-history/1/sale/1",
            headers=headers,
        )

        self.assertEqual(bulk_delete.status_code, 403)
        self.assertEqual(history_delete.status_code, 403)

    def test_product_with_sales_history_cannot_be_deleted(self):
        with crm_app_module.app.app_context():
            product = Product(
                name="Historical product",
                article="TEST-HISTORY-001",
                product_description="",
            )
            customer = Customer(name="Historical customer")
            db.session.add_all([product, customer])
            db.session.flush()
            sale = SaleHistory(
                product_id=product.id,
                customer_id=customer.id,
                quantity_sold=1,
                selling_price_per_item=10,
                selling_total_price=10,
            )
            db.session.add(sale)
            db.session.commit()
            product_id = product.id
            sale_id = sale.id

        headers = self._headers(self._login("test_manager"))
        response = self.client.delete(f"/api/product/{product_id}", headers=headers)

        self.assertEqual(response.status_code, 409)
        with crm_app_module.app.app_context():
            self.assertIsNotNone(db.session.get(Product, product_id))
            self.assertIsNotNone(db.session.get(SaleHistory, sale_id))

    def test_customer_with_sales_history_cannot_be_deleted(self):
        with crm_app_module.app.app_context():
            product = Product(
                name="Customer history product",
                article="TEST-HISTORY-002",
                product_description="",
            )
            customer = Customer(name="Customer with sales")
            db.session.add_all([product, customer])
            db.session.flush()
            sale = SaleHistory(
                product_id=product.id,
                customer_id=customer.id,
                quantity_sold=1,
                selling_price_per_item=10,
                selling_total_price=10,
            )
            db.session.add(sale)
            db.session.commit()
            customer_id = customer.id
            sale_id = sale.id

        headers = self._headers(self._login("test_manager"))
        response = self.client.delete(f"/api/delete_customers/{customer_id}", headers=headers)

        self.assertEqual(response.status_code, 409)
        with crm_app_module.app.app_context():
            self.assertIsNotNone(db.session.get(Customer, customer_id))
            self.assertIsNotNone(db.session.get(SaleHistory, sale_id))

    def test_deployment_webhook_requires_secret(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WEBHOOK_SECRET", None)
            disabled = self.client.post("/update_server")
        self.assertEqual(disabled.status_code, 503)

        with patch.dict(os.environ, {"WEBHOOK_SECRET": "expected-secret"}):
            unauthorized = self.client.post(
                "/update_server",
                headers={"X-Webhook-Secret": "wrong-secret"},
            )
        self.assertEqual(unauthorized.status_code, 401)


    def test_bootstrap_does_not_create_accounts_with_default_passwords(self):
        with crm_app_module.app.app_context():
            User.query.filter(
                User.email.in_(["guest@example.com", "manager@example.com"])
            ).delete(synchronize_session=False)
            db.session.commit()

            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("GUEST_PASSWORD", None)
                os.environ.pop("MANAGER_PASSWORD", None)
                crm_app_module.create_roles_and_users()

            self.assertIsNone(User.query.filter_by(email="guest@example.com").first())
            self.assertIsNone(User.query.filter_by(email="manager@example.com").first())


    def test_expired_revoked_tokens_are_cleaned_up(self):
        now = datetime.now(timezone.utc)
        with crm_app_module.app.app_context():
            expired = RevokedToken(
                jti="expired-test-token",
                token_type="access",
                user_identity="1",
                revoked_at=now - timedelta(hours=2),
                expires_at=now - timedelta(hours=1),
            )
            active = RevokedToken(
                jti="active-test-token",
                token_type="access",
                user_identity="1",
                revoked_at=now,
                expires_at=now + timedelta(hours=1),
            )
            db.session.add_all([expired, active])
            db.session.commit()

            deleted_count = crm_app_module.cleanup_expired_revoked_tokens()

            self.assertEqual(deleted_count, 1)
            self.assertIsNone(
                RevokedToken.query.filter_by(jti="expired-test-token").first()
            )
            self.assertIsNotNone(
                RevokedToken.query.filter_by(jti="active-test-token").first()
            )


if __name__ == "__main__":
    unittest.main()
