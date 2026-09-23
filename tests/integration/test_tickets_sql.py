"""Tests del SQL real de tickets SAT contra una base de datos PostgreSQL.

Los tests de tests/api/ mockean database.SessionLocal y reimplementan el filtrado
en Python, de modo que validan el mock escrito en el propio test y no la consulta.
Estos, en cambio, ejercitan las funciones de app/database.py contra una base de
datos creada con las migraciones de Alembic.

Se omiten automáticamente si PostgreSQL no está accesible.
"""

import pytest

from app import database


def _datos_ticket(**overrides) -> dict:
    base = {
        "instalador": "Carlos Ruiz",
        "email": "carlos@ejemplo.es",
        "telefono": "600100200",
        "obra": "Residencial Gran Via",
        "distribuidor": "IoT Fenster",
        "dispositivo": "Connect-1",
        "sintoma": "La persiana sube al pulsar bajar",
        "diagnostico": "Inversion de fases",
        "estado": "en_espera",
    }
    base.update(overrides)
    return base


def test_numero_de_ticket_es_correlativo(db):
    """El contador debe avanzar sin huecos y con el formato SAT-AAAA-NNNN."""
    primero = database.crear_ticket_sat(db, _datos_ticket())
    segundo = database.crear_ticket_sat(db, _datos_ticket())

    assert primero.numero_ticket.startswith("SAT-")
    assert primero.numero_ticket != segundo.numero_ticket

    secuencia = lambda n: int(n.rsplit("-", 1)[1])  # noqa: E731
    assert secuencia(segundo.numero_ticket) == secuencia(primero.numero_ticket) + 1


def test_filtro_por_estado_no_devuelve_otros_estados(db):
    database.crear_ticket_sat(db, _datos_ticket(estado="resuelto"))
    database.crear_ticket_sat(db, _datos_ticket(estado="en_espera"))
    database.crear_ticket_sat(db, _datos_ticket(estado="en_espera"))

    tickets, total = database.obtener_tickets_sat(db, estado="en_espera")

    assert total == 2
    assert {t.estado for t in tickets} == {"en_espera"}


def test_estado_todos_no_filtra(db):
    database.crear_ticket_sat(db, _datos_ticket(estado="resuelto"))
    database.crear_ticket_sat(db, _datos_ticket(estado="en_espera"))

    _tickets, total = database.obtener_tickets_sat(db, estado="todos")

    assert total == 2


@pytest.mark.parametrize(
    "termino",
    ["Gran Via", "gran via", "Connect-1", "carlos@ejemplo.es", "600100200", "Inversion"],
)
def test_busqueda_libre_cubre_todas_las_columnas_y_es_insensible_a_mayusculas(db, termino):
    database.crear_ticket_sat(db, _datos_ticket())
    database.crear_ticket_sat(
        db,
        _datos_ticket(
            instalador="Otro",
            email="otro@ejemplo.es",
            telefono="911000000",
            obra="Nave industrial",
            dispositivo="C-Wall",
            sintoma="No enciende",
            diagnostico="Sin tension",
        ),
    )

    tickets, total = database.obtener_tickets_sat(db, q=termino)

    assert total == 1, f"El termino {termino!r} deberia encontrar exactamente un ticket"
    assert tickets[0].obra == "Residencial Gran Via"


def test_busqueda_sin_coincidencias_devuelve_vacio(db):
    database.crear_ticket_sat(db, _datos_ticket())

    tickets, total = database.obtener_tickets_sat(db, q="texto que no existe en ningun campo")

    assert (tickets, total) == ([], 0)


def test_paginacion_en_sql_devuelve_el_total_completo(db):
    """El total debe ser el de la consulta filtrada, no el de la página devuelta."""
    for i in range(5):
        database.crear_ticket_sat(db, _datos_ticket(obra=f"Obra {i}"))

    pagina, total = database.obtener_tickets_sat(db, limit=2, offset=0)

    assert total == 5
    assert len(pagina) == 2


def test_paginacion_no_solapa_ni_pierde_tickets(db):
    for i in range(5):
        database.crear_ticket_sat(db, _datos_ticket(obra=f"Obra {i}"))

    primera, _ = database.obtener_tickets_sat(db, limit=2, offset=0)
    segunda, _ = database.obtener_tickets_sat(db, limit=2, offset=2)
    tercera, _ = database.obtener_tickets_sat(db, limit=2, offset=4)

    ids = [t.id for t in primera + segunda + tercera]

    assert len(ids) == 5
    assert len(set(ids)) == 5, "Alguna página repite tickets"
    assert ids == sorted(ids, reverse=True), "El orden debe ser descendente por id"


def test_paginacion_y_filtro_se_combinan(db):
    for i in range(4):
        database.crear_ticket_sat(db, _datos_ticket(estado="resuelto", obra=f"Obra {i}"))
    database.crear_ticket_sat(db, _datos_ticket(estado="en_espera"))

    pagina, total = database.obtener_tickets_sat(db, estado="resuelto", limit=3, offset=0)

    assert total == 4
    assert len(pagina) == 3
    assert {t.estado for t in pagina} == {"resuelto"}


def test_stats_cuenta_por_estado(db):
    database.crear_ticket_sat(db, _datos_ticket(estado="resuelto"))
    database.crear_ticket_sat(db, _datos_ticket(estado="resuelto"))
    database.crear_ticket_sat(db, _datos_ticket(estado="en_espera"))
    database.crear_ticket_sat(db, _datos_ticket(estado="rma_pendiente"))

    stats = database.obtener_stats_tickets_sat(db)

    assert stats["total"] == 4
    assert stats["resuelto"] == 2
    assert stats["en_espera"] == 1
    assert stats["rma_pendiente"] == 1
    assert stats["descartado"] == 0


def test_actualizar_y_eliminar_ticket(db):
    ticket = database.crear_ticket_sat(db, _datos_ticket())

    actualizado = database.actualizar_ticket_sat(db, ticket.id, {"estado": "resuelto"})
    assert actualizado.estado == "resuelto"

    assert database.eliminar_ticket_sat(db, ticket.id) is True
    assert database.obtener_ticket_por_id(db, ticket.id) is None
