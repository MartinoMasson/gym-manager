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
    op.add_column('alumnos', sa.Column('fecha_inactividad', sa.DateTime(), nullable=True))

    naming_convention = {"fk": "%(table_name)s_%(column_0_name)s_fkey"}

    with op.batch_alter_table('detalles_alumno', naming_convention=naming_convention) as batch_op:
        batch_op.drop_constraint('detalles_alumno_alumno_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(
            'detalles_alumno_alumno_id_fkey',
            'alumnos', ['alumno_id'], ['id'], ondelete='CASCADE'
        )

    with op.batch_alter_table('entrenamientos', naming_convention=naming_convention) as batch_op:
        batch_op.drop_constraint('entrenamientos_alumno_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(
            'entrenamientos_alumno_id_fkey',
            'alumnos', ['alumno_id'], ['id'], ondelete='CASCADE'
        )

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