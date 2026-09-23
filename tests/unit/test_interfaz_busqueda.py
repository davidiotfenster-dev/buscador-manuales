"""Lo que la interfaz tiene que hacer con lo nuevo del buscador y del triaje.

No hay runner de JavaScript en el proyecto; esto comprueba que el código que
consume los campos nuevos existe, que es lo que se perdería sin avisar.
"""

import re
from pathlib import Path

import pytest

APP_JS = Path(__file__).resolve().parent.parent.parent / "app" / "static" / "app.js"


@pytest.fixture(scope="module")
def js():
    codigo = APP_JS.read_text(encoding="utf-8")
    sin_bloque = re.sub(r"/\*.*?\*/", "", codigo, flags=re.S)
    return "\n".join(re.sub(r"(^|\s)//.*$", "", l) for l in sin_bloque.splitlines())


def test_una_respuesta_atrasada_no_pisa_a_la_mas_nueva(js):
    """Dos Intro seguidos: la primera respuesta puede llegar la última."""
    assert "secuenciaBusqueda" in js
    assert js.count("miBusqueda !== secuenciaBusqueda") >= 2  # en el éxito y en el error


def test_si_se_corrige_una_errata_se_dice(js):
    """Buscar otra palabra sin avisar confunde más que ayuda."""
    assert "data.correcciones" in js


def test_el_grupo_probable_se_ensena_como_candidato_si_no_es_fiable(js):
    """Por debajo de 0,6 de confianza acierta el 61 % o menos: no es un veredicto."""
    assert "data.grupo_probable" in js
    assert "gp.fiable" in js
