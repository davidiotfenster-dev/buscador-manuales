"""Sugerencia de vídeos para un ticket, contra PostgreSQL real.

En las 119 incidencias reales, «Vídeos» aparece 29 veces como acción correctiva,
pero al cerrar un ticket el selector ofrecía los 43 vídeos del canal en una
lista plana: dar con el que servía dependía de acordarse del título.

Lo que se fija aquí es el orden, que es lo único que hace útil una sugerencia,
y que cada propuesta venga con el motivo por el que está ahí.

Se omiten automáticamente si PostgreSQL no está accesible.
"""

from app import database


def _video(db, video_id, titulo, categoria, dispositivo, texto="", fragmentos=None):
    v = database.Video(
        video_id=video_id,
        titulo=titulo,
        canal="MySmartWindow",
        url=f"https://www.youtube.com/watch?v={video_id}",
        miniatura_url="",
        categoria=categoria,
        dispositivo=dispositivo,
        transcripcion_texto=texto,
    )
    db.add(v)
    db.flush()
    for segundo, frase in (fragmentos or []):
        db.add(database.VideoFragmento(video_id=v.id, segundo_inicio=segundo, duracion=15, texto=frase))
    db.commit()
    return v


def _ticket(db, **extra):
    datos = {
        "instalador": "Marta Gil",
        "obra": "Torre Oeste",
        "dispositivo": "",
        "sintoma": "El dispositivo no responde",
        "estado": "en_espera",
    }
    datos.update(extra)
    return database.crear_ticket_sat(db, datos)


def _titulos(resultado):
    return [v["titulo"] for v in resultado["videos"]]


def test_el_grupo_del_ticket_manda_sobre_el_resto(db):
    """Es la señal que no depende de cómo esté redactado el síntoma."""
    _video(db, "vid_vinc", "Vinculación AP", "VINCULACION", "General")
    _video(db, "vid_otro", "Menú de edición", "CONFIGURACION_APP", "General")
    ticket = _ticket(db, grupo="VINCULACION")

    resultado = database.sugerir_documentacion_para_ticket(db, ticket.id)

    assert _titulos(resultado)[0] == "Vinculación AP"
    assert resultado["grupo"] == "VINCULACION"


def test_el_dispositivo_casa_aunque_se_escriba_distinto(db):
    """Los tickets guardan 'C-Wall' y los vídeos 'C-WALL': comparar en crudo no casaba."""
    _video(db, "vid_wall", "Instalación C-WALL", "INSTALACION", "C-WALL")
    ticket = _ticket(db, dispositivo="C-Wall")

    resultado = database.sugerir_documentacion_para_ticket(db, ticket.id)

    assert _titulos(resultado) == ["Instalación C-WALL"]
    assert "Mismo dispositivo (C-Wall)" in resultado["videos"][0]["motivos"]


def test_el_sintoma_pesa_mas_que_el_dispositivo(db):
    """Once vídeos son 'Connect-1': sin esto, la primera sugerencia salía por compartir aparato."""
    _video(db, "vid_gen", "Guía del candado de seguridad", "CONFIGURACION_APP", "General",
           texto="activar candado", fragmentos=[(42, "Activación del candado de seguridad")])
    _video(db, "vid_disp", "Menú de edición", "CONFIGURACION_APP", "Connect-1")
    ticket = _ticket(db, dispositivo="Connect-1", sintoma="candado")

    resultado = database.sugerir_documentacion_para_ticket(db, ticket.id)

    assert _titulos(resultado)[0] == "Guía del candado de seguridad"


def test_la_sugerencia_apunta_al_segundo_del_fragmento(db):
    """El minuto exacto es lo que aporta el vídeo frente al manual en PDF."""
    _video(db, "vid_seg", "Vinculación AP", "VINCULACION", "C-PULSAR",
           texto="hard reset", fragmentos=[(0, "Pantalla inicial"), (128, "Aviso de hard reset previo")])
    ticket = _ticket(db, sintoma="hard reset")

    resultado = database.sugerir_documentacion_para_ticket(db, ticket.id)

    assert resultado["videos"][0]["segundo"] == 128
    assert resultado["videos"][0]["tiempo_formateado"] == "02:08"
    assert resultado["videos"][0]["url"].endswith("&t=128s")


def test_cada_sugerencia_explica_por_que_esta(db):
    """Una lista ordenada sin motivo obliga a abrir los vídeos uno por uno."""
    _video(db, "vid_todo", "Vinculación del C-Pulsar", "VINCULACION", "C-PULSAR",
           texto="no vincula", fragmentos=[(10, "El dispositivo no vincula con la app")])
    ticket = _ticket(db, grupo="VINCULACION", dispositivo="C-Pulsar", sintoma="no vincula")

    motivos = database.sugerir_documentacion_para_ticket(db, ticket.id)["videos"][0]["motivos"]

    assert any("Mismo grupo" in m for m in motivos)
    assert any("Mismo dispositivo" in m for m in motivos)
    assert any("síntoma" in m for m in motivos)


def test_un_sintoma_redactado_como_frase_no_se_queda_sin_nada(db):
    """La búsqueda exige todos los términos; una frase larga no casaba con ningún vídeo."""
    _video(db, "vid_pers", "Servicio de persiana", "CONFIGURACION_APP", "General",
           texto="persiana", fragmentos=[(5, "Configuración del servicio de persiana")])
    ticket = _ticket(db, sintoma="La persiana sube al pulsar la orden de bajar desde la aplicación")

    resultado = database.sugerir_documentacion_para_ticket(db, ticket.id)

    assert _titulos(resultado) == ["Servicio de persiana"]
    assert any("parte del síntoma" in m for m in resultado["videos"][0]["motivos"])


def test_un_ticket_inexistente_no_revienta(db):
    assert database.sugerir_documentacion_para_ticket(db, 999999) == {
        "videos": [], "grupo": "", "dispositivo": ""
    }


def test_sin_nada_que_cruzar_devuelve_lista_vacia(db):
    """Mejor ninguna sugerencia que una arbitraria."""
    _video(db, "vid_solo", "Instalación C-WALL", "INSTALACION", "C-WALL")
    ticket = _ticket(db, dispositivo="", sintoma="zzz")

    assert database.sugerir_documentacion_para_ticket(db, ticket.id)["videos"] == []
