"""Qué borra la rotación de copias y qué volcados se rechazan.

Las dos cosas que pueden salir mal en una copia de seguridad son silenciosas:
que la rotación se lleve por delante una copia que alguien guardó a propósito,
y que se archive un volcado cortado a medias que solo se descubre el día que
hace falta restaurar. Las dos se comprueban aquí sin tocar Docker: la rotación
trabaja sobre ficheros, y el rechazo del volcado incompleto depende solo de si
aparece la marca final de pg_dump.
"""

import gzip
from pathlib import Path

import pytest

from tools import copia_seguridad


def _copia(carpeta: Path, nombre: str) -> Path:
    ruta = carpeta / nombre
    ruta.write_bytes(b"x")
    return ruta


@pytest.fixture
def carpeta(tmp_path, monkeypatch):
    monkeypatch.setattr(copia_seguridad, "DESTINO", tmp_path)
    return tmp_path


def test_rota_las_mas_antiguas_y_conserva_las_ultimas(carpeta):
    for dia in range(1, 6):
        _copia(carpeta, f"buscador_manuales_2026-09-0{dia}_0300.sql.gz")

    borradas = copia_seguridad.rotar(conservar=2)

    assert [b.name for b in borradas] == [
        "buscador_manuales_2026-09-01_0300.sql.gz",
        "buscador_manuales_2026-09-02_0300.sql.gz",
        "buscador_manuales_2026-09-03_0300.sql.gz",
    ]
    quedan = sorted(p.name for p in carpeta.iterdir())
    assert quedan == [
        "buscador_manuales_2026-09-04_0300.sql.gz",
        "buscador_manuales_2026-09-05_0300.sql.gz",
    ]


def test_no_toca_las_copias_puestas_a_mano(carpeta):
    """Una copia guardada antes de algo delicado no puede caducar sola.

    `tickets_antes_de_importar_2026-09-14.sql` se hizo justo antes de importar
    el histórico. Es exactamente la que haría falta si la importación hubiera
    salido mal, y no lleva el nombre que genera el script.
    """
    a_mano = _copia(carpeta, "tickets_antes_de_importar_2026-09-14.sql")
    otra = _copia(carpeta, "antes_de_migrar.sql.gz")
    for dia in range(1, 4):
        _copia(carpeta, f"buscador_manuales_2026-09-0{dia}_0300.sql.gz")

    copia_seguridad.rotar(conservar=1)

    assert a_mano.exists()
    assert otra.exists()


def test_conservar_cero_no_borra_nada(carpeta):
    """Un 0 mal pasado no puede vaciar la carpeta entera."""
    _copia(carpeta, "buscador_manuales_2026-09-01_0300.sql.gz")

    assert copia_seguridad.rotar(conservar=0) == []
    assert len(list(carpeta.iterdir())) == 1


def test_rechaza_el_volcado_incompleto(carpeta, monkeypatch):
    """Un pg_dump cortado no se guarda: sería una copia falsa."""
    monkeypatch.setattr(
        copia_seguridad, "_compose",
        lambda *a, **k: _Proc(0, b"CREATE TABLE tickets_sat (\n"),
    )

    with pytest.raises(RuntimeError, match="incompleto"):
        copia_seguridad.volcar(carpeta / "salida.sql.gz")

    assert not (carpeta / "salida.sql.gz").exists()


def test_guarda_y_comprime_el_volcado_completo(carpeta, monkeypatch):
    sql = b"CREATE TABLE tickets_sat ();\n" + copia_seguridad.MARCA_FINAL.encode() + b"\n"
    monkeypatch.setattr(copia_seguridad, "_compose", lambda *a, **k: _Proc(0, sql))

    destino = copia_seguridad.volcar(carpeta / "salida.sql.gz")

    assert gzip.open(destino, "rb").read() == sql


def test_el_fallo_de_pg_dump_no_deja_fichero(carpeta, monkeypatch):
    monkeypatch.setattr(
        copia_seguridad, "_compose",
        lambda *a, **k: _Proc(1, b"", b"could not connect to server"),
    )

    with pytest.raises(RuntimeError, match="pg_dump"):
        copia_seguridad.volcar(carpeta / "salida.sql.gz")

    assert not (carpeta / "salida.sql.gz").exists()


class _Proc:
    def __init__(self, returncode, stdout=b"", stderr=b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
