"""Tests de los grupos de incidencia (G2) contra PostgreSQL real.

Los 9 grupos los siembra la migración `3f514b913e75`, así que estos tests
comprueban también que la migración se aplicó y dejó la taxonomía en su sitio.

Se omiten automáticamente si PostgreSQL no está accesible.
"""

import pytest

from app import database

CODIGOS_ESPERADOS = [
    "VINCULACION",
    "CONECTIVIDAD",
    "GESTUAL",
    "APP",
    "PULSADOR",
    "INTEGRACIONES",
    "INSTALACION",
    "HARDWARE",
    "OTRO",
]


def _datos_ticket(**overrides) -> dict:
    base = {
        "instalador": "Carlos Ruiz",
        "obra": "Residencial Gran Via",
        "dispositivo": "Connect-1",
        "sintoma": "No vincula",
    }
    base.update(overrides)
    return base


def test_la_migracion_siembra_los_nueve_grupos(db):
    grupos = database.obtener_grupos_incidencia(db)

    assert [g.code for g in grupos] == CODIGOS_ESPERADOS


def test_los_grupos_salen_en_orden_de_presentacion(db):
    grupos = database.obtener_grupos_incidencia(db)

    ordenes = [g.sort_order for g in grupos]
    assert ordenes == sorted(ordenes)
    assert grupos[-1].code == "OTRO", "OTRO debe quedar el ultimo de la lista"


def test_un_grupo_desactivado_desaparece_de_la_lista(db):
    grupo = database.obtener_grupo_por_codigo(db, "HARDWARE")
    grupo.is_active = False
    db.commit()

    activos = [g.code for g in database.obtener_grupos_incidencia(db)]
    todos = [g.code for g in database.obtener_grupos_incidencia(db, solo_activos=False)]

    assert "HARDWARE" not in activos
    assert "HARDWARE" in todos


def test_busqueda_de_grupo_por_codigo_es_insensible_a_mayusculas(db):
    assert database.obtener_grupo_por_codigo(db, "conectividad").code == "CONECTIVIDAD"
    assert database.obtener_grupo_por_codigo(db, "  App  ").code == "APP"
    assert database.obtener_grupo_por_codigo(db, "") is None
    assert database.obtener_grupo_por_codigo(db, "NO_EXISTE") is None


def test_el_ticket_guarda_el_grupo_indicado(db):
    ticket = database.crear_ticket_sat(db, _datos_ticket(grupo="CONECTIVIDAD"))

    assert ticket.grupo is not None
    assert ticket.grupo.code == "CONECTIVIDAD"


def test_un_grupo_desconocido_no_rompe_el_alta(db):
    """Un código erróneo deja el ticket sin grupo, no lo rechaza.

    El alta llega desde tres puntos distintos de la interfaz; perder un parte SAT
    por un código mal escrito seria peor que registrarlo sin clasificar.
    """
    ticket = database.crear_ticket_sat(db, _datos_ticket(grupo="NO_EXISTE"))

    assert ticket.grupo_id is None


def test_ticket_sin_grupo_queda_sin_clasificar(db):
    ticket = database.crear_ticket_sat(db, _datos_ticket())

    assert ticket.grupo_id is None


def test_filtro_por_grupo_en_el_listado(db):
    database.crear_ticket_sat(db, _datos_ticket(grupo="CONECTIVIDAD"))
    database.crear_ticket_sat(db, _datos_ticket(grupo="CONECTIVIDAD"))
    database.crear_ticket_sat(db, _datos_ticket(grupo="APP"))

    _tickets, total = database.obtener_tickets_sat(db, grupo="CONECTIVIDAD")

    assert total == 2


def test_filtro_sin_grupo_devuelve_los_no_clasificados(db):
    database.crear_ticket_sat(db, _datos_ticket(grupo="APP"))
    database.crear_ticket_sat(db, _datos_ticket())
    database.crear_ticket_sat(db, _datos_ticket())

    _tickets, total = database.obtener_tickets_sat(db, grupo="sin_grupo")

    assert total == 2


def test_filtro_de_grupo_se_combina_con_estado_y_paginacion(db):
    for _ in range(3):
        database.crear_ticket_sat(db, _datos_ticket(grupo="APP", estado="resuelto"))
    database.crear_ticket_sat(db, _datos_ticket(grupo="APP", estado="en_espera"))
    database.crear_ticket_sat(db, _datos_ticket(grupo="GESTUAL", estado="resuelto"))

    pagina, total = database.obtener_tickets_sat(db, grupo="APP", estado="resuelto", limit=2, offset=0)

    assert total == 3
    assert len(pagina) == 2


def test_stats_cuenta_tickets_por_grupo_incluidos_los_vacios(db):
    database.crear_ticket_sat(db, _datos_ticket(grupo="CONECTIVIDAD"))
    database.crear_ticket_sat(db, _datos_ticket(grupo="CONECTIVIDAD"))
    database.crear_ticket_sat(db, _datos_ticket())

    por_grupo = {g["code"]: g["tickets"] for g in database.obtener_stats_tickets_sat(db)["por_grupo"]}

    assert por_grupo["CONECTIVIDAD"] == 2
    assert por_grupo[""] == 1, "Los tickets sin grupo deben contarse aparte"
    assert por_grupo["HARDWARE"] == 0, "Un grupo sin tickets tambien es informacion"
    assert set(CODIGOS_ESPERADOS).issubset(por_grupo)


@pytest.mark.parametrize("valor_neutro", [None, "todos"])
def test_sin_filtro_de_grupo_se_devuelven_todos(db, valor_neutro):
    database.crear_ticket_sat(db, _datos_ticket(grupo="APP"))
    database.crear_ticket_sat(db, _datos_ticket())

    _tickets, total = database.obtener_tickets_sat(db, grupo=valor_neutro)

    assert total == 2
