"""Entorno de Alembic para Buscador de Manuales.

La URL de la base de datos NO se lee de alembic.ini: se toma de la misma variable
DATABASE_URL que usa la aplicación, para que las migraciones apunten siempre al
mismo sitio que el código.
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# La raíz del proyecto debe estar en sys.path para poder importar app.database
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.database import DATABASE_URL, Base  # noqa: E402

config = context.config

# Si quien invoca ya ha fijado una URL (la suite de tests apunta a su propia base
# de datos), se respeta. Si no, se usa la misma que la aplicación.
_url_configurada = config.get_main_option("sqlalchemy.url", "") or ""
if not _url_configurada or _url_configurada.startswith("driver://"):
    config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """Excluye de la comparación lo que Alembic no puede derivar de los modelos.

    Dos familias de objetos se crean con SQL explícito en sus propias revisiones
    y no existen como atributos de los modelos, así que sin este filtro cada
    autogenerate propondría borrarlas:

    - Las columnas tsvector, que son GENERATED ALWAYS AS ... STORED.
    - Los índices GIN y trigram que las acompañan, cuyo nombre empieza por idx_
      (los que sí derivan de los modelos los nombra SQLAlchemy como ix_).
    """
    if type_ == "column" and name.endswith("_tsv"):
        return False
    if type_ == "index" and name and name.startswith("idx_"):
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
