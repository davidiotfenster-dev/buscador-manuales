"""Persistencia del cuestionario de asistencia (G3.1), contra PostgreSQL real.

Hasta ahora el técnico rellenaba doce bloques, recibía un diagnóstico y **no
quedaba rastro de lo que había contestado**. Eso impide las dos cosas que vienen
después: diseñar la tabla de preguntas de G3.2 con datos en vez de a ojo, y
medir si el triaje acierta.

Lo que se fija aquí es que el envío se guarda entero, que se puede atar al
ticket que salga de él, y que las estadísticas dicen qué campos se rellenan de
verdad.

Se omiten automáticamente si PostgreSQL no está accesible.
"""

import json

from app import database


RESPUESTAS = {
    "partner": "IoT Fenster",
    "dispositivo": "Connect-1",
    "area_incidencia": "Conectividad",
    "estado_app": "No",
    "sintomas_observados": ["Aparece offline"],
    "wifi_info": {"banda": "5GHz"},
    "descripcion_detallada": "Dejó de verse en la app tras cambiar el router",
}

RESULTADO = {
    "exito": True,
    "confianza": 89.3,
    "diagnostico_titulo": "Incidencia de Conectividad Wi-Fi",
}


def _ticket(db):
    return database.crear_ticket_sat(db, {
        "instalador": "Marta Gil",
        "obra": "Torre Oeste",
        "dispositivo": "Connect-1",
        "sintoma": "No aparece en la app",
        "estado": "en_espera",
    })


def test_se_guarda_el_envio_entero_no_un_resumen(db):
    """Las preguntas van a cambiar; guardar el JSON completo es lo que aguanta."""
    registro = database.guardar_cuestionario_asistencia(db, RESPUESTAS, RESULTADO)

    guardado = json.loads(registro.respuestas_json)
    assert guardado == RESPUESTAS
    assert guardado["wifi_info"]["banda"] == "5GHz"


def test_los_campos_que_se_filtran_salen_del_json(db):
    """Para poder listar por dispositivo sin abrir el JSON de cada fila."""
    registro = database.guardar_cuestionario_asistencia(db, RESPUESTAS, RESULTADO)

    assert registro.dispositivo == "Connect-1"
    assert registro.area_incidencia == "Conectividad"
    assert registro.diagnostico_titulo == "Incidencia de Conectividad Wi-Fi"


def test_la_confianza_conserva_los_decimales(db):
    """El triaje devuelve 89.3: redondear a 89 sería inventar precisión."""
    registro = database.guardar_cuestionario_asistencia(db, RESPUESTAS, RESULTADO)

    assert registro.confianza == 89.3


def test_un_cuestionario_sin_sesion_tambien_se_guarda(db):
    """El endpoint de triaje es accesible sin token; perder ese envío sería peor."""
    registro = database.guardar_cuestionario_asistencia(db, RESPUESTAS, RESULTADO)

    assert registro.id is not None
    assert registro.creado_por == ""


def test_el_cuestionario_se_ata_al_ticket_que_salio_de_el(db):
    """El ticket nace después, y solo a veces: por eso la relación va en dos pasos."""
    registro = database.guardar_cuestionario_asistencia(db, RESPUESTAS, RESULTADO)
    ticket = _ticket(db)

    assert database.vincular_cuestionario_a_ticket(db, registro.id, ticket.id) is True
    assert database.obtener_cuestionarios_asistencia(db, ticket_id=ticket.id)[0].id == registro.id


def test_vincular_un_cuestionario_inexistente_no_revienta(db):
    ticket = _ticket(db)

    assert database.vincular_cuestionario_a_ticket(db, 999999, ticket.id) is False


def test_borrar_el_ticket_no_borra_lo_que_se_contesto(db):
    """La clave foránea es SET NULL: la evidencia del triaje sobrevive al ticket."""
    registro = database.guardar_cuestionario_asistencia(db, RESPUESTAS, RESULTADO)
    ticket = _ticket(db)
    database.vincular_cuestionario_a_ticket(db, registro.id, ticket.id)

    db.delete(db.get(database.TicketSAT, ticket.id))
    db.commit()
    db.expire_all()

    superviviente = db.get(database.CuestionarioAsistencia, registro.id)
    assert superviviente is not None
    assert superviviente.ticket_id is None
    assert json.loads(superviviente.respuestas_json) == RESPUESTAS


def test_las_estadisticas_dicen_que_campos_se_rellenan(db):
    """Es lo que G3.2 necesita: un campo que no toca nadie sobra del formulario."""
    database.guardar_cuestionario_asistencia(db, RESPUESTAS, RESULTADO)
    database.guardar_cuestionario_asistencia(
        db, {"dispositivo": "C-Wall", "area_incidencia": ""}, RESULTADO
    )

    stats = database.estadisticas_cuestionarios(db)
    por_campo = {c["campo"]: c for c in stats["campos"]}

    assert stats["total"] == 2
    assert por_campo["dispositivo"]["porcentaje"] == 100.0
    assert por_campo["wifi_info"]["veces"] == 1
    # 'area_incidencia' llega vacía en el segundo envío: no cuenta como rellenada.
    assert por_campo["area_incidencia"]["veces"] == 1


def test_las_estadisticas_sobre_una_tabla_vacia_no_dividen_entre_cero(db):
    assert database.estadisticas_cuestionarios(db) == {
        "total": 0, "con_ticket": 0, "confianza_media": None, "campos": [], "por_dispositivo": []
    }


def test_un_json_corrupto_no_tumba_las_estadisticas(db):
    """Un envío raro no puede dejar sin métricas a todos los demás."""
    database.guardar_cuestionario_asistencia(db, RESPUESTAS, RESULTADO)
    db.add(database.CuestionarioAsistencia(dispositivo="X", respuestas_json="{esto no es json"))
    db.commit()

    stats = database.estadisticas_cuestionarios(db)

    assert stats["total"] == 2
    assert {c["campo"] for c in stats["campos"]} >= {"dispositivo", "wifi_info"}
