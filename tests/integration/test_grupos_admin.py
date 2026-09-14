"""Administración de grupos de incidencia (G2.4) contra PostgreSQL real.

Hasta ahora, añadir o renombrar un grupo exigía escribir una migración: la
taxonomía era «configurable» solo para quien tocara el repositorio. Estos tests
cubren lo que pide el documento —crear, editar, ordenar, activar/desactivar,
fusionar y marcar en revisión— y sobre todo que **fusionar no pierda tickets**,
que es la operación con la que se puede hacer daño de verdad.

Se omiten automáticamente si PostgreSQL no está accesible.
"""

import pytest

from app import database


def _datos_ticket(**overrides) -> dict:
    base = {
        "instalador": "Marta Gil",
        "obra": "Torre Oeste",
        "dispositivo": "Connect-1",
        "sintoma": "No responde al mando",
        "estado": "en_espera",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------
# Crear
# ---------------------------------------------------------------------

def test_crear_grupo_normaliza_el_codigo(db):
    """El código es la referencia estable: sin normalizar, 'wifi' y 'WIFI' serían dos."""
    grupo = database.crear_grupo_incidencia(db, {"code": " sensor apertura ", "name": "Sensor de apertura"})

    assert grupo.code == "SENSOR_APERTURA"
    assert grupo.name == "Sensor de apertura"


def test_grupo_creado_nace_como_nuevo(db):
    """Distingue la taxonomía validada de la que se inventa durante una llamada."""
    grupo = database.crear_grupo_incidencia(db, {"code": "RECIEN_CREADO", "name": "Recien creado"})

    assert grupo.estado_revision == "nuevo"


def test_los_grupos_sembrados_son_estables(db):
    """Los 9 salen del análisis de 119 incidencias reales, no de una llamada."""
    sembrado = database.obtener_grupo_por_codigo(db, "VINCULACION")

    assert sembrado is not None
    assert sembrado.estado_revision == "estable"


def test_no_se_puede_repetir_el_codigo(db):
    database.crear_grupo_incidencia(db, {"code": "DUPLI", "name": "Primero"})

    with pytest.raises(ValueError, match="Ya existe"):
        database.crear_grupo_incidencia(db, {"code": "dupli", "name": "Segundo"})


def test_crear_sin_nombre_o_sin_codigo_falla(db):
    with pytest.raises(ValueError, match="código"):
        database.crear_grupo_incidencia(db, {"code": "  ", "name": "Sin código"})
    with pytest.raises(ValueError, match="nombre"):
        database.crear_grupo_incidencia(db, {"code": "SINNOMBRE", "name": "  "})


def test_estado_de_revision_invalido_se_rechaza(db):
    with pytest.raises(ValueError, match="Estado de revisión"):
        database.crear_grupo_incidencia(db, {"code": "RARO", "name": "Raro", "estado_revision": "inventado"})


def test_el_grupo_nuevo_se_coloca_al_final(db):
    """No reordena lo que ya estaba colocado."""
    maximo_previo = max(g.sort_order for g in database.obtener_grupos_incidencia(db, solo_activos=False))

    grupo = database.crear_grupo_incidencia(db, {"code": "ULTIMO", "name": "Último"})

    assert grupo.sort_order > maximo_previo


# ---------------------------------------------------------------------
# Editar, ordenar, desactivar
# ---------------------------------------------------------------------

def test_editar_cambia_nombre_y_estado_pero_no_el_codigo(db):
    database.crear_grupo_incidencia(db, {"code": "EDITAR", "name": "Nombre viejo"})

    actualizado = database.actualizar_grupo_incidencia(
        db, "editar", {"name": "Nombre nuevo", "estado_revision": "en_revision"}
    )

    assert actualizado.code == "EDITAR"
    assert actualizado.name == "Nombre nuevo"
    assert actualizado.estado_revision == "en_revision"


def test_editar_un_grupo_inexistente_devuelve_none(db):
    assert database.actualizar_grupo_incidencia(db, "NO_EXISTE", {"name": "x"}) is None


def test_desactivar_lo_saca_del_selector_pero_conserva_los_tickets(db):
    """Es la alternativa a borrar cuando hay histórico que no se quiere perder."""
    database.crear_grupo_incidencia(db, {"code": "OBSOLETO", "name": "Obsoleto"})
    ticket = database.crear_ticket_sat(db, _datos_ticket(grupo="OBSOLETO"))

    database.actualizar_grupo_incidencia(db, "OBSOLETO", {"is_active": False})

    activos = [g.code for g in database.obtener_grupos_incidencia(db, solo_activos=True)]
    todos = [g.code for g in database.obtener_grupos_incidencia(db, solo_activos=False)]
    assert "OBSOLETO" not in activos
    assert "OBSOLETO" in todos
    assert database.obtener_ticket_por_id(db, ticket.id).grupo.code == "OBSOLETO"


def test_reordenar_deja_huecos_para_intercalar_despues(db):
    """Numerar de 10 en 10 permite meter un grupo entre dos sin reescribir la tabla."""
    codigos = [g.code for g in database.obtener_grupos_incidencia(db, solo_activos=False)]
    invertido = list(reversed(codigos))

    database.reordenar_grupos_incidencia(db, invertido)

    resultado = database.obtener_grupos_incidencia(db, solo_activos=False)
    assert [g.code for g in resultado] == invertido
    assert [g.sort_order for g in resultado] == [(i + 1) * 10 for i in range(len(invertido))]


# ---------------------------------------------------------------------
# Fusionar — la operación con la que se puede perder información
# ---------------------------------------------------------------------

def test_fusionar_mueve_los_tickets_y_borra_el_origen(db):
    database.crear_grupo_incidencia(db, {"code": "WIFI_A", "name": "Wifi A"})
    database.crear_grupo_incidencia(db, {"code": "WIFI_B", "name": "Wifi B"})
    t1 = database.crear_ticket_sat(db, _datos_ticket(grupo="WIFI_A"))
    t2 = database.crear_ticket_sat(db, _datos_ticket(grupo="WIFI_A"))

    resultado = database.fusionar_grupos_incidencia(db, "WIFI_A", "WIFI_B")

    assert resultado["tickets_movidos"] == 2
    assert database.obtener_grupo_por_codigo(db, "WIFI_A") is None
    for t in (t1, t2):
        assert database.obtener_ticket_por_id(db, t.id).grupo.code == "WIFI_B"


def test_fusionar_no_duplica_cuando_el_ticket_ya_tenia_el_destino(db):
    """La tabla puente tiene clave primaria compuesta: insertar a ciegas reventaría."""
    database.crear_grupo_incidencia(db, {"code": "ORIG", "name": "Origen"})
    database.crear_grupo_incidencia(db, {"code": "DEST", "name": "Destino"})
    ticket = database.crear_ticket_sat(db, _datos_ticket())
    origen = database.obtener_grupo_por_codigo(db, "ORIG")
    destino = database.obtener_grupo_por_codigo(db, "DEST")
    db.add(database.TicketGrupoSecundario(ticket_id=ticket.id, grupo_id=origen.id))
    db.add(database.TicketGrupoSecundario(ticket_id=ticket.id, grupo_id=destino.id))
    db.commit()

    resultado = database.fusionar_grupos_incidencia(db, "ORIG", "DEST")

    assert resultado["secundarios_movidos"] == 0
    filas = db.query(database.TicketGrupoSecundario).filter(
        database.TicketGrupoSecundario.ticket_id == ticket.id
    ).all()
    assert len(filas) == 1
    assert filas[0].grupo_id == destino.id


def test_fusionar_arrastra_los_grupos_secundarios(db):
    database.crear_grupo_incidencia(db, {"code": "SEC_ORIG", "name": "Origen"})
    database.crear_grupo_incidencia(db, {"code": "SEC_DEST", "name": "Destino"})
    ticket = database.crear_ticket_sat(db, _datos_ticket())
    origen = database.obtener_grupo_por_codigo(db, "SEC_ORIG")
    db.add(database.TicketGrupoSecundario(ticket_id=ticket.id, grupo_id=origen.id))
    db.commit()

    resultado = database.fusionar_grupos_incidencia(db, "SEC_ORIG", "SEC_DEST")

    assert resultado["secundarios_movidos"] == 1
    destino = database.obtener_grupo_por_codigo(db, "SEC_DEST")
    fila = db.query(database.TicketGrupoSecundario).filter(
        database.TicketGrupoSecundario.ticket_id == ticket.id
    ).one()
    assert fila.grupo_id == destino.id


def test_no_se_puede_fusionar_un_grupo_consigo_mismo(db):
    with pytest.raises(ValueError, match="consigo mismo"):
        database.fusionar_grupos_incidencia(db, "VINCULACION", "vinculacion")


def test_fusionar_con_un_grupo_inexistente_falla(db):
    with pytest.raises(ValueError, match="inexistente"):
        database.fusionar_grupos_incidencia(db, "VINCULACION", "NO_EXISTE")


# ---------------------------------------------------------------------
# Borrar
# ---------------------------------------------------------------------

def test_borrar_un_grupo_sin_usar(db):
    database.crear_grupo_incidencia(db, {"code": "BORRABLE", "name": "Borrable"})

    assert database.eliminar_grupo_incidencia(db, "BORRABLE") == {"ok": True}
    assert database.obtener_grupo_por_codigo(db, "BORRABLE") is None


def test_no_se_borra_un_grupo_con_tickets(db):
    """La clave foránea es SET NULL: borrar dejaría tickets sin clasificar en silencio."""
    database.crear_grupo_incidencia(db, {"code": "EN_USO", "name": "En uso"})
    ticket = database.crear_ticket_sat(db, _datos_ticket(grupo="EN_USO"))

    resultado = database.eliminar_grupo_incidencia(db, "EN_USO")

    assert resultado["ok"] is False
    assert resultado["motivo"] == "en_uso"
    assert resultado["tickets"] == 1
    assert database.obtener_ticket_por_id(db, ticket.id).grupo.code == "EN_USO"


def test_borrar_un_grupo_inexistente_lo_dice(db):
    assert database.eliminar_grupo_incidencia(db, "FANTASMA") == {"ok": False, "motivo": "no_existe"}
