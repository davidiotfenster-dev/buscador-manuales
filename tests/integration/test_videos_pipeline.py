"""El texto de los vídeos sobrevive a una resincronización, contra PostgreSQL real.

Los 43 vídeos del canal son grabaciones de pantalla sin narración: YouTube no
devuelve ninguna transcripción para ellos. Todo su texto —y con él la búsqueda
por minuto— viene del pipeline de visión de `../descarga-videos`, que tarda
horas en producirlo.

`insertar_video()` pisaba ese texto y borraba los fragmentos en cada llamada.
Como lo que llega de YouTube es cadena vacía, bastaba con volver a dar de alta
un vídeo ya procesado para dejarlo mudo otra vez, sin error ni aviso. Estos
tests fijan que eso no vuelva a pasar.

Se omiten automáticamente si PostgreSQL no está accesible.
"""

from app import database


PASOS = [
    {"start": 8, "duration": 15, "text": "[8s] Aviso de Hard Reset antes de la vinculación AP"},
    {"start": 26, "duration": 15, "text": "[26s] Pulsar CONECTAR A BDSMART"},
]


def _alta(db, video_id="j7V8uHqqbq0", texto="", fragmentos=None, **extra):
    datos = {
        "video_id": video_id,
        "titulo": "Vinculación AP de C-Pulsar",
        "canal": "MySmartWindow",
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "miniatura_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "transcripcion_texto": texto,
        "fragmentos": fragmentos,
    }
    datos.update(extra)
    return database.insertar_video(db=db, **datos)


def _fragmentos_de(db, video_db_id):
    return db.query(database.VideoFragmento).filter(
        database.VideoFragmento.video_id == video_db_id
    ).all()


def test_una_resincronizacion_sin_texto_no_borra_el_del_pipeline(db):
    """El caso real: YouTube no da transcripción de estos vídeos, devuelve ''."""
    vid = _alta(db, texto="[8s] Aviso de Hard Reset", fragmentos=PASOS)

    _alta(db, texto="", fragmentos=None)

    guardado = db.query(database.Video).filter(database.Video.id == vid).one()
    assert guardado.transcripcion_texto == "[8s] Aviso de Hard Reset"
    assert len(_fragmentos_de(db, vid)) == 2


def test_un_texto_nuevo_si_reemplaza_al_anterior(db):
    """La guarda protege de borrar, no impide actualizar."""
    vid = _alta(db, texto="descripción antigua", fragmentos=PASOS)

    _alta(db, texto="descripción mejorada", fragmentos=[PASOS[0]])

    guardado = db.query(database.Video).filter(database.Video.id == vid).one()
    assert guardado.transcripcion_texto == "descripción mejorada"
    assert len(_fragmentos_de(db, vid)) == 1


def test_los_metadatos_si_se_refrescan_en_cada_sincronizacion(db):
    """Título y miniatura salen de YouTube, que es su fuente legítima."""
    vid = _alta(db, texto="texto del pipeline", fragmentos=PASOS)

    _alta(db, titulo="Vinculación AP de C-Pulsar - MySmartWindow (2026)")

    guardado = db.query(database.Video).filter(database.Video.id == vid).one()
    assert guardado.titulo.endswith("(2026)")
    assert guardado.transcripcion_texto == "texto del pipeline"


def test_la_categoria_vacia_no_pisa_la_que_ya_habia(db):
    """La temática la fija el pipeline (VINCULACION, RESETEO...); la sync manda ''."""
    vid = _alta(db, categoria="VINCULACION", dispositivo="C-PULSAR")

    _alta(db, categoria="", dispositivo="")

    guardado = db.query(database.Video).filter(database.Video.id == vid).one()
    assert guardado.categoria == "VINCULACION"
    assert guardado.dispositivo == "C-PULSAR"


def test_el_alta_de_un_video_nuevo_guarda_sus_fragmentos(db):
    vid = _alta(db, video_id="mxnSQ1yJokk", texto="texto", fragmentos=PASOS)

    fragmentos = _fragmentos_de(db, vid)
    assert [f.segundo_inicio for f in fragmentos] == [8, 26]
