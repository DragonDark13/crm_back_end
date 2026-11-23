"""Merge inventory-date and orders migration branches.

Revision ID: d1e5f7a9c240
Revises: c3a8f1d9e620, c9d4e7a1b630
"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "d1e5f7a9c240"
down_revision: Union[str, Sequence[str], None] = (
    "c3a8f1d9e620",
    "c9d4e7a1b630",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge migration branches without changing the database schema."""
    pass


def downgrade() -> None:
    """No schema changes are performed by this merge revision."""
    pass
