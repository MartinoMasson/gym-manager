"""add updated_at

Revision ID: 06258af3b16c
Revises: f497471f388f
Create Date: 2026-06-28 23:52:35.793945

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '06258af3b16c'
down_revision: Union[str, Sequence[str], None] = 'f497471f388f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('updated_at', sa.DateTime(), nullable=True))

def downgrade() -> None:
    op.drop_column('usuarios', 'updated_at')
