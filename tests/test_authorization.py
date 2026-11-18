"""Integration tests for API authentication and role-based authorization.

A dedicated SQLite database is prepared before importing app.py because the
application currently initializes roles/users during module import. Business
view functions are stubbed where needed; the real Flask request hooks, JWT
validation, user lookup, and RBAC middleware remain active.
"""

import importlib
import os
import tempfile
from pathlib import Path

import pytest
from flask import jsonify
from sqlalchemy import create_engine

_db_fd, _db_path = tempfile.mkstemp(prefix="crm-auth-tests-", suffix=".sqlite3")
os.close(_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_db_path).as_posix()}"
os.environ["SECRET_KEY"] = "integration-test-secret-key"
os.environ["JWT_SECRET_KEY"] = "integration-test-jwt-secret"
os.environ["GUEST_PASSWORD"] = "guest-test-password"
os.environ["MANAGER_PASSWORD"] = "manager-test-password"

from models import db, User, Role, TokenBlocklist, LoginAttempt, LoginIPAttempt  # noqa: E402
from models.associations import user_roles_table  # noqa: E402

_engine = create_engine(os.environ["DATABASE_URL"])
db.metadata.create_all(
    bind=_engine,
    tables=[
        Role.__table__,
        User.__table__,
        user_roles_table,
        TokenBlocklist.__table__,
        LoginAttempt.__table__,
        LoginIPAttempt.__table__,
    ],
)
_engine.dispose()

app_module = importlib.import_module("app")
app = app_module.app
app.config["TESTING"] = True

FINANCIAL_GET_PATHS = [
    "/api/get_all_sales_history",
    "/api/get_all_purchase_history",
    "/api/statistics/sales/monthly",
    "/api/statistics/profit-expense",
    "/api/investments/get_all_investments",
]


# These endpoints exercise the real app.before_request middleware without
# relying on business data or performing actual database mutations.
@app.route("/api/integration/read", methods=["GET", "HEAD"])
def integration_read():
    return jsonify({"read": True}), 200


@app.route("/api/integration/write", methods=["POST", "PUT", "PATCH", "DELETE"])
def integration_write():
    return jsonify({"write": True}), 200


@app.route("/api/integration/items/<int:item_id>", methods=["DELETE"])
def integration_delete_single(item_id):
    return jsonify({"deleted_id": item_id}), 200


@app.route("/api/delete_all_integration", methods=["DELETE"])
def integration_delete_all():
    return jsonify({"deleted_all": True}), 200


@app.route("/api/delete-history/integration", methods=["DELETE"])
def integration_delete_history():
    return jsonify({"deleted_history": True}), 200


@pytest.fixture(scope="session")
def auth_tokens():
    with app.app_context():
        guest_role = Role.query.filter_by(name="guest").first()
        manager_role = Role.query.filter_by(name="manager").first()

        guest = User.query.filter_by(username="integration_guest").first()
        if guest is None:
            guest = User(
                username="integration_guest",
                email="integration_guest@example.test",
                fs_uniquifier="integration-guest-unique",
                active=1,
            )
            guest.set_password("guest-test-password")
            guest.roles.append(guest_role)
            db.session.add(guest)

        manager = User.query.filter_by(username="integration_manager").first()
        if manager is None:
            manager = User(
                username="integration_manager",
                email="integration_manager@example.test",
                fs_uniquifier="integration-manager-unique",
                active=1,
            )
            manager.set_password("manager-test-password")
            manager.roles.append(manager_role)
            db.session.add(manager)

        db.session.commit()

        return {
            "guest": app_module.create_access_token(identity=str(guest.id)),
            "manager": app_module.create_access_token(identity=str(manager.id)),
        }


@pytest.fixture
def client():
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def stub_financial_get_views(monkeypatch):
    """Stub financial view bodies while retaining the real authorization hook."""
    for path in FINANCIAL_GET_PATHS:
        matching_rules = [rule for rule in app.url_map.iter_rules() if rule.rule == path]
        assert matching_rules, f"No Flask route registered for {path}"
        endpoint = matching_rules[0].endpoint
        monkeypatch.setitem(
            app.view_functions,
            endpoint,
            lambda: (jsonify({"integration_test": True}), 200),
        )


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_guest_can_read_general_and_financial_get_endpoints(
    client, auth_tokens, stub_financial_get_views
):
    headers = _auth_headers(auth_tokens["guest"])

    assert client.get("/api/integration/read", headers=headers).status_code == 200
    assert client.head("/api/integration/read", headers=headers).status_code == 200

    for path in FINANCIAL_GET_PATHS:
        response = client.get(path, headers=headers)
        assert response.status_code == 200, f"Guest could not read {path}"


def test_guest_cannot_create_update_or_delete(client, auth_tokens):
    headers = _auth_headers(auth_tokens["guest"])

    for method in ("post", "put", "patch", "delete"):
        response = getattr(client, method)("/api/integration/write", headers=headers)
        assert response.status_code == 403, f"Guest {method.upper()} was not forbidden"


def test_manager_can_read_general_and_financial_get_endpoints(
    client, auth_tokens, stub_financial_get_views
):
    headers = _auth_headers(auth_tokens["manager"])

    assert client.get("/api/integration/read", headers=headers).status_code == 200

    for path in FINANCIAL_GET_PATHS:
        response = client.get(path, headers=headers)
        assert response.status_code == 200, f"Manager could not read {path}"


def test_manager_can_create_update_and_delete_individual_records(client, auth_tokens):
    headers = _auth_headers(auth_tokens["manager"])

    for method in ("post", "put", "patch", "delete"):
        response = getattr(client, method)("/api/integration/write", headers=headers)
        assert response.status_code == 200, f"Manager {method.upper()} was unexpectedly blocked"

    response = client.delete("/api/integration/items/42", headers=headers)
    assert response.status_code == 200


def test_manager_cannot_bulk_delete_or_delete_history(client, auth_tokens):
    headers = _auth_headers(auth_tokens["manager"])

    assert client.delete(
        "/api/delete_all_integration", headers=headers
    ).status_code == 403
    assert client.delete(
        "/api/delete-history/integration", headers=headers
    ).status_code == 403


def test_unauthenticated_user_cannot_read_or_write_protected_api(
    client, stub_financial_get_views
):
    assert client.get("/api/integration/read").status_code == 401
    assert client.post("/api/integration/write").status_code == 401

    for path in FINANCIAL_GET_PATHS:
        assert client.get(path).status_code == 401, path


def test_login_is_public_and_options_preflight_does_not_require_jwt(client):
    login_response = client.post(
        "/api/login",
        json={"username": "missing-test-user", "password": "invalid"},
    )
    assert login_response.status_code == 401
    assert login_response.get_json().get("message") == "Invalid credentials"

    options_response = client.options("/api/integration/read")
    assert options_response.status_code != 401
