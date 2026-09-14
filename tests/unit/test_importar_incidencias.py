"""Traducción de las etiquetas de SAT a grupos de incidencia.

De `data/sat/Incidencias.xlsx` salieron los 9 grupos, y su columna «Problema»
trae las etiquetas que puso SAT a mano. La clasificación del histórico no se
inventa: se traduce. Estas reglas son las que deciden en qué grupo acaba cada
una de las 119 incidencias, así que conviene que no cambien por accidente.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ / "tools"))

from importar_incidencias import grupos_de_etiquetas  # noqa: E402


def test_una_etiqueta_da_su_grupo():
    assert grupos_de_etiquetas("Vinculación") == ["VINCULACION"]


def test_las_etiquetas_llegan_con_y_sin_acento():
    """El Excel mezcla ambas formas según quién escribiera la fila."""
    assert grupos_de_etiquetas("Aplicacion") == ["APP"]
    assert grupos_de_etiquetas("Aplicación") == ["APP"]
    assert grupos_de_etiquetas("  INSTALACIÓN  ") == ["INSTALACION"]


def test_wifi_y_conexion_caen_en_el_mismo_grupo_sin_duplicarlo():
    """Ambas son problemas de enlace; se fusionaron en CONECTIVIDAD (G2.1)."""
    assert grupos_de_etiquetas("Wifi, Conexión") == ["CONECTIVIDAD"]


def test_el_primero_de_la_lista_es_el_principal():
    """El 46 % de las incidencias lleva más de una etiqueta."""
    assert grupos_de_etiquetas("Pulsador, Vinculación") == ["PULSADOR", "VINCULACION"]


def test_otro_no_manda_si_hay_algo_mas_concreto():
    """«Otro, Instalación» es una incidencia de instalación, no una sin clasificar."""
    assert grupos_de_etiquetas("Otro, Instalación") == ["INSTALACION", "OTRO"]
    assert grupos_de_etiquetas("Otro, Aplicación, Vinculación") == ["APP", "VINCULACION", "OTRO"]


def test_otro_a_solas_si_es_el_grupo():
    assert grupos_de_etiquetas("Otro") == ["OTRO"]


def test_una_celda_vacia_es_otro_y_no_se_descarta():
    """17 de las 119 no se etiquetaron; omitirlas falsearía los totales."""
    assert grupos_de_etiquetas("") == ["OTRO"]
    assert grupos_de_etiquetas("   ") == ["OTRO"]


def test_una_etiqueta_desconocida_no_inventa_grupo():
    assert grupos_de_etiquetas("Teletransporte") == ["OTRO"]


def test_sensor_de_apertura_no_es_un_grupo_propio():
    """1 incidencia de 119: encaja como pregunta condicionada al dispositivo (G4)."""
    assert grupos_de_etiquetas("Sensor de Apertura") == ["OTRO"]
    assert grupos_de_etiquetas("Sensor de Apertura, Pulsador") == ["PULSADOR", "OTRO"]


def test_una_etiqueta_repetida_no_duplica_el_grupo():
    assert grupos_de_etiquetas("Wifi, Conexión, Wifi") == ["CONECTIVIDAD"]
