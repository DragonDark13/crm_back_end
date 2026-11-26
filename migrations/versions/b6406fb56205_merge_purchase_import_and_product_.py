"""Merge duplicate purchase import and product image migration heads.

Revision ID: b6406fb56205
Revises: a4b7c9d2e610, e3b7c9d1a520
"""

from typing import Sequence, Union


revision: str = "b6406fb56205"
down_revision: Union[str, Sequence[str], None] = (
    "a4b7c9d2e610",
    "e3b7c9d1a520",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge the duplicate migration branch without changing the schema."""
    pass


def downgrade() -> None:
    """Restore the two parent branches without changing the schema."""
    pass
