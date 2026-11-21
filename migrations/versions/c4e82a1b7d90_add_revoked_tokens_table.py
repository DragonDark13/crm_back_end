"""Add revoked tokens table.

Revision ID: c4e82a1b7d90
Revises: a7c91e2d4f60
"""

from alembic import op
import sqlalchemy as sa


revision = "c4e82a1b7d90"
down_revision = "a7c91e2d4f60"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "revoked_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("jti", sa.String(length=36), nullable=False, unique=True),
        sa.Column("token_type", sa.String(length=16), nullable=False),
        sa.Column("user_identity", sa.String(length=255), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table("revoked_tokens")
