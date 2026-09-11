"""
Fixtures y configuración compartida de Pytest para Buscador de Manuales.
"""

import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Asegurar que la raíz del proyecto está en sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Clave fija de prueba para generación determinista de tokens
os.environ["SECRET_KEY"] = "clave-secreta-para-tests-rbac-1234567890"

from app.main import app, create_access_token, MANUALES_DIR
from app import database


# ---------------------------------------------------------------------------
# Base de datos de pruebas
#
# Los tests de API mockean database.SessionLocal, asi que validan el mock y no
# el SQL. Estas piezas dan una base de datos PostgreSQL real, creada desde cero
# con las migraciones de Alembic y destruida al terminar, para los tests que
# necesitan ejercitar consultas de verdad.
# ---------------------------------------------------------------------------

NOMBRE_BD_PRUEBAS = "buscador_manuales_test"


def _leer_variable_env_local(nombre: str) -> str:
    """Lee una variable del .env del proyecto (pytest no lo carga por si solo)."""
    fichero = BASE_DIR / ".env"
    if not fichero.exists():
        return ""
    for linea in fichero.read_text(encoding="utf-8").splitlines():
        if linea.startswith(f"{nombre}="):
            return linea.split("=", 1)[1].strip()
    return ""


def _url_bd_pruebas() -> str:
    """URL de la base de datos de pruebas, o cadena vacia si no se puede componer."""
    explicita = os.environ.get("TEST_DATABASE_URL", "").strip()
    if explicita:
        return explicita
    password = _leer_variable_env_local("POSTGRES_PASSWORD")
    if not password:
        return ""
    return f"postgresql://postgres:{password}@127.0.0.1:5432/{NOMBRE_BD_PRUEBAS}"


@pytest.fixture(scope="session")
def url_bd_pruebas():
    """Crea la base de datos de pruebas, le aplica las migraciones y la destruye.

    Si PostgreSQL no esta accesible (stack parado, o CI sin servicio de base de
    datos), los tests que dependan de este fixture se omiten en lugar de fallar.
    """
    import sqlalchemy
    from alembic import command
    from alembic.config import Config

    url = _url_bd_pruebas()
    if not url:
        pytest.skip("Sin TEST_DATABASE_URL ni POSTGRES_PASSWORD en .env")

    url_admin = url.rsplit("/", 1)[0] + "/postgres"
    motor_admin = sqlalchemy.create_engine(url_admin, isolation_level="AUTOCOMMIT")
    try:
        with motor_admin.connect() as conn:
            conn.execute(sqlalchemy.text(f'DROP DATABASE IF EXISTS "{NOMBRE_BD_PRUEBAS}"'))
            conn.execute(sqlalchemy.text(f'CREATE DATABASE "{NOMBRE_BD_PRUEBAS}"'))
    except sqlalchemy.exc.OperationalError as e:
        pytest.skip(f"PostgreSQL no accesible para los tests: {e}")

    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")

    yield url

    with motor_admin.connect() as conn:
        conn.execute(sqlalchemy.text(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname = '{NOMBRE_BD_PRUEBAS}' AND pid <> pg_backend_pid()"
        ))
        conn.execute(sqlalchemy.text(f'DROP DATABASE IF EXISTS "{NOMBRE_BD_PRUEBAS}"'))
    motor_admin.dispose()


@pytest.fixture
def db(url_bd_pruebas):
    """Sesion contra la base de datos de pruebas, con las tablas vaciadas antes de cada test."""
    import sqlalchemy
    from sqlalchemy.orm import sessionmaker

    motor = sqlalchemy.create_engine(url_bd_pruebas)
    with motor.connect() as conn:
        conn.execute(sqlalchemy.text(
            "TRUNCATE ticket_comentarios, tickets_sat, ticket_contadores, "
            "video_fragmentos, videos, paginas, manuales, usuarios RESTART IDENTITY CASCADE"
        ))
        conn.commit()

    sesion = sessionmaker(bind=motor)()
    try:
        yield sesion
    finally:
        sesion.close()
        motor.dispose()


@pytest.fixture(scope="session")
def client():
    """
    Cliente HTTP de prueba para interactuar con la aplicación FastAPI.

    El arranque (lifespan) se neutraliza a propósito: init_db() crea el esquema y
    sincronizar_manuales() reindexa los PDF con OCR, y ambos actuarían sobre la base
    de datos de desarrollo real. La suite mockea database.SessionLocal, así que no
    necesita esquema; lo que necesita es no tocar datos de verdad.
    """
    original_init_db = database.init_db
    database.init_db = lambda: None
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        database.init_db = original_init_db

@pytest.fixture
def test_manuals_dir(tmp_path, monkeypatch):
    """
    Crea un directorio temporal de manuales con archivos PDF reales de prueba
    y parchea app.main.MANUALES_DIR para aislar completamente los tests del disco.
    """
    manuales_tmp = tmp_path / "manuales"
    manuales_tmp.mkdir(parents=True, exist_ok=True)

    # Crear PDF público ficticio
    pdf_publico = manuales_tmp / "manual_publico.pdf"
    pdf_publico.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")

    # Crear PDF técnico ficticio
    pdf_tecnico = manuales_tmp / "manual_tecnico.pdf"
    pdf_tecnico.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")

    # Parchear MANUALES_DIR en app.main
    monkeypatch.setattr("app.main.MANUALES_DIR", manuales_tmp)

    # Diccionario en memoria con metadatos de los manuales de prueba
    manuales_db = {
        "manual_publico.pdf": {
            "id": 101,
            "nombre_original": "Manual Usuario Publico.pdf",
            "nombre_archivo": "manual_publico.pdf",
            "dispositivo": "C-PULSAR",
            "categoria": "Manuales de Usuario",
            "nivel_acceso": "publico",
            "etiquetas": "comercial, basico"
        },
        "manual_tecnico.pdf": {
            "id": 102,
            "nombre_original": "Manual Tecnico Avanzado.pdf",
            "nombre_archivo": "manual_tecnico.pdf",
            "dispositivo": "C-PULSAR",
            "categoria": "Esquemas y Firmware",
            "nivel_acceso": "tecnico",
            "etiquetas": "tecnico, esquemas, circuito"
        }
    }

    def mock_obtener_manual_por_archivo(nombre_archivo: str):
        return manuales_db.get(nombre_archivo)

    def mock_obtener_manual(manual_id: int):
        for m in manuales_db.values():
            if m["id"] == manual_id:
                return m
        return None

    monkeypatch.setattr(database, "obtener_manual_por_archivo", mock_obtener_manual_por_archivo)
    monkeypatch.setattr(database, "obtener_manual", mock_obtener_manual)

    cache_tmp = tmp_path / "cache_miniaturas"
    cache_tmp.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("app.main.CACHE_MINIATURAS_DIR", cache_tmp)

    return {
        "dir": manuales_tmp,
        "cache_dir": cache_tmp,
        "publico": "manual_publico.pdf",
        "tecnico": "manual_tecnico.pdf",
        "db": manuales_db
    }

@pytest.fixture
def mock_users(monkeypatch):
    """
    Crea usuarios ficticios y tokens JWT asociados con roles admin, tecnico y comercial.
    Simula la consulta a SessionLocal para resolver el usuario por email.
    """
    usuarios = {
        "comercial@iotfenster.es": database.User(
            id=1, email="comercial@iotfenster.es", role="comercial", is_first_login=False
        ),
        "tecnico@iotfenster.es": database.User(
            id=2, email="tecnico@iotfenster.es", role="tecnico", is_first_login=False
        ),
        "admin@iotfenster.es": database.User(
            id=3, email="admin@iotfenster.es", role="admin", is_first_login=False
        )
    }

    token_comercial = create_access_token(data={"sub": "comercial@iotfenster.es", "role": "comercial"})
    token_tecnico = create_access_token(data={"sub": "tecnico@iotfenster.es", "role": "tecnico"})
    token_admin = create_access_token(data={"sub": "admin@iotfenster.es", "role": "admin"})

    class MockQuery:
        def __init__(self, model):
            self.model = model
            self._filter_email = None

        def filter(self, *criterion):
            for c in criterion:
                # Extraer valor de comparación si es User.email == email
                if hasattr(c, "right") and hasattr(c.right, "value"):
                    self._filter_email = c.right.value
            return self

        def first(self):
            if self._filter_email:
                return usuarios.get(self._filter_email)
            return None

    class MockSession:
        def query(self, model):
            return MockQuery(model)

        def close(self):
            pass

    monkeypatch.setattr(database, "SessionLocal", lambda: MockSession())

    return {
        "tokens": {
            "comercial": token_comercial,
            "tecnico": token_tecnico,
            "admin": token_admin
        },
        "headers": {
            "comercial": {"Authorization": f"Bearer {token_comercial}"},
            "tecnico": {"Authorization": f"Bearer {token_tecnico}"},
            "admin": {"Authorization": f"Bearer {token_admin}"}
        }
    }
