"""columnas generadas tsvector e indices GIN/trigram

Estas columnas son GENERATED ALWAYS AS ... STORED, así que no se pueden declarar
como atributos de los modelos SQLAlchemy: van aquí con SQL explícito. Antes de
introducirlas, cada búsqueda recalculaba to_tsvector sobre toda la tabla y el
listado de tickets filtraba con ILIKE '%...%' sin ningún índice.

Revision ID: b1f4c2d93e77
Revises: a511c79f0cbd
Create Date: 2026-09-11

"""
from typing import Sequence, Union

from alembic import op

revision: str = "b1f4c2d93e77"
down_revision: Union[str, Sequence[str], None] = "a511c79f0cbd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Columnas de búsqueda por tabla: (tabla, columna, expresión generadora)
COLUMNAS_TSV = [
    ("paginas", "texto_tsv", "to_tsvector('spanish', texto)"),
    (
        "manuales",
        "metadatos_tsv",
        "to_tsvector('spanish', nombre_original || ' ' || COALESCE(dispositivo,'') "
        "|| ' ' || COALESCE(categoria,'') || ' ' || COALESCE(etiquetas,''))",
    ),
    (
        "videos",
        "metadatos_tsv",
        "to_tsvector('spanish', titulo || ' ' || COALESCE(dispositivo,'') "
        "|| ' ' || COALESCE(categoria,'') || ' ' || COALESCE(etiquetas,''))",
    ),
    ("videos", "transcripcion_tsv", "to_tsvector('spanish', COALESCE(transcripcion_texto,''))"),
    ("video_fragmentos", "texto_tsv", "to_tsvector('spanish', texto)"),
    (
        "tickets_sat",
        "busqueda_tsv",
        "to_tsvector('spanish', sintoma || ' ' || COALESCE(diagnostico,'') "
        "|| ' ' || COALESCE(solucion,''))",
    ),
]

# Índices GIN sobre las columnas generadas: (nombre, tabla, columna)
INDICES_GIN = [
    ("idx_paginas_tsv", "paginas", "texto_tsv"),
    ("idx_manuales_tsv", "manuales", "metadatos_tsv"),
    ("idx_videos_tsv", "videos", "metadatos_tsv"),
    ("idx_videos_transcripcion_tsv", "videos", "transcripcion_tsv"),
    ("idx_video_fragmentos_tsv", "video_fragmentos", "texto_tsv"),
    ("idx_tickets_busqueda_tsv", "tickets_sat", "busqueda_tsv"),
]

# Columnas de tickets_sat que el listado filtra con ILIKE '%...%'
COLUMNAS_TRIGRAM = (
    "numero_ticket",
    "instalador",
    "email",
    "telefono",
    "obra",
    "dispositivo",
    "distribuidor",
    "sintoma",
    "diagnostico",
)


def upgrade() -> None:
    """Añade las columnas generadas tsvector y sus índices."""
    for tabla, columna, expresion in COLUMNAS_TSV:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = '{tabla}' AND column_name = '{columna}'
                ) THEN
                    ALTER TABLE {tabla} ADD COLUMN {columna} tsvector
                        GENERATED ALWAYS AS ({expresion}) STORED;
                END IF;
            END
            $$;
            """
        )

    for nombre, tabla, columna in INDICES_GIN:
        op.execute(f"CREATE INDEX IF NOT EXISTS {nombre} ON {tabla} USING GIN ({columna});")

    for columna in COLUMNAS_TRIGRAM:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS idx_tickets_trgm_{columna} "
            f"ON tickets_sat USING GIN ({columna} gin_trgm_ops);"
        )


def downgrade() -> None:
    """Elimina los índices y las columnas generadas."""
    for columna in COLUMNAS_TRIGRAM:
        op.execute(f"DROP INDEX IF EXISTS idx_tickets_trgm_{columna};")

    for nombre, _tabla, _columna in INDICES_GIN:
        op.execute(f"DROP INDEX IF EXISTS {nombre};")

    for tabla, columna, _expresion in COLUMNAS_TSV:
        op.execute(f"ALTER TABLE {tabla} DROP COLUMN IF EXISTS {columna};")
