"""Qué toca y qué no toca la rotación de la clave de firma.

Un fichero de configuración a medias deja el stack sin arrancar —`SECRET_KEY`
lleva `:?` en el compose— así que lo que importa aquí no es que rote, sino que
**cuando no está seguro no escriba nada**: sin línea que sustituir, o con más
de una, se sale sin tocar el fichero.
"""

import pytest

from tools import rotar_secret_key as rsk


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(rsk, "ENV", tmp_path / ".env")
    monkeypatch.setattr(rsk, "COPIAS", tmp_path / "copias")
    return tmp_path


def _env(repo, texto):
    (repo / ".env").write_text(texto, encoding="utf-8")


def _clave(repo):
    for linea in (repo / ".env").read_text(encoding="utf-8").splitlines():
        if linea.startswith("SECRET_KEY="):
            return linea[len("SECRET_KEY="):]
    return None


def test_cambia_la_clave_y_deja_el_resto_igual(repo, monkeypatch):
    _env(repo, "POSTGRES_PASSWORD=algo\nSECRET_KEY=filtrada\nTOKEN_EXPIRE_MINUTES=1440\n")
    monkeypatch.setattr("sys.argv", ["rotar"])

    assert rsk.main() == 0

    lineas = (repo / ".env").read_text(encoding="utf-8").splitlines()
    assert lineas[0] == "POSTGRES_PASSWORD=algo"
    assert lineas[2] == "TOKEN_EXPIRE_MINUTES=1440"
    assert _clave(repo) not in ("filtrada", "", None)
    assert len(_clave(repo)) > 60


def test_guarda_la_anterior_antes_de_pisarla(repo, monkeypatch):
    _env(repo, "SECRET_KEY=filtrada\n")
    monkeypatch.setattr("sys.argv", ["rotar"])

    rsk.main()

    respaldos = list((repo / "copias").iterdir())
    assert len(respaldos) == 1
    assert "SECRET_KEY=filtrada" in respaldos[0].read_text(encoding="utf-8")


def test_sin_linea_que_sustituir_no_escribe_nada(repo, monkeypatch):
    """Crear la clave donde no había significaría que este no es el .env que
    usa el stack. Mejor salir que dejar dos ficheros de configuración
    distintos y que nadie sepa cuál manda."""
    _env(repo, "POSTGRES_PASSWORD=algo\n")
    monkeypatch.setattr("sys.argv", ["rotar"])

    assert rsk.main() == 1
    assert (repo / ".env").read_text(encoding="utf-8") == "POSTGRES_PASSWORD=algo\n"
    assert not (repo / "copias").exists()


def test_sin_env_no_hace_nada(repo, monkeypatch):
    monkeypatch.setattr("sys.argv", ["rotar"])

    assert rsk.main() == 1
    assert not (repo / ".env").exists()


def test_dry_run_no_toca_el_fichero(repo, monkeypatch):
    _env(repo, "SECRET_KEY=filtrada\n")
    monkeypatch.setattr("sys.argv", ["rotar", "--dry-run"])

    assert rsk.main() == 0
    assert _clave(repo) == "filtrada"
    assert not (repo / "copias").exists()


def test_dos_rotaciones_seguidas_dan_claves_distintas(repo, monkeypatch):
    _env(repo, "SECRET_KEY=filtrada\n")
    monkeypatch.setattr("sys.argv", ["rotar"])

    rsk.main()
    primera = _clave(repo)
    rsk.main()

    assert _clave(repo) != primera
