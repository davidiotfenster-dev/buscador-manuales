"""Piezas del buscador que no necesitan base de datos."""

import pytest

from app.busqueda import (
    UMBRAL_CORRECCION,
    _literal,
    distancia_edicion,
    similitud_trigramas,
    variantes_palabra,
)


@pytest.mark.parametrize("sin, con", [
    ("instalacion", "instalación"),
    ("configuracion", "configuración"),
    ("bateria", "batería"),
])
def test_una_palabra_sin_tilde_se_busca_tambien_con_ella(sin, con):
    """El extractor de raíces solo reconoce «-ación» con tilde: sin ella,
    «instalacion» no comparte raíz con «instalar»."""
    assert con in variantes_palabra(sin)


def test_una_palabra_con_tilde_se_busca_tambien_sin_ella():
    """Por los textos escritos sin tildes, que son casi todos los tickets."""
    assert "vinculacion" in variantes_palabra("vinculación")


def test_una_palabra_sin_sufijo_acentuable_no_se_toca():
    assert variantes_palabra("motor") == ["motor"]


@pytest.mark.parametrize("a, b, cambios", [
    ("vinuclar", "vincular", 1),
    ("perisana", "persiana", 1),
    ("alexxa", "alexa", 1),
    ("persiana", "persiana", 0),
    ("router", "persiana", 7),
])
def test_la_distancia_cuenta_el_intercambio_de_letras_como_un_cambio(a, b, cambios):
    assert distancia_edicion(a, b) == cambios


def test_los_trigramas_separan_parecido_de_distinto():
    assert similitud_trigramas("calibarcion", "calibracion") >= UMBRAL_CORRECCION
    assert similitud_trigramas("persiana", "router") < UMBRAL_CORRECCION


def test_un_lexema_con_comilla_no_rompe_la_consulta():
    """Se castea a tsquery tal cual: una comilla sin escapar sería un error de sintaxis."""
    barra = chr(92)
    assert _literal("o'neil") == "'o''neil'"
    assert _literal("a" + barra + "b") == "'a" + barra * 2 + "b'"


def test_una_palabra_que_el_extractor_ya_iguala_no_necesita_variante():
    """«conexión» y «conexion» dan la misma raíz: no hace falta probar las dos."""
    assert variantes_palabra("conexion") == ["conexion"]
