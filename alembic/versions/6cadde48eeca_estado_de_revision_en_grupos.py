"""estado de revision en grupos

Anade incident_groups.estado_revision para poder distinguir la taxonomia
validada de la que esta a prueba: los 9 grupos sembrados salen del analisis de
119 incidencias reales y son 'estable', mientras que los que cree SAT sobre la
marcha nacen 'nuevo' y pueden pasar a 'en_revision'.

La columna es NOT NULL, asi que lleva server_default: sin el, ALTER TABLE falla
sobre las 9 filas que ya existen. El default se retira despues de rellenarlas,
para que sea el modelo quien decida el valor de las nuevas y no la base de datos.

Revision ID: 6cadde48eeca
Revises: 31314c06dfbc
Create Date: 2026-09-14 10:24:11.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6cadde48eeca'
down_revision: Union[str, Sequence[str], None] = '31314c06dfbc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'incident_groups',
        sa.Column('estado_revision', sa.String(), nullable=False, server_default='estable'),
    )
    op.alter_column('incident_groups', 'estado_revision', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('incident_groups', 'estado_revision')
