"""cierre tecnico estructurado

Añade a tickets_sat los campos del cierre técnico (G10): qué resolvió la
incidencia y si la documentación existente bastó.

Todas las columnas son NULL. Eso es deliberado: NULL significa "este ticket no
se ha cerrado todavía", que no es lo mismo que "no se resolvió" ni que "la
documentación no fue suficiente". Los 47 tickets que ya existen quedan así, sin
cierre, y no contaminan las métricas de G15.

Las dos claves foráneas van nombradas a propósito. Alembic las autogenera sin
nombre, y entonces el downgrade emite DROP CONSTRAINT None, que PostgreSQL
rechaza.

Revision ID: eec0dc7833f3
Revises: 3f514b913e75
Create Date: 2026-09-14 09:40:15.168606

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eec0dc7833f3'
down_revision: Union[str, Sequence[str], None] = '3f514b913e75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FK_MANUAL = "fk_tickets_sat_cierre_manual_id_manuales"
FK_VIDEO = "fk_tickets_sat_cierre_video_id_videos"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tickets_sat', sa.Column('cierre_resuelto', sa.Boolean(), nullable=True))
    op.add_column('tickets_sat', sa.Column('cierre_descripcion', sa.Text(), nullable=True))
    op.add_column('tickets_sat', sa.Column('cierre_doc_suficiente', sa.Boolean(), nullable=True))
    op.add_column('tickets_sat', sa.Column('cierre_manual_id', sa.Integer(), nullable=True))
    op.add_column('tickets_sat', sa.Column('cierre_video_id', sa.Integer(), nullable=True))
    op.add_column('tickets_sat', sa.Column('cierre_doc_texto', sa.Text(), nullable=True))
    op.add_column('tickets_sat', sa.Column('cierre_alternativa', sa.Text(), nullable=True))
    op.add_column('tickets_sat', sa.Column('cierre_escalado', sa.Boolean(), nullable=True))
    op.add_column('tickets_sat', sa.Column('cierre_fecha', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tickets_sat', sa.Column('cierre_por', sa.String(), nullable=True))
    op.create_index(op.f('ix_tickets_sat_cierre_manual_id'), 'tickets_sat', ['cierre_manual_id'], unique=False)
    op.create_index(op.f('ix_tickets_sat_cierre_video_id'), 'tickets_sat', ['cierre_video_id'], unique=False)
    # ondelete SET NULL: borrar un manual no puede llevarse por delante el ticket
    # que lo citó. Se pierde el enlace, pero el cierre y su texto se conservan.
    op.create_foreign_key(FK_MANUAL, 'tickets_sat', 'manuales', ['cierre_manual_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key(FK_VIDEO, 'tickets_sat', 'videos', ['cierre_video_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(FK_VIDEO, 'tickets_sat', type_='foreignkey')
    op.drop_constraint(FK_MANUAL, 'tickets_sat', type_='foreignkey')
    op.drop_index(op.f('ix_tickets_sat_cierre_video_id'), table_name='tickets_sat')
    op.drop_index(op.f('ix_tickets_sat_cierre_manual_id'), table_name='tickets_sat')
    for columna in (
        'cierre_por', 'cierre_fecha', 'cierre_escalado', 'cierre_alternativa',
        'cierre_doc_texto', 'cierre_video_id', 'cierre_manual_id',
        'cierre_doc_suficiente', 'cierre_descripcion', 'cierre_resuelto',
    ):
        op.drop_column('tickets_sat', columna)
