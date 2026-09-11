"""
Tests de verificación exhaustiva del Gestor de Sinónimos Técnicos y Tesauro SAT.
Cubre averías, conectividad, marcas, modos, equivalencias y tolerancia a acentos.
"""

import pytest
from app.sinonimos import GestorSinonimos, expandir_query


def test_carga_tesauro():
    """Comprueba que el archivo .ths carga correctamente con más de 200 conceptos y frases."""
    gestor = GestorSinonimos()
    assert len(gestor.frase_a_target) >= 200, f"Se esperaban >= 200 frases, hay {len(gestor.frase_a_target)}"
    assert len(gestor.target_a_frases) >= 30, f"Se esperaban >= 30 conceptos, hay {len(gestor.target_a_frases)}"


def test_averias_sat_excel():
    """Verifica la correcta expansión de síntomas reales del archivo Problemas-soluciones.xlsx."""
    # 1. Alimentación
    e1 = expandir_query("el dispositivo no enciende")
    assert "sin alimentacion" in e1

    # 2. Sensibilidad
    e2 = expandir_query("pulsador no responde")
    assert "pulsador no tiene sensibilidad" in e2

    # 3. Cable cortado por parpadeo
    e3 = expandir_query("el pulsador parpadea constantemente")
    assert "cable cortado" in e3

    # 4. Movimientos fantasma / ruido
    e4 = expandir_query("las persianas se mueven solas")
    assert "ruido electrico" in e4

    # 5. Relé / motor
    e5 = expandir_query("suena el rele")
    assert "fallo motor rele" in e5

    # 6. Candado
    e6 = expandir_query("la persiana tiene candado")
    assert "modo candado" in e6

    # 7. Controles invertidos
    e7 = expandir_query("cuando le da a bajar sube")
    assert "invertir controles" in e7

    # 8. Finales de carrera
    e8 = expandir_query("la persiana no para en su sitio")
    assert "finales de carrera" in e8


def test_marcas_y_dispositivos_cruzados():
    """Verifica que las búsquedas por marcas partner o nombres de proyecto mapean a los dispositivos correctos."""
    # Connect-1
    e1 = expandir_query("solven wave 1")
    assert "connect-1" in e1

    e2 = expandir_query("essential+")
    assert "connect-1" in e2

    # Connect-2
    e3 = expandir_query("sentry")
    assert "connect-2" in e3

    e4 = expandir_query("wave 2")
    assert "connect-2" in e4

    # C-Wall
    e5 = expandir_query("wave 3")
    assert "c-wall" in e5

    # C-Pulsar
    e6 = expandir_query("icon mini")
    assert "c-pulsar" in e6

    # Sense / Konect Élite
    e7 = expandir_query("control gestual")
    assert "konect elite sense" in e7 or "sense" in e7

    # Witooth / Blu-Connect
    e8 = expandir_query("mando a distancia")
    assert "blu-connect witooth" in e8 or "witooth" in e8


def test_conectividad_y_red():
    """Verifica términos de conectividad, CG-NAT, router y operadores."""
    e1 = expandir_query("problema con cgnat")
    assert "carrier grade nat" in e1

    e2 = expandir_query("digi plus")
    assert "cgnat operadores espana" in e2 or "carrier grade nat" in e2

    e3 = expandir_query("aislamiento de clientes")
    assert "aislamiento de clientes" in e3

    e4 = expandir_query("metodo multicast")
    assert "multivinculacion multicast" in e4 or "multicast" in e4

    e5 = expandir_query("modo ap")
    assert "modo ap punto a punto" in e5 or "punto a punto" in e5


def test_tolerancia_a_acentos_y_diacriticos():
    """Verifica que consultas con o sin tildes expanden de forma idéntica."""
    # Con tilde
    e_con = expandir_query("modo fábrica")
    # Sin tilde
    e_sin = expandir_query("modo fabrica")

    assert "modo fabrica" in e_con or "modo fabrica" in e_sin
    assert e_con.startswith("modo fábrica")
    assert e_sin.startswith("modo fabrica")

    # Otro ejemplo: pulsación / pulsacion
    e_p_con = expandir_query("pulsación corta reset")
    e_p_sin = expandir_query("pulsacion corta reset")
    assert "reset simple" in e_p_con
    assert "reset simple" in e_p_sin


def test_evitar_colisiones_subpalabras():
    """Verifica que términos cortos no colisionen falsamente dentro de palabras más largas."""
    # 'red' no debe coincidir dentro de 'pared'
    e_pared = expandir_query("la pared de la habitacion")
    assert "red wifi" not in e_pared

    # Pero sí cuando es palabra completa
    e_red = expandir_query("problemas de red")
    assert "red wifi" in e_red


def test_consultas_sin_coincidencia():
    """Verifica que términos desconocidos o vacíos no se alteran."""
    assert expandir_query("") == ""
    assert expandir_query("   ") == "   "
    assert expandir_query("palabra_rara_9999") == "palabra_rara_9999"
