"""Predicción del grupo y de los tickets parecidos, contra PostgreSQL real.

Sustituye a `buscar_tickets_resueltos_similares`, que medido con «deja uno
fuera» acertaba el grupo el 38 % de las veces frente al 62 % de esto, comparaba
el síntoma sin tildes contra un índice con raíces acentuadas e ignoraba el
dispositivo que recibía.

Lo que se fija aquí es que acierte con lo obvio, que aguante las erratas con las
que se escriben de verdad los tickets, y sobre todo que se entere SOLO de los
tickets nuevos: cuantos más se clasifican, mejor acierta, sin tocar nada.
"""

import pytest

from app import database, prediccion
from app.prediccion import indice


def _ticket(db, sintoma, grupo=None, dispositivo="Connect-1", estado="resuelto", solucion=""):
    datos = {"instalador": "Marta Gil", "sintoma": sintoma, "dispositivo": dispositivo,
             "estado": estado, "solucion": solucion}
    if grupo:
        datos["grupo"] = grupo
    return database.crear_ticket_sat(db, datos)


@pytest.fixture
def historico(db):
    for s in ["No vincula el dispositivo con la aplicación del móvil",
              "No consigue vincular el equipo, la app no lo encuentra",
              "Al vincular desde la app se queda buscando y no aparece"]:
        _ticket(db, s, "VINCULACION", solucion="Separar las bandas del router y repetir el emparejamiento")
    for s in ["El pulsador de la pared no responde al tocarlo",
              "La botonera no hace caso, hay que pulsar muchas veces",
              "El pulsador capacitivo no tiene sensibilidad"]:
        _ticket(db, s, "PULSADOR", solucion="Recalibrar el pulsador")
    return db


def test_predice_el_grupo_de_un_caso_parecido(historico):
    p = indice.predecir(historico, "no consigo vincular con la aplicacion", "Connect-1")
    assert p["grupo"] == "VINCULACION"
    assert 0 < p["confianza"] <= 1
    assert p["base"] == 6


def test_aguanta_las_erratas_con_las_que_se_escriben_los_tickets(historico):
    """«princiapl», «qu ellos»: los tickets reales vienen así. Por eso n-gramas de caracteres."""
    assert indice.predecir(historico, "el pulsdor de la pared no respnde", "Connect-1")["grupo"] == "PULSADOR"


def test_devuelve_los_tickets_parecidos_con_su_solucion(historico):
    p = indice.predecir(historico, "la app no encuentra el equipo al vincular", "Connect-1")
    assert p["vecinos"], "debería enseñar casos parecidos"
    assert p["vecinos"][0]["grupo"] == "VINCULACION"
    assert "router" in p["vecinos"][0]["solucion"]


def test_con_poco_texto_no_se_inventa_nada(historico):
    p = indice.predecir(historico, "falla", "Connect-1")
    assert p["grupo"] is None and p["vecinos"] == []


def test_sin_tickets_clasificados_no_revienta(db):
    assert indice.predecir(db, "no vincula el dispositivo con la app", "Connect-1")["grupo"] is None


def test_un_ticket_no_se_predice_a_si_mismo(historico):
    """Para evaluar sin trampas: excluido él y sus copias exactas."""
    t = _ticket(historico, "Sensor de temperatura que marca cinco grados de más", "HARDWARE")
    indice.invalidar()
    sin_excluir = indice.predecir(historico, t.sintoma, "Connect-1")
    excluido = indice.predecir(historico, t.sintoma, "Connect-1", excluir_ids=[t.id], excluir_texto=t.sintoma)
    assert sin_excluir["vecinos"][0]["ticket_id"] == t.id
    assert all(v["ticket_id"] != t.id for v in excluido["vecinos"])


def test_se_entera_sola_de_los_tickets_nuevos(historico, monkeypatch):
    """El corazón de «meter información sin tocar nada»: clasificar un ticket
    cambia la firma de los datos y el índice se reconstruye solo."""
    monkeypatch.setattr(prediccion, "VIGENCIA_S", 0.0)
    texto = "el sensor de apertura de la ventana oscilobatiente no detecta nada"
    assert indice.predecir(historico, texto, "Connect-2")["grupo"] != "HARDWARE"

    for s in ["El sensor de apertura de la hoja no detecta el cierre",
              "Sensor de apertura roto en la ventana oscilobatiente",
              "El sensor de la ventana no detecta si está abierta"]:
        _ticket(historico, s, "HARDWARE", dispositivo="Connect-2")

    assert indice.predecir(historico, texto, "Connect-2")["grupo"] == "HARDWARE"


def test_los_tickets_sin_clasificar_no_votan_pero_se_ensenan(historico):
    """Un ticket sin grupo no puede decir de qué grupo es otro, pero su
    solución puede servir igual."""
    _ticket(historico, "No vincula el dispositivo con la aplicación, sigue sin salir", grupo=None,
            estado="en_espera")
    indice.invalidar()
    p = indice.predecir(historico, "no vincula el dispositivo con la aplicacion", "Connect-1")
    assert p["base"] == 6  # los clasificados, no los siete
    assert any(v["grupo"] is None for v in p["vecinos"])


def test_la_evaluacion_mide_con_lo_que_haya(historico):
    r = indice.evaluar(historico)
    assert r["casos"] == 6
    assert 0 <= r["acierto_1"] <= r["acierto_3"] <= 1
    assert set(r["por_grupo"]) == {"VINCULACION", "PULSADOR"}


def test_con_menos_de_cinco_casos_no_se_da_una_cifra(db):
    """Un porcentaje sobre tres tickets no significa nada; mejor decirlo."""
    for s in ["No vincula el dispositivo", "No vincula con la app", "El pulsador no responde"]:
        _ticket(db, s + " desde hace dos semanas", "VINCULACION")
    assert indice.evaluar(db)["acierto_1"] is None
