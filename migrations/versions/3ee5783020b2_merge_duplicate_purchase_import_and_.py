"""merge duplicate purchase import and product images heads

Revision ID: 3ee5783020b2
Revises: b6406fb56205, f4c8b2a1d930
Create Date: 2026-11-26 20:33:19.510302

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3ee5783020b2'
down_revision: Union[str, Sequence[str], None] = ('b6406fb56205', 'f4c8b2a1d930')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
