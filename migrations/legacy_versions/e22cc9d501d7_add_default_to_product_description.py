"""add default to product_description

Revision ID: e22cc9d501d7
Revises: 3d0b17bc90aa
Create Date: 2026-01-01 11:38:27.136281

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e22cc9d501d7'
down_revision: Union[str, Sequence[str], None] = '3d0b17bc90aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # 1. Заповнюємо NULL
    op.execute("""
        UPDATE products
        SET product_description = ''
        WHERE product_description IS NULL
    """)

    # 2. Ставимо NOT NULL + default
    op.alter_column(
        'products',
        'product_description',
        existing_type=sa.String(length=500),
        nullable=False,
        server_default=''
    )


def downgrade():
    op.alter_column(
        'products',
        'product_description',
        existing_type=sa.String(length=500),
        nullable=True,
        server_default=None
    )