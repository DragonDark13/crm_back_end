"""Create or adopt the application security tables.

This migration is intentionally limited to the three authentication/security
tables. Existing tables are adopted without dropping or recreating their data.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261118_01"
down_revision = None
branch_labels = None
depends_on = None


def _table_exists(bind, table_name):
    return table_name in inspect(bind).get_table_names()


def _index_exists(bind, table_name, index_name):
    return any(
        index["name"] == index_name
        for index in inspect(bind).get_indexes(table_name)
    )


def _unique_constraint_exists(bind, table_name, constraint_name):
    return any(
        constraint["name"] == constraint_name
        for constraint in inspect(bind).get_unique_constraints(table_name)
    )


def upgrade():
    bind = op.get_bind()

    if not _table_exists(bind, "jwt_token_blocklist"):
        op.create_table(
            "jwt_token_blocklist",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("jti", sa.String(length=36), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _index_exists(bind, "jwt_token_blocklist", "ix_jwt_token_blocklist_jti"):
        op.create_index(
            "ix_jwt_token_blocklist_jti",
            "jwt_token_blocklist",
            ["jti"],
            unique=True,
        )

    if not _index_exists(bind, "jwt_token_blocklist", "ix_jwt_token_blocklist_expires_at"):
        op.create_index(
            "ix_jwt_token_blocklist_expires_at",
            "jwt_token_blocklist",
            ["expires_at"],
            unique=False,
        )

    if not _table_exists(bind, "login_attempts"):
        op.create_table(
            "login_attempts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=255), nullable=False),
            sa.Column("ip_address", sa.String(length=64), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint("username", "ip_address", name="uq_login_attempt_username_ip"),
        )

    if not _unique_constraint_exists(bind, "login_attempts", "uq_login_attempt_username_ip"):
        op.create_unique_constraint(
            "uq_login_attempt_username_ip",
            "login_attempts",
            ["username", "ip_address"],
        )

    if not _index_exists(bind, "login_attempts", "ix_login_attempt_locked_until"):
        op.create_index(
            "ix_login_attempt_locked_until",
            "login_attempts",
            ["locked_until"],
            unique=False,
        )

    if not _table_exists(bind, "login_ip_attempts"):
        op.create_table(
            "login_ip_attempts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("ip_address", sa.String(length=64), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )

    if not _index_exists(bind, "login_ip_attempts", "ix_login_ip_attempts_ip_address"):
        op.create_index(
            "ix_login_ip_attempts_ip_address",
            "login_ip_attempts",
            ["ip_address"],
            unique=True,
        )


def downgrade():
    # This revision may adopt tables that existed before Alembic was introduced.
    # Dropping them would destroy login throttling and token revocation state.
    pass
