"""add fecha_inactividad to alumnos

Revision ID: 0453fb292603
Revises: 06258af3b16c
Create Date: 2026-06-29 13:05:14.371787

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0453fb292603'
down_revision: Union[str, Sequence[str], None] = '06258af3b16c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Columna nueva — esto sí funciona directo en SQLite
    op.add_column('alumnos', sa.Column('fecha_inactividad', sa.DateTime(), nullable=True))

    # FK changes — usar batch mode para SQLite
    with op.batch_alter_table('detalles_alumno') as batch_op:
        batch_op.drop_constraint('detalles_alumno_alumno_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(None, 'alumnos', ['alumno_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('entrenamientos') as batch_op:
        batch_op.drop_constraint('entrenamientos_alumno_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(None, 'alumnos', ['alumno_id'], ['id'], ondelete='CASCADE')

    # NOT NULL en updated_at si lo detectó
    with op.batch_alter_table('usuarios') as batch_op:
        batch_op.alter_column('updated_at', existing_type=sa.DateTime(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('usuarios') as batch_op:
        batch_op.alter_column('updated_at', existing_type=sa.DateTime(), nullable=True)

    with op.batch_alter_table('entrenamientos') as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(None, 'alumnos', ['alumno_id'], ['id'])

    with op.batch_alter_table('detalles_alumno') as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(None, 'alumnos', ['alumno_id'], ['id'])

    op.drop_column('alumnos', 'fecha_inactividad')