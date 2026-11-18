"""Integration tests for authentication and role-based API access.

Run against a dedicated database with the application's existing schema already migrated:
    TEST_DATABASE_URL=postgresql://... python -m unittest tests.test_security_access
The test suite never falls back to the application's normal DATABASE_URL.
"""
import os
import unittest
from datetime import datetime, timezone

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ.setdefault("SECRET_KEY", "test-only-secret-key")
    os.environ.setdefault("JWT_SECRET_KEY", "test-only-jwt-secret")
    from app import app
    from models import db, User, Role


@unittest.skipUnless(TEST_DATABASE_URL, "Set TEST_DATABASE_URL to a dedicated test database")
class SecurityAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config.update(TESTING=True, JWT_ACCESS_TOKEN_EXPIRES=False)
        with app.app_context():
            db.create_all()
            cls.guest_role = Role.query.filter_by(name="guest").first()
            if not cls.guest_role:
                cls.guest_role = Role(name="guest", description="Test guest")
                db.session.add(cls.guest_role)
            cls.manager_role = Role.query.filter_by(name="manager").first()
            if not cls.manager_role:
                cls.manager_role = Role(name="manager", description="Test manager")
                db.session.add(cls.manager_role)
            db.session.flush()

            cls.guest = User.query.filter_by(username="security_test_guest").first()
            if not cls.guest:
                cls.guest = User(
                    username="security_test_guest",
                    email="security_test_guest@example.invalid",
                    fs_uniquifier="security-test-guest",
                    active=1,
                )
                cls.guest.set_password("test-password")
                cls.guest.roles.append(cls.guest_role)
                db.session.add(cls.guest)

            cls.manager = User.query.filter_by(username="security_test_manager").first()
            if not cls.manager:
                cls.manager = User(
                    username="security_test_manager",
                    email="security_test_manager@example.invalid",
                    fs_uniquifier="security-test-manager",
                    active=1,
                )
                cls.manager.set_password("test-password")
                cls.manager.roles.append(cls.manager_role)
                db.session.add(cls.manager)
            db.session.commit()

    def setUp(self):
        self.client = app.test_client()
        with app.app_context():
            from flask_jwt_extended import create_access_token
            self.guest_token = create_access_token(
                identity=str(self.guest.id),
                additional_claims={"roles": ["guest"]},
            )
            self.manager_token = create_access_token(
                identity=str(self.manager.id),
                additional_claims={"roles": ["manager"]},
            )

    def headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_missing_token_is_rejected(self):
        response = self.client.get("/api/customers/get_all_customers")
        self.assertEqual(response.status_code, 401)

    def test_guest_can_read_catalogue(self):
        response = self.client.get(
            "/api/categories/get_all_categories",
            headers=self.headers(self.guest_token),
        )
        self.assertNotIn(response.status_code, (401, 403))

    def test_guest_cannot_read_customer_or_financial_data(self):
        for path in (
            "/api/customers/get_all_customers",
            "/api/statistics/profit-expense",
        ):
            with self.subTest(path=path):
                response = self.client.get(path, headers=self.headers(self.guest_token))
                self.assertEqual(response.status_code, 403)

    def test_manager_can_access_financial_read_route(self):
        response = self.client.get(
            "/api/statistics/profit-expense",
            headers=self.headers(self.manager_token),
        )
        self.assertNotIn(response.status_code, (401, 403))

    def test_manager_cannot_run_bulk_delete_or_delete_history(self):
        paths = (
            "/api/delete_all_products",
            "/api/delete-history/1/product/1",
        )
        for path in paths:
            with self.subTest(path=path):
                response = self.client.delete(path, headers=self.headers(self.manager_token))
                self.assertEqual(response.status_code, 403)

    def test_logout_revokes_token(self):
        headers = self.headers(self.manager_token)
        logout_response = self.client.post("/api/logout", headers=headers)
        self.assertEqual(logout_response.status_code, 200)
        profile_response = self.client.get("/api/me", headers=headers)
        self.assertEqual(profile_response.status_code, 401)

    def test_login_throttles_after_five_failed_attempts(self):
        username = f"security-lockout-{datetime.now(timezone.utc).timestamp()}"
        for _ in range(5):
            response = self.client.post(
                "/api/login",
                json={"username": username, "password": "incorrect"},
            )
            self.assertEqual(response.status_code, 401)
        response = self.client.post(
            "/api/login",
            json={"username": username, "password": "incorrect"},
        )
        self.assertEqual(response.status_code, 429)


if __name__ == "__main__":
    unittest.main()
