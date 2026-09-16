"""Qué sale y qué no sale en el paquete que se le pasa a otra persona.

Un fallo aquí no se ve en esta máquina: se ve en la del compañero, que es
donde peor se arregla. Los dos que importan ya ocurrieron al construirlo.

El primero: excluir la tabla `usuarios` entera parecía más limpio, pero el
volcado trae `alembic_version` al día, así que Alembic daría el esquema por
hecho y no crearía la tabla que falta — y la aplicación revienta al buscar el
admin. La tabla tiene que viajar, vacía.

El segundo: el guardián que busca hashes saltaba con el `CREATE TABLE`, porque
ahí aparece la **columna** `password_hash` de forma legítima. Un guardián que
salta siempre acaba desactivado, y entonces no guarda nada.
"""

import gzip

import pytest

from tools import paquete_companero as pc

CABECERA = b"--\n-- PostgreSQL database dump\n--\n"
PIE = pc.MARCA_FINAL.encode() + b"\n"

ESQUEMA_USUARIOS = (
    b"CREATE TABLE public.usuarios (\n"
    b"    id integer NOT NULL,\n"
    b"    email character varying,\n"
    b"    password_hash character varying,\n"
    b"    role character varying\n"
    b");\n"
)


def _volcado(*cuerpo: bytes) -> bytes:
    return CABECERA + b"".join(cuerpo) + PIE


@pytest.fixture
def dump(monkeypatch):
    """Sustituye pg_dump por un volcado controlado."""
    def poner(sql: bytes, returncode: int = 0):
        monkeypatch.setattr(pc, "_compose",
                            lambda *a, **k: _Proc(returncode, sql))
    return poner


def test_se_excluyen_los_datos_y_no_la_tabla(monkeypatch, tmp_path):
    """La bandera importa: --exclude-table dejaría al otro sin tabla."""
    vistos = {}

    def falso(*args, **kwargs):
        vistos["args"] = args
        return _Proc(0, _volcado(ESQUEMA_USUARIOS))

    monkeypatch.setattr(pc, "_compose", falso)
    pc.volcar_sin_usuarios(tmp_path / "datos.sql.gz")

    assert "--exclude-table-data" in vistos["args"]
    assert "--exclude-table" not in vistos["args"]


def test_el_esquema_de_usuarios_si_viaja(dump, tmp_path):
    """Sin el CREATE TABLE, Alembic no la crearía: está al día en el volcado."""
    dump(_volcado(ESQUEMA_USUARIOS))

    pc.volcar_sin_usuarios(tmp_path / "datos.sql.gz")

    escrito = gzip.open(tmp_path / "datos.sql.gz", "rb").read()
    assert b"CREATE TABLE public.usuarios" in escrito


def test_el_nombre_de_la_columna_no_hace_saltar_el_guardian(dump, tmp_path):
    """`password_hash` está en el CREATE TABLE de forma legítima. Un guardián
    que salta siempre acaba desactivado."""
    dump(_volcado(ESQUEMA_USUARIOS))

    pc.volcar_sin_usuarios(tmp_path / "datos.sql.gz")

    assert (tmp_path / "datos.sql.gz").exists()


@pytest.mark.parametrize("prefijo", [b"$2b$", b"$2a$"])
def test_un_hash_de_verdad_lo_para(dump, tmp_path, prefijo):
    fila = b"1\tadmin@empresa.com\t" + prefijo + b"12$abcdefghijklmnop\tadmin\n"
    dump(_volcado(ESQUEMA_USUARIOS, b"COPY public.usuarios ...\n", fila))

    with pytest.raises(RuntimeError, match="hashes"):
        pc.volcar_sin_usuarios(tmp_path / "datos.sql.gz")

    assert not (tmp_path / "datos.sql.gz").exists()


def test_un_volcado_cortado_no_se_empaqueta(dump, tmp_path):
    dump(CABECERA + ESQUEMA_USUARIOS)  # sin la marca final

    with pytest.raises(RuntimeError, match="incompleto"):
        pc.volcar_sin_usuarios(tmp_path / "datos.sql.gz")

    assert not (tmp_path / "datos.sql.gz").exists()


def test_si_pg_dump_falla_no_queda_fichero(dump, tmp_path):
    dump(b"", returncode=1)

    with pytest.raises(RuntimeError, match="pg_dump"):
        pc.volcar_sin_usuarios(tmp_path / "datos.sql.gz")

    assert not (tmp_path / "datos.sql.gz").exists()


def test_el_leeme_no_manda_copiar_el_env_de_aqui(dump, tmp_path):
    """El .env lleva la SECRET_KEY con la que se firman los tokens de aquí.
    Las instrucciones tienen que decirle que genere la suya."""
    assert ".env.example" in pc.LEEME
    assert "secrets.token_urlsafe" in pc.LEEME
    assert "nombres reales de instaladores" in pc.LEEME


class _Proc:
    def __init__(self, returncode, stdout=b"", stderr=b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
