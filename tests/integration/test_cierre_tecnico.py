"""Tests del cierre técnico estructurado (G10) contra PostgreSQL real.

El cierre existe para responder a una pregunta que hoy no tiene respuesta:
¿nuestra documentación resuelve? Por eso lo que más se prueba aquí no es que los
campos se guarden, sino que los **denominadores de las métricas** sean los
correctos — un ticket sin cerrar no puede contar como documentación insuficiente.

Se omiten automáticamente si PostgreSQL no está accesible.
"""

import pytest

from app import database


def _datos_ticket(**overrides) -> dict:
    base = {
        "instalador": "Ana Serrano",
        "email": "ana@ejemplo.es",
        "obra": "Edificio Norte",
        "distribuidor": "IoT Fenster",
        "dispositivo": "Connect-2",
        "sintoma": "El dispositivo aparece offline tras cambiar el router",
        "estado": "en_espera",
    }
    base.update(overrides)
    return base


def _cierre(**overrides) -> dict:
    base = {
        "cierre_resuelto": True,
        "cierre_doc_suficiente": True,
        "cierre_descripcion": "Reconfigurado el wifi en 2.4 GHz",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------
# Registro del cierre
# ---------------------------------------------------------------------

def test_registrar_cierre_guarda_campos_fecha_y_autor(db):
    ticket = database.crear_ticket_sat(db, _datos_ticket())

    cerrado = database.registrar_cierre_tecnico(db, ticket.id, _cierre(), autor="tecnico@iotfenster.com")

    assert cerrado.cierre_resuelto is True
    assert cerrado.cierre_doc_suficiente is True
    assert cerrado.cierre_descripcion == "Reconfigurado el wifi en 2.4 GHz"
    assert cerrado.cierre_por == "tecnico@iotfenster.com"
    assert cerrado.cierre_fecha is not None


def test_registrar_cierre_no_toca_el_estado(db):
    """El cierre describe lo ocurrido; el estado es el flujo de trabajo.

    Un ticket puede cerrarse diciendo que no se resolvió y seguir en espera
    hasta que llegue un recambio. Mezclar ambas cosas perdería ese matiz.
    """
    ticket = database.crear_ticket_sat(db, _datos_ticket(estado="rma_pendiente"))

    cerrado = database.registrar_cierre_tecnico(db, ticket.id, _cierre(cierre_resuelto=False))

    assert cerrado.estado == "rma_pendiente"
    assert cerrado.cierre_resuelto is False


def test_registrar_cierre_en_ticket_inexistente_devuelve_none(db):
    assert database.registrar_cierre_tecnico(db, 999999, _cierre()) is None


def test_cierre_admite_resuelto_false_sin_confundirlo_con_sin_cerrar(db):
    """False y None son cosas distintas: «no se resolvió» y «nadie lo ha cerrado»."""
    sin_cerrar = database.crear_ticket_sat(db, _datos_ticket())
    no_resuelto = database.crear_ticket_sat(db, _datos_ticket())
    database.registrar_cierre_tecnico(db, no_resuelto.id, _cierre(cierre_resuelto=False))

    assert sin_cerrar.cierre_resuelto is None
    assert database.obtener_ticket_por_id(db, no_resuelto.id).cierre_resuelto is False


# ---------------------------------------------------------------------
# Métricas — lo que alimenta G15
# ---------------------------------------------------------------------

def test_stats_de_cierre_sin_ningun_cierre_no_inventa_porcentajes(db):
    """Sin datos, los porcentajes deben ser None, no 0.

    Un 0 % de documentación suficiente diría que la documentación nunca sirve,
    cuando lo cierto es que todavía nadie ha contestado.
    """
    database.crear_ticket_sat(db, _datos_ticket())

    stats = database.obtener_stats_cierre_tecnico(db)

    assert stats["con_cierre"] == 0
    assert stats["sin_cierre"] == 1
    assert stats["resueltos_pct"] is None
    assert stats["documentacion_suficiente_pct"] is None
    assert stats["horas_hasta_cierre"] is None


def test_porcentaje_de_documentacion_se_calcula_sobre_los_cerrados(db):
    """El denominador son los tickets cerrados, nunca el total.

    Este es el fallo que haría inútil la métrica: con 2 de 4 cerrados y 1 con
    documentación suficiente, la respuesta es 50 %, no 25 %.
    """
    for _ in range(2):
        database.crear_ticket_sat(db, _datos_ticket())  # sin cerrar
    a = database.crear_ticket_sat(db, _datos_ticket())
    b = database.crear_ticket_sat(db, _datos_ticket())
    database.registrar_cierre_tecnico(db, a.id, _cierre(cierre_doc_suficiente=True))
    database.registrar_cierre_tecnico(db, b.id, _cierre(cierre_doc_suficiente=False))

    stats = database.obtener_stats_cierre_tecnico(db)

    assert stats["con_cierre"] == 2
    assert stats["sin_cierre"] == 2
    assert stats["documentacion_suficiente"] == 1
    assert stats["documentacion_suficiente_pct"] == 50.0


def test_escalados_se_cuentan_y_se_porcentuan(db):
    a = database.crear_ticket_sat(db, _datos_ticket())
    b = database.crear_ticket_sat(db, _datos_ticket())
    database.registrar_cierre_tecnico(db, a.id, _cierre(cierre_escalado=True))
    database.registrar_cierre_tecnico(db, b.id, _cierre(cierre_escalado=False))

    stats = database.obtener_stats_cierre_tecnico(db)

    assert stats["escalados"] == 1
    assert stats["escalados_pct"] == 50.0


def test_stats_de_tickets_incluyen_el_bloque_de_cierre(db):
    """Las stats generales deben exponer el cierre, que es lo que consume G15."""
    ticket = database.crear_ticket_sat(db, _datos_ticket())
    database.registrar_cierre_tecnico(db, ticket.id, _cierre())

    stats = database.obtener_stats_tickets_sat(db)

    assert "cierre" in stats
    assert stats["cierre"]["con_cierre"] == 1
    assert stats["cierre"]["resueltos_pct"] == 100.0


def test_horas_hasta_cierre_usa_la_fecha_del_cierre(db):
    """No puede usar fecha_actualizacion: cambia con cualquier edición posterior."""
    ticket = database.crear_ticket_sat(db, _datos_ticket())
    database.registrar_cierre_tecnico(db, ticket.id, _cierre())

    stats = database.obtener_stats_cierre_tecnico(db)

    assert stats["horas_hasta_cierre"] is not None
    assert stats["horas_hasta_cierre"] >= 0


# ---------------------------------------------------------------------
# Documentos que resuelven
# ---------------------------------------------------------------------

def test_documentos_usados_ordena_por_veces_y_mezcla_manuales_y_videos(db):
    """Al operador le da igual el formato: quiere saber qué material resuelve."""
    manual = database.Manual(nombre_original="Guia Connect-2.pdf", nombre_archivo="guia_c2.pdf")
    video = database.Video(video_id="abc123", titulo="Vincular Connect-2", url="https://x/abc123")
    db.add_all([manual, video])
    db.commit()

    for _ in range(3):
        t = database.crear_ticket_sat(db, _datos_ticket())
        database.registrar_cierre_tecnico(db, t.id, _cierre(cierre_manual_id=manual.id))
    t = database.crear_ticket_sat(db, _datos_ticket())
    database.registrar_cierre_tecnico(db, t.id, _cierre(cierre_video_id=video.id))

    documentos = database.contar_documentos_usados_en_cierres(db)

    assert [d["veces"] for d in documentos] == [3, 1]
    assert documentos[0]["tipo"] == "manual"
    assert documentos[0]["nombre"] == "Guia Connect-2.pdf"
    assert documentos[1]["tipo"] == "video"
    assert documentos[1]["nombre"] == "Vincular Connect-2"


def test_borrar_un_manual_no_borra_el_ticket_que_lo_citaba(db):
    """ondelete SET NULL: se pierde el enlace, pero el cierre sobrevive."""
    manual = database.Manual(nombre_original="Obsoleto.pdf", nombre_archivo="obsoleto.pdf")
    db.add(manual)
    db.commit()
    ticket = database.crear_ticket_sat(db, _datos_ticket())
    database.registrar_cierre_tecnico(
        db, ticket.id, _cierre(cierre_manual_id=manual.id, cierre_doc_texto="Guia obsoleta")
    )

    db.delete(manual)
    db.commit()

    superviviente = database.obtener_ticket_por_id(db, ticket.id)
    assert superviviente is not None
    assert superviviente.cierre_manual_id is None
    assert superviviente.cierre_doc_texto == "Guia obsoleta"
    assert superviviente.cierre_resuelto is True
