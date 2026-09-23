"""Qué cierre se deduce de cada combinación de acciones de SAT.

La métrica G10 —«¿la documentación fue suficiente?»— sale entera de esta
traducción, así que un criterio mal puesto no da error: da un porcentaje
equivocado que nadie sabe que lo está. Cada regla tiene aquí su caso.

La frontera de fondo es una sola: ¿bastó con explicar, o tuvo que actuar
alguien? Una llamada sigue siendo explicar. Tocar el firmware, no.
"""

import pytest

from tools import cerrar_historico as ch


def test_solo_explicar_cuenta_como_documentacion_suficiente():
    cierre = ch.derivar("resuelto", "Videos, Mensaje Informativo")

    assert cierre["resuelto"] is True
    assert cierre["doc_suficiente"] is True
    assert cierre["escalado"] is False


def test_una_llamada_sigue_siendo_explicar():
    """62 de 119 incidencias llevan «Llamada»: si contara como fracaso de la
    documentación, la métrica diría que casi nada funciona. Guiar por
    teléfono es documentación haciendo su trabajo, solo que en directo."""
    cierre = ch.derivar("resuelto", "Llamada, Reset, Tiempo")

    assert cierre["doc_suficiente"] is True
    assert cierre["motivo"] == "explicado"


@pytest.mark.parametrize("accion", [
    "Firmware", "servidor", "Reposición", "Asistencia Presencial",
    "Ofertar Nuevos Dispositivos",
])
def test_si_tuvo_que_actuar_alguien_la_documentacion_no_basto(accion):
    cierre = ch.derivar("resuelto", f"Llamada, Videos, {accion}")

    assert cierre["doc_suficiente"] is False
    assert cierre["escalado"] is True
    assert cierre["motivo"] == "intervencion"


def test_la_incomparecencia_no_es_resuelta_ni_dice_nada_de_la_documentacion():
    """El cliente dejó de responder. Contarlo como resuelto inflaría el
    porcentaje con casos que nadie sabe cómo acabaron."""
    cierre = ch.derivar("resuelto", "Llamada, incompareciencia")

    assert cierre["resuelto"] is False
    assert cierre["doc_suficiente"] is None


def test_la_incomparecencia_manda_sobre_el_resto_de_acciones():
    cierre = ch.derivar("resuelto", "Videos, Mensaje Informativo, incompareciencia")

    assert cierre["motivo"] == "incomparecencia"


def test_la_intervencion_manda_sobre_haber_explicado():
    """Mandar el vídeo y acabar yendo a la obra no es un éxito a medias:
    la documentación no resolvió."""
    cierre = ch.derivar("resuelto", "Videos, Asistencia Presencial")

    assert cierre["doc_suficiente"] is False


def test_la_incidencia_ajena_no_puntua_en_la_metrica():
    cierre = ch.derivar("resuelto", "Llamada, Incidencia Ajena a nosotros")

    assert cierre["resuelto"] is True
    assert cierre["doc_suficiente"] is None
    assert cierre["escalado"] is True


def test_un_ticket_en_espera_no_se_cierra():
    assert ch.derivar("en_espera", "Llamada, Videos") is None


def test_un_resuelto_sin_acciones_no_se_inventa():
    assert ch.derivar("resuelto", None) is None
    assert ch.derivar("resuelto", "") is None
    assert ch.derivar("resuelto", "  ,  ") is None


def test_las_acciones_se_leen_con_espacios_y_sin_ellos():
    con = ch.acciones_de("Llamada, Videos ,Reset")

    assert con == {"Llamada", "Videos", "Reset"}


def test_el_vocabulario_cubre_las_doce_acciones_del_excel():
    """Si aparece una acción nueva en un Excel futuro, el script avisa en vez
    de tragársela en silencio; esta lista es la que sabe interpretar."""
    assert ch.CONOCIDAS == {
        "Llamada", "Mensaje Informativo", "Videos", "incompareciencia",
        "Tiempo", "Firmware", "Reset", "Incidencia Ajena a nosotros",
        "Asistencia Presencial", "servidor", "Ofertar Nuevos Dispositivos",
        "Reposición",
    }


def test_la_descripcion_conserva_las_acciones_originales():
    """El texto derivado no puede tapar el dato de partida: quien lea el
    cierre tiene que poder comprobar de dónde salió."""
    texto = ch.descripcion("Videos, Firmware", "intervencion")

    assert "Videos, Firmware" in texto
    assert "no bastó" in texto
