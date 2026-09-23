"""El correo como puerta de entrada al caso.

El cuestionario de asistencia no preguntaba nada de la persona: doce bloques de
electrónica y ni el nombre ni el correo. Sin eso, cada llamada empieza de cero
aunque sea la cuarta del mismo cliente, y el ticket que sale del triaje nace sin
a quién atribuirlo.

`historial_por_correo` es lo que permite la pregunta que faltaba: ¿esta persona
ya tiene algo abierto? Estos tests fijan sobre todo la parte que puede hacer
daño —que la búsqueda sea exacta y no por `LIKE`—, porque aquí un falso positivo
significa enseñar el historial de un cliente mientras se atiende a otro.
"""

import pytest

from app import database


@pytest.fixture
def tickets_de_ejemplo(db):
    """Dos clientes distintos, uno de ellos con correos parecidos."""
    for datos in [
        {
            "instalador": "Paco Gómez",
            "email": "paco@ventanas.example",
            "telefono": "612345678",
            "obra": "Residencial Las Rozas",
            "distribuidor": "Solven",
            "dispositivo": "Connect-1",
            "sintoma": "La persiana no sube",
            "estado": "en_espera",
        },
        {
            "instalador": "Paco Gómez",
            "email": "PACO@Ventanas.Example",  # el mismo, tecleado de otra forma
            "telefono": "612345678",
            "obra": "Residencial Las Rozas",
            "dispositivo": "Connect-1",
            "sintoma": "Sigue sin subir",
            "estado": "resuelto",
        },
        {
            "instalador": "Ana Ruiz",
            "email": "ana@otraempresa.example",
            "dispositivo": "C-Wall",
            "sintoma": "El pulsador no responde",
            "estado": "en_espera",
        },
    ]:
        database.crear_ticket_sat(db, datos, creado_por="tester@iotfenster.com")
    return db


def test_devuelve_los_casos_de_ese_correo(tickets_de_ejemplo):
    h = database.historial_por_correo(tickets_de_ejemplo, "paco@ventanas.example")
    assert h["total"] == 2
    assert h["abiertos"] == 1
    assert h["resueltos"] == 1


def test_el_correo_no_distingue_mayusculas(tickets_de_ejemplo):
    """Nadie teclea su correo igual dos veces; el historial no puede depender de eso."""
    h = database.historial_por_correo(tickets_de_ejemplo, "  PACO@VENTANAS.EXAMPLE  ")
    assert h["total"] == 2


def test_no_se_devuelve_el_historial_de_otra_persona(tickets_de_ejemplo):
    """La búsqueda es por igualdad, no por LIKE.

    Con un LIKE, teclear "paco@" a medias devolvería casos de cualquiera cuyo
    correo lo contuviera. Aquí eso es enseñar datos de un cliente a cuenta de
    otro, así que un correo a medias no devuelve nada.
    """
    h = database.historial_por_correo(tickets_de_ejemplo, "paco@")
    assert h["total"] == 0
    assert h["tickets"] == []


def test_un_correo_vacio_no_devuelve_toda_la_base(tickets_de_ejemplo):
    h = database.historial_por_correo(tickets_de_ejemplo, "")
    assert h["total"] == 0
    assert h["tickets"] == []


def test_devuelve_los_datos_de_contacto_para_no_volver_a_pedirlos(tickets_de_ejemplo):
    h = database.historial_por_correo(tickets_de_ejemplo, "paco@ventanas.example")
    assert h["instalador"] == "Paco Gómez"
    assert h["telefono"] == "612345678"
    assert h["obra"] == "Residencial Las Rozas"


def test_un_cliente_desconocido_no_revienta(tickets_de_ejemplo):
    h = database.historial_por_correo(tickets_de_ejemplo, "nadie@ejemplo.example")
    assert h["total"] == 0
    assert h["abiertos"] == 0
    assert h["instalador"] == ""


def test_el_historial_de_un_cliente_no_esta_abierto_a_cualquiera(client, mock_users, monkeypatch):
    """Devuelve datos de una persona identificada: exige sesión técnica.

    El triaje en sí se puede usar sin sesión, así que era fácil dejar esto
    colgando de la misma puerta y publicar el historial de cualquier cliente a
    quien acertara un correo.
    """
    # Lo que se comprueba aquí es la puerta, no la consulta: la sesión de este
    # cliente de pruebas no tiene una base real detrás.
    monkeypatch.setattr(
        database, "historial_por_correo",
        lambda db, email, limite=10: {"email": email, "total": 0, "abiertos": 0,
                                      "resueltos": 0, "instalador": "", "telefono": "",
                                      "obra": "", "distribuidor": "", "tickets": []},
    )

    sin_sesion = client.get("/api/sat/clientes/historial?email=paco@ventanas.example")
    assert sin_sesion.status_code in (401, 403)

    comercial = client.get(
        "/api/sat/clientes/historial?email=paco@ventanas.example",
        headers=mock_users["headers"]["comercial"],
    )
    assert comercial.status_code == 403

    tecnico = client.get(
        "/api/sat/clientes/historial?email=paco@ventanas.example",
        headers=mock_users["headers"]["tecnico"],
    )
    assert tecnico.status_code == 200
