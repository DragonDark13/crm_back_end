"""Merge purchase import tracking and product image migrations.

Revision ID: f4c8b2a1d930
Revises: a4b7c9d2e610, e3b7c9d1a520
"""

from typing import Sequence, Union


revision: str = "f4c8b2a1d930"
down_revision: Union[str, Sequence[str], None] = (
    "a4b7c9d2e610",
    "e3b7c9d1a520",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge the parallel migration branches without changing the schema."""
    pass


def downgrade() -> None:
    """Restore the two independent heads without changing the schema."""
    pass
