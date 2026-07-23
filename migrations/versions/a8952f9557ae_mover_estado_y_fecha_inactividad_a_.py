"""mover estado y fecha_inactividad a usuarios

Revision ID: a8952f9557ae
Revises: a3f05e42006f
Create Date: 2026-07-22 01:12:36.798895

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a8952f9557ae'
down_revision: Union[str, Sequence[str], None] = 'a3f05e42006f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('alumnos') as batch_op:
        batch_op.drop_column('estado')
        batch_op.drop_column('fecha_inactividad')

    with op.batch_alter_table('usuarios') as batch_op:
        batch_op.add_column(sa.Column('estado', sa.Integer(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('fecha_inactividad', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('usuarios') as batch_op:
        batch_op.drop_column('fecha_inactividad')
        batch_op.drop_column('estado')

    with op.batch_alter_table('alumnos') as batch_op:
        batch_op.add_column(sa.Column('estado', sa.Integer(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('fecha_inactividad', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###
