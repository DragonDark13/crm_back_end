import os
import uuid

import pytest
from flask import jsonify
from sqlalchemy import create_engine

# Integration tests must never use the application's normal DATABASE_URL.
test_database_url = os.getenv("TEST_DATABASE_URL")
if not test_database_url:
    raise RuntimeError(
        "TEST_DATABASE_URL must point to a dedicated test database. "
        "Run Alembic migrations against it before running pytest."
    )

if test_database_url == os.getenv("DATABASE_URL"):
    raise RuntimeError("TEST_DATABASE_URL must be different from DATABASE_URL.")

os.environ["DATABASE_URL"] = test_database_url
os.environ.setdefault("SECRET_KEY", "integration-tests-only-secret")
os.environ.setdefault("JWT_SECRET_KEY", "integration-tests-only-jwt-secret")
os.environ.setdefault("GUEST_PASSWORD", "integration-tests-only-guest-password")
os.environ.setdefault("MANAGER_PASSWORD", "integration-tests-only-manager-password")

# Import only after the test database URL and test secrets have been set.
from app import app
from models import db, Role, User


@app.route("/api/__test__/authorization-resource", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def authorization_test_resource():
    return jsonify(message="authorization test endpoint"), 200


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def user_factory():
    created_users = []

    def create_user(role_name=None, active=1):
        role = None
        if role_name:
            role = Role.query.filter_by(name=role_name).first()
            if role is None:
                role = Role(name=role_name, description="Integration test role")
                db.session.add(role)
                db.session.flush()

        user = User(
            username=f"test-{uuid.uuid4().hex}",
            email=f"test-{uuid.uuid4().hex}@example.invalid",
            active=active,
            fs_uniquifier=str(uuid.uuid4()),
        )
        user.set_password("integration-test-password")
        if role is not None:
            user.roles.append(role)

        db.session.add(user)
        db.session.commit()
        created_users.append(user)
        return user

    yield create_user

    for user in created_users:
        db.session.delete(user)
    db.session.commit()


@pytest.fixture
def auth_headers():
    def make_headers(user):
        from flask_jwt_extended import create_access_token

        with app.app_context():
            token = create_access_token(identity=str(user.id))
        return {"Authorization": f"Bearer {token}"}

    return make_headers
