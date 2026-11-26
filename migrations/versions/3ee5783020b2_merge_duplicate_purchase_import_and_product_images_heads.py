"""Merge the local duplicate migration head with the repository head.

Revision ID: 3ee5783020b2
Revises: b6406fb56205, f4c8b2a1d930
"""

from typing import Sequence, Union


revision: str = "3ee5783020b2"
down_revision: Union[str, Sequence[str], None] = (
    "b6406fb56205",
    "f4c8b2a1d930",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge duplicate migration heads without changing the schema."""
    pass


def downgrade() -> None:
    """Restore the duplicate migration heads without changing the schema."""
    pass
