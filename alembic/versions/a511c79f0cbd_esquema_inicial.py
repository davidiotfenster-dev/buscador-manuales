"""esquema inicial

Revision ID: a511c79f0cbd
Revises: 
Create Date: 2026-09-11 13:16:44.177741

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision: str = 'a511c79f0cbd'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea el esquema completo sobre una base de datos vacía."""
    # Las extensiones van primero: el tipo vector no existe hasta que pgvector
    # está instalado, y las tablas de abajo declaran columnas vector(1536).
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Configuración de búsqueda en español insensible a acentos, usada por las
    # consultas de búsqueda léxica.
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'spanish_unaccent') THEN
                CREATE TEXT SEARCH CONFIGURATION spanish_unaccent (COPY = spanish);
                ALTER TEXT SEARCH CONFIGURATION spanish_unaccent
                    ALTER MAPPING FOR hword, hword_part, word
                    WITH unaccent, spanish_stem;
            END IF;
        END
        $$;
    """)

    op.create_table('manuales',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre_original', sa.String(), nullable=False),
    sa.Column('nombre_archivo', sa.String(), nullable=False),
    sa.Column('dispositivo', sa.String(), nullable=True),
    sa.Column('categoria', sa.String(), nullable=True),
    sa.Column('etiquetas', sa.Text(), nullable=True),
    sa.Column('num_paginas', sa.Integer(), nullable=True),
    sa.Column('nivel_acceso', sa.String(), nullable=True),
    sa.Column('fecha_subida', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('nombre_archivo')
    )
    op.create_index(op.f('ix_manuales_id'), 'manuales', ['id'], unique=False)
    op.create_table('ticket_contadores',
    sa.Column('anio', sa.Integer(), nullable=False),
    sa.Column('ultimo', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('anio')
    )
    op.create_table('tickets_sat',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('numero_ticket', sa.String(), nullable=False),
    sa.Column('instalador', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('telefono', sa.String(), nullable=True),
    sa.Column('obra', sa.String(), nullable=True),
    sa.Column('distribuidor', sa.String(), nullable=True),
    sa.Column('dispositivo', sa.String(), nullable=True),
    sa.Column('motor', sa.String(), nullable=True),
    sa.Column('sintoma', sa.Text(), nullable=False),
    sa.Column('diagnostico', sa.Text(), nullable=True),
    sa.Column('solucion', sa.Text(), nullable=True),
    sa.Column('estado', sa.String(), nullable=True),
    sa.Column('prioridad', sa.String(), nullable=True),
    sa.Column('creado_por', sa.String(), nullable=True),
    sa.Column('notas', sa.Text(), nullable=True),
    sa.Column('fecha_creacion', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('fecha_actualizacion', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=1536), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tickets_sat_estado'), 'tickets_sat', ['estado'], unique=False)
    op.create_index(op.f('ix_tickets_sat_id'), 'tickets_sat', ['id'], unique=False)
    op.create_index(op.f('ix_tickets_sat_instalador'), 'tickets_sat', ['instalador'], unique=False)
    op.create_index(op.f('ix_tickets_sat_numero_ticket'), 'tickets_sat', ['numero_ticket'], unique=True)
    op.create_table('usuarios',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('is_first_login', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_usuarios_email'), 'usuarios', ['email'], unique=True)
    op.create_index(op.f('ix_usuarios_id'), 'usuarios', ['id'], unique=False)
    op.create_table('videos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('video_id', sa.String(), nullable=False),
    sa.Column('titulo', sa.String(), nullable=False),
    sa.Column('canal', sa.String(), nullable=True),
    sa.Column('url', sa.String(), nullable=False),
    sa.Column('miniatura_url', sa.String(), nullable=True),
    sa.Column('dispositivo', sa.String(), nullable=True),
    sa.Column('categoria', sa.String(), nullable=True),
    sa.Column('etiquetas', sa.Text(), nullable=True),
    sa.Column('nivel_acceso', sa.String(), nullable=True),
    sa.Column('transcripcion_texto', sa.Text(), nullable=True),
    sa.Column('fecha_subida', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=1536), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_videos_id'), 'videos', ['id'], unique=False)
    op.create_index(op.f('ix_videos_video_id'), 'videos', ['video_id'], unique=True)
    op.create_table('paginas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('manual_id', sa.Integer(), nullable=True),
    sa.Column('numero_pagina', sa.Integer(), nullable=False),
    sa.Column('texto', sa.Text(), nullable=False),
    sa.Column('obtenido_por_ocr', sa.Boolean(), nullable=True),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=1536), nullable=True),
    sa.ForeignKeyConstraint(['manual_id'], ['manuales.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_paginas_id'), 'paginas', ['id'], unique=False)
    op.create_table('ticket_comentarios',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ticket_id', sa.Integer(), nullable=False),
    sa.Column('autor', sa.String(), nullable=False),
    sa.Column('texto', sa.Text(), nullable=False),
    sa.Column('tipo', sa.String(), nullable=True),
    sa.Column('metadata_json', sa.Text(), nullable=True),
    sa.Column('fecha', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['ticket_id'], ['tickets_sat.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ticket_comentarios_id'), 'ticket_comentarios', ['id'], unique=False)
    op.create_index(op.f('ix_ticket_comentarios_ticket_id'), 'ticket_comentarios', ['ticket_id'], unique=False)
    op.create_table('video_fragmentos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('video_id', sa.Integer(), nullable=True),
    sa.Column('segundo_inicio', sa.Integer(), nullable=False),
    sa.Column('duracion', sa.Integer(), nullable=True),
    sa.Column('texto', sa.Text(), nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=1536), nullable=True),
    sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_fragmentos_id'), 'video_fragmentos', ['id'], unique=False)
    op.create_index(op.f('ix_video_fragmentos_video_id'), 'video_fragmentos', ['video_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Elimina el esquema. No borra las extensiones: pueden usarlas otras bases."""
    op.drop_index(op.f('ix_video_fragmentos_video_id'), table_name='video_fragmentos')
    op.drop_index(op.f('ix_video_fragmentos_id'), table_name='video_fragmentos')
    op.drop_table('video_fragmentos')
    op.drop_index(op.f('ix_ticket_comentarios_ticket_id'), table_name='ticket_comentarios')
    op.drop_index(op.f('ix_ticket_comentarios_id'), table_name='ticket_comentarios')
    op.drop_table('ticket_comentarios')
    op.drop_index(op.f('ix_paginas_id'), table_name='paginas')
    op.drop_table('paginas')
    op.drop_index(op.f('ix_videos_video_id'), table_name='videos')
    op.drop_index(op.f('ix_videos_id'), table_name='videos')
    op.drop_table('videos')
    op.drop_index(op.f('ix_usuarios_id'), table_name='usuarios')
    op.drop_index(op.f('ix_usuarios_email'), table_name='usuarios')
    op.drop_table('usuarios')
    op.drop_index(op.f('ix_tickets_sat_numero_ticket'), table_name='tickets_sat')
    op.drop_index(op.f('ix_tickets_sat_instalador'), table_name='tickets_sat')
    op.drop_index(op.f('ix_tickets_sat_id'), table_name='tickets_sat')
    op.drop_index(op.f('ix_tickets_sat_estado'), table_name='tickets_sat')
    op.drop_table('tickets_sat')
    op.drop_table('ticket_contadores')
    op.drop_index(op.f('ix_manuales_id'), table_name='manuales')
    op.drop_table('manuales')
    # ### end Alembic commands ###
