"""Quién puede pedir la ficha de una obra.

El contenido de la ficha se prueba en `tests/integration/test_ficha_obra.py`,
contra PostgreSQL. Aquí solo la frontera de acceso, que es lo único que se ve
desde fuera.

**Por qué no hay tests del camino con datos.** El fixture `mock_users`
sustituye `SessionLocal` entera por un doble que solo sabe resolver usuarios
por correo, así que cualquier endpoint que consulte datos de verdad revienta
con él. Extenderlo para esta ficha sería tocar andamiaje que comparten todos
los tests de API para cubrir algo que ya está cubierto contra la base de datos
real. Queda anotado como lo que es: una limitación del andamiaje, no una
decisión sobre esta funcionalidad.
"""

import pytest


def test_la_ficha_pide_estar_identificado(client):
    assert client.get("/api/sat/obras/13282/ficha").status_code == 401


def test_la_ficha_de_un_ticket_pide_estar_identificado(client):
    assert client.get("/api/sat/tickets/1/ficha-obra").status_code == 401


def test_el_comercial_no_ve_el_historial_de_obras(client, mock_users):
    """La ficha lleva nombres de instaladores y síntomas de clientes: es el
    mismo material que los tickets, y los tickets ya son de técnico."""
    respuesta = client.get("/api/sat/obras/13282/ficha",
                           headers=mock_users["headers"]["comercial"])

    assert respuesta.status_code == 403


def test_el_comercial_tampoco_por_la_via_del_ticket(client, mock_users):
    """Dos endpoints distintos llegan al mismo dato. Proteger solo uno es la
    forma habitual de dejar una puerta abierta."""
    respuesta = client.get("/api/sat/tickets/1/ficha-obra",
                           headers=mock_users["headers"]["comercial"])

    assert respuesta.status_code == 403


@pytest.mark.parametrize("rol", ["tecnico", "admin"])
def test_un_ticket_que_no_existe_es_404(client, mock_users, rol):
    """Preguntar por la obra de un ticket inexistente es un error de quien
    llama. Una obra sin antecedentes, en cambio, contesta 200 con la ficha
    vacía: «no hay historial» es la respuesta más frecuente y no puede llegar
    como error, o la interfaz aprendería a ignorar el aviso."""
    respuesta = client.get("/api/sat/tickets/99999999/ficha-obra",
                           headers=mock_users["headers"][rol])

    assert respuesta.status_code == 404
