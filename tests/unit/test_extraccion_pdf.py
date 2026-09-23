"""Cuándo se recurre al OCR al indexar un PDF, y con qué texto se queda.

Los manuales llegan de dos formas: PDF generados por un programa, con capa de
texto, y escaneos que son una imagen. Hay un tercer caso, el que más se da y el
que más daño hace: un escaneo **con una pizca de texto encima** —un número de
página, una cabecera, una marca de agua del escáner—. Decidir «¿hay texto?
entonces no hace falta OCR» indexaba esa página con su pie y tiraba el contenido
entero, sin error y sin aviso.

El OCR de verdad necesita tesseract, que no tiene por qué estar en la máquina que
ejecuta los tests. Lo que se prueba aquí es la **decisión**: cuándo se llama al
OCR y con qué texto se acaba. El OCR se sustituye por una función controlada, así
que estos tests corren en cualquier sitio.
"""

import pytest
from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app import extraccion_pdf


PARRAFO = (
    "El dispositivo Connect-1 parpadea en rojo cuando pierde la red del "
    "domicilio. Mantener pulsado el boton lateral durante diez segundos "
    "fuerza el reinicio de fabrica del modulo y vuelve a emitir su wifi."
)


def _pdf(tmp_path, nombre, paginas):
    """Crea un PDF. Cada página es una lista de líneas de texto real."""
    ruta = tmp_path / nombre
    c = canvas.Canvas(str(ruta), pagesize=A4)
    for lineas in paginas:
        c.setFont("Helvetica", 11)
        for i, linea in enumerate(lineas):
            c.drawString(50, 780 - i * 16, linea)
        c.showPage()
    c.save()
    return ruta


def _pdf_solo_imagen(tmp_path, nombre, pie=None):
    """PDF cuyo contenido es una imagen, con un pie de texto real opcional."""
    imagen = tmp_path / "pagina.png"
    img = Image.new("RGB", (800, 1000), "white")
    ImageDraw.Draw(img).text((40, 40), "contenido dibujado", fill="black")
    img.save(imagen)

    ruta = tmp_path / nombre
    c = canvas.Canvas(str(ruta), pagesize=A4)
    c.drawImage(ImageReader(str(imagen)), 40, 200, width=500, height=600)
    if pie:
        c.setFont("Helvetica", 8)
        c.drawString(40, 40, pie)
    c.save()
    return ruta


@pytest.fixture
def ocr_falso(monkeypatch):
    """Sustituye el OCR por un texto fijo y anota si llegó a llamarse."""
    llamadas = []

    def _fake(ruta_pdf, numero_pagina):
        llamadas.append(numero_pagina)
        return "TEXTO RECUPERADO POR OCR de la imagen de la pagina"

    monkeypatch.setattr(extraccion_pdf, "_ocr_de_pagina", _fake)
    return llamadas


def test_una_pagina_con_texto_suficiente_no_pasa_por_ocr(tmp_path, ocr_falso):
    """El OCR es lento: los PDF normales no deben pagarlo."""
    ruta = _pdf(tmp_path, "texto.pdf", [[PARRAFO[:60], PARRAFO[60:120]]])

    paginas = extraccion_pdf.extraer_texto_por_pagina(ruta)

    assert ocr_falso == []
    assert paginas[0][1] is False
    assert "Connect-1" in paginas[0][0]


def test_una_pagina_sin_nada_de_texto_va_al_ocr(tmp_path, ocr_falso):
    ruta = _pdf_solo_imagen(tmp_path, "escaneo.pdf")

    paginas = extraccion_pdf.extraer_texto_por_pagina(ruta)

    assert ocr_falso == [1]
    assert paginas[0][1] is True
    assert "RECUPERADO POR OCR" in paginas[0][0]


def test_un_escaneo_con_pie_de_pagina_tambien_va_al_ocr(tmp_path, ocr_falso):
    """El caso que se perdía entero: había texto, pero no era el contenido."""
    ruta = _pdf_solo_imagen(tmp_path, "mixta.pdf", pie="Pag. 1 - documento escaneado")

    paginas = extraccion_pdf.extraer_texto_por_pagina(ruta)

    assert ocr_falso == [1]
    assert paginas[0][1] is True
    assert "RECUPERADO POR OCR" in paginas[0][0]
    # El pie tampoco se tira: puede ser la referencia del documento.
    assert "documento escaneado" in paginas[0][0]


def test_el_pie_no_se_repite_si_el_ocr_ya_lo_leyo(tmp_path, monkeypatch):
    """El OCR lee la página entera, pie incluido."""
    monkeypatch.setattr(
        extraccion_pdf, "_ocr_de_pagina",
        lambda r, n: "Pag. 1 - documento escaneado\ncontenido de la imagen",
    )
    ruta = _pdf_solo_imagen(tmp_path, "mixta.pdf", pie="Pag. 1 - documento escaneado")

    texto = extraccion_pdf.extraer_texto_por_pagina(ruta)[0][0]

    assert texto.count("Pag. 1 - documento escaneado") == 1


def test_si_el_ocr_no_aporta_nada_se_conserva_la_capa_de_texto(tmp_path, monkeypatch):
    """Nunca se empeora lo que ya se tenía."""
    monkeypatch.setattr(extraccion_pdf, "_ocr_de_pagina", lambda r, n: "")
    ruta = _pdf_solo_imagen(tmp_path, "mixta.pdf", pie="Referencia REF-4471")

    texto, uso_ocr = extraccion_pdf.extraer_texto_por_pagina(ruta)[0]

    assert uso_ocr is False
    assert "REF-4471" in texto


def test_sin_ocr_disponible_el_pdf_escaneado_no_revienta(tmp_path, monkeypatch):
    """Sin tesseract la aplicación sigue funcionando, solo indexa menos."""
    monkeypatch.setattr(extraccion_pdf, "OCR_DISPONIBLE", False)
    ruta = _pdf_solo_imagen(tmp_path, "escaneo.pdf")

    paginas = extraccion_pdf.extraer_texto_por_pagina(ruta)

    assert len(paginas) == 1
    assert paginas[0][1] is False


def test_cada_pagina_se_decide_por_separado(tmp_path, ocr_falso):
    """Un manual mezcla páginas generadas y páginas escaneadas."""
    ruta = _pdf(tmp_path, "mixto.pdf", [[PARRAFO[:60], PARRAFO[60:120]], ["x"]])

    paginas = extraccion_pdf.extraer_texto_por_pagina(ruta)

    assert len(paginas) == 2
    assert paginas[0][1] is False   # tenía texto de sobra
    assert paginas[1][1] is True    # una sola letra no es el contenido
    assert ocr_falso == [2]
