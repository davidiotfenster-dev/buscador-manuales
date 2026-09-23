"""El buscador contra PostgreSQL real.

Medido sobre la base real antes del cambio, con los síntomas de los tickets como
consultas: 147 ms de mediana y el 73 % de las búsquedas SIN NINGÚN resultado.
Las causas eran que todas las palabras eran obligatorias y que las tildes
importaban («instalacion» no encontraba nada; «instalación», nueve páginas).

Estos tests fijan lo que un técnico espera sin pensarlo: que escribir sin
tildes, con una errata o con una frase entera encuentre lo mismo que escribir
bien, y que lo que coincide del todo salga primero.
"""

import pytest

from app import busqueda, database


def _manual(db, nombre, paginas, dispositivo="Connect-1", categoria="General", nivel="publico"):
    m = database.Manual(
        nombre_original=nombre,
        nombre_archivo=f"{nombre.lower().replace(' ', '_')}.pdf",
        dispositivo=dispositivo,
        categoria=categoria,
        num_paginas=len(paginas),
        nivel_acceso=nivel,
    )
    db.add(m)
    db.flush()
    for i, texto in enumerate(paginas, start=1):
        db.add(database.Pagina(manual_id=m.id, numero_pagina=i, texto=texto))
    db.commit()
    return m


def _video(db, video_id, titulo, fragmentos, categoria="General", dispositivo="General"):
    v = database.Video(video_id=video_id, titulo=titulo, canal="MySmartWindow",
                       url=f"https://www.youtube.com/watch?v={video_id}", miniatura_url="",
                       categoria=categoria, dispositivo=dispositivo, transcripcion_texto="")
    db.add(v)
    db.flush()
    for segundo, frase in fragmentos:
        db.add(database.VideoFragmento(video_id=v.id, segundo_inicio=segundo, duracion=15, texto=frase))
    db.commit()
    return v


def _buscar(db, consulta, **kw):
    """Lo mismo que hace `database.buscar()`, pero sobre la sesión del test."""
    prep = busqueda.preparar_consulta(db, consulta)
    return {
        "prep": prep,
        "manuales": busqueda.buscar_manuales(db, prep, **kw),
        "videos": busqueda.buscar_videos(db, prep, **kw),
    }


def _nombres(res):
    return [r["nombre"] for r in res["manuales"]]


# ── Tildes ──────────────────────────────────────────────────────────────────

def test_sin_tilde_encuentra_lo_escrito_con_tilde(db):
    """La regresión exacta: «instalacion» no encontraba ninguna página."""
    _manual(db, "Guía de montaje", ["La instalación del módulo se hace en el cajón."])
    assert _nombres(_buscar(db, "instalacion")) == ["Guía de montaje"]


def test_con_tilde_encuentra_lo_escrito_sin_tilde(db):
    """Los tickets y muchas notas se escriben sin tildes; el otro sentido también cuenta."""
    _manual(db, "Notas de obra", ["La vinculacion se hizo desde el movil del cliente."])
    assert _nombres(_buscar(db, "vinculación")) == ["Notas de obra"]


def test_la_palabra_encuentra_sus_otras_formas(db):
    """Se probó a cambiar el índice a 'spanish_unaccent' y rompía esto.

    Esa configuración quita la tilde antes de extraer la raíz, y el extractor
    deja de reconocer el sufijo «-ación»: «instalación» dejaba de encontrar
    «instalar». Por eso las tildes se resuelven en la consulta, no en el índice.
    """
    _manual(db, "Guía de montaje", ["Para instalar el equipo, corte la corriente."])
    assert _nombres(_buscar(db, "instalacion")) == ["Guía de montaje"]
    assert _nombres(_buscar(db, "instalación")) == ["Guía de montaje"]


# ── Frases largas ───────────────────────────────────────────────────────────

def test_una_frase_larga_no_se_queda_sin_resultados(db):
    """Antes todas las palabras eran obligatorias: una frase casi nunca casaba."""
    _manual(db, "Averías", ["Si la persiana no sube, revise el final de carrera."])
    res = _buscar(db, "la persiana no sube cuando le doy a la orden desde el movil")
    assert _nombres(res) == ["Averías"]
    assert res["manuales"][0]["coincidencia_completa"] is False


def test_lo_que_coincide_del_todo_sale_primero(db):
    _manual(db, "Parcial", ["La persiana es de aluminio. " * 3])
    _manual(db, "Completo", ["La persiana no sube: revise el motor."])
    res = _buscar(db, "persiana no sube motor")
    assert _nombres(res)[0] == "Completo"
    assert res["manuales"][0]["coincidencia_completa"] is True


# ── Erratas y palabras a medias ─────────────────────────────────────────────

def test_una_errata_se_corrige_con_el_vocabulario_real(db):
    _manual(db, "Puesta en marcha", ["La calibración del motor tarda un minuto."])
    res = _buscar(db, "calibarcion")
    assert _nombres(res) == ["Puesta en marcha"]
    assert res["prep"]["correcciones"], "debería avisar de que ha corregido la consulta"


def test_no_se_corrige_hacia_una_palabra_que_no_se_parece(db):
    """Corregir a cualquier cosa es peor que no encontrar nada."""
    _manual(db, "Puesta en marcha", ["La calibración del motor tarda un minuto."])
    res = _buscar(db, "xylofonoq")
    assert res["prep"]["correcciones"] == []
    assert _nombres(res) == []


def test_la_ultima_palabra_se_busca_a_medio_escribir(db):
    _manual(db, "Puesta en marcha", ["La calibración del motor tarda un minuto."])
    assert _nombres(_buscar(db, "motor calib")) == ["Puesta en marcha"]


def test_la_correccion_se_entera_sola_de_los_documentos_nuevos(db, monkeypatch):
    """El vocabulario se reconstruye cuando cambian los datos, sin tocar nada.

    Subir un manual no puede exigir reiniciar el servidor para que sus palabras
    entren en la corrección de erratas.
    """
    monkeypatch.setattr(busqueda, "VIGENCIA_VOCABULARIO_S", 0.0)
    _manual(db, "Primero", ["Texto sin relación alguna."])
    assert _buscar(db, "anemometro")["prep"]["correcciones"] == []

    _manual(db, "Estación meteorológica", ["El anemómetro mide la velocidad del viento."])
    res = _buscar(db, "anemonetro")
    assert res["prep"]["correcciones"], "la palabra del manual nuevo no ha entrado en el vocabulario"
    assert _nombres(res) == ["Estación meteorológica"]


# ── Sintaxis y filtros ──────────────────────────────────────────────────────

def test_se_puede_excluir_una_palabra(db):
    _manual(db, "Gestual", ["La persiana con control gestual."])
    _manual(db, "Manual", ["La persiana con pulsador de pared."])
    assert _nombres(_buscar(db, "persiana -gestual")) == ["Manual"]


def test_una_consulta_de_solo_palabras_vacias_no_revienta(db):
    _manual(db, "Cualquiera", ["La de el en y."])
    res = _buscar(db, "la de el")
    assert res["prep"]["tsquery"] is None
    assert _nombres(res) == []


def test_el_filtro_de_dispositivo_no_distingue_mayusculas(db):
    """En la base conviven «CONNECT-1» y «Connect-1»."""
    _manual(db, "Manual C1", ["Instrucciones de montaje."], dispositivo="CONNECT-1")
    assert _nombres(_buscar(db, "montaje", dispositivo="Connect-1")) == ["Manual C1"]


def test_un_comercial_no_ve_la_documentacion_tecnica(db):
    """El control de acceso por rol se conserva en el motor nuevo."""
    _manual(db, "Esquema interno", ["Cableado del relé de potencia."], nivel="tecnico")
    assert _nombres(_buscar(db, "cableado", role="comercial")) == []
    assert _nombres(_buscar(db, "cableado", role="tecnico")) == ["Esquema interno"]


# ── Vídeos ──────────────────────────────────────────────────────────────────

def test_el_video_salta_al_fragmento_que_habla_de_lo_buscado(db):
    """El título es igual para todos los fragmentos; sin desempate, el enlace iría al segundo 0."""
    _video(db, "v1", "Configuración del Connect", [(0, "Bienvenidos al canal"),
                                                   (95, "Para calibrar la persiana pulse tres veces")])
    res = _buscar(db, "calibrar persiana")
    assert res["videos"][0]["segundo"] == 95
    assert res["videos"][0]["url"].endswith("&t=95s")


def test_los_videos_tampoco_dependen_de_las_tildes(db):
    _video(db, "v2", "Emparejamiento", [(10, "La vinculación se hace desde la aplicación")])
    assert [v["titulo"] for v in _buscar(db, "vinculacion aplicacion")["videos"]] == ["Emparejamiento"]


def test_la_funcion_publica_devuelve_lo_que_se_ha_anadido_a_la_consulta(db, monkeypatch):
    """`database.buscar` expone correcciones y sinónimos para poder enseñarlos."""
    _manual(db, "Puesta en marcha", ["La calibración del motor tarda un minuto."])
    monkeypatch.setattr(database, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)
    res = database.buscar("calibarcion")
    assert res["total_manuales"] == 1
    assert res["correcciones"]
    assert "sinonimos" in res


@pytest.mark.parametrize("errata, bien", [
    ("vinuclar", "vincular"),     # dos letras intercambiadas
    ("perisana", "persiana"),     # la errata más típica escribiendo en el móvil
    ("instlacion", "instalación"),  # letra que falta y sin tilde
])
def test_las_erratas_de_movil_encuentran_lo_mismo_que_bien_escrito(db, errata, bien):
    """Los trigramas solos no veían las letras intercambiadas: «vinuclar» se
    parece a «vincular» solo un 0,38. La distancia de edición sí lo ve: un cambio."""
    _manual(db, "Manual A", ["Para vincular la persiana, complete la instalación desde la app."])
    assert _nombres(_buscar(db, errata)) == _nombres(_buscar(db, bien)) == ["Manual A"]


def test_una_palabra_bien_escrita_no_se_corrige(db):
    _manual(db, "Manual A", ["La persiana y el vinculo de la app."])
    assert _buscar(db, "persiana")["prep"]["correcciones"] == []
