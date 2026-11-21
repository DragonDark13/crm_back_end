"""Add login throttling tables.

Revision ID: a7c91e2d4f60
Revises: 5bf39d38e869
"""

from alembic import op
import sqlalchemy as sa


revision = "a7c91e2d4f60"
down_revision = "5bf39d38e869"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column(
            "window_started_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "locked_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "username",
            "ip_address",
            name="uq_login_attempt_username_ip",
        ),
    )

    op.create_index(
        "ix_login_attempt_locked_until",
        "login_attempts",
        ["locked_until"],
    )

    op.create_table(
        "login_ip_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column(
            "window_started_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "locked_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_login_ip_attempts_ip_address",
        "login_ip_attempts",
        ["ip_address"],
        unique=True,
    )


def downgrade():
    op.drop_index(
        "ix_login_ip_attempts_ip_address",
        table_name="login_ip_attempts",
    )
    op.drop_table("login_ip_attempts")

    op.drop_index(
        "ix_login_attempt_locked_until",
        table_name="login_attempts",
    )
    op.drop_table("login_attempts")
