import os
import unittest
from unittest.mock import patch
from uuid import uuid4

os.environ["DATABASE_URL"] = "sqlite:////tmp/crm_backend_auth_tests.db"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key"
os.environ["GUEST_PASSWORD"] = "test-guest-password"
os.environ["MANAGER_PASSWORD"] = "test-manager-password"

from flask import Flask

from models import db, Role, User

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


if __name__ == "__main__":
    unittest.main()
