"""merge purchase import and product images migrations

Revision ID: b6406fb56205
Revises: a4b7c9d2e610, e3b7c9d1a520
Create Date: 2026-11-25 21:02:31.585085

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6406fb56205'
down_revision: Union[str, Sequence[str], None] = ('a4b7c9d2e610', 'e3b7c9d1a520')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass