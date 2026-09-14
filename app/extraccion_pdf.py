"""Extracción del texto de un PDF, página a página, con OCR cuando hace falta.

Los manuales llegan de dos formas. Unos son PDF generados por un programa y
llevan una capa de texto que se lee directamente. Otros son escaneos: páginas
que son una imagen y no contienen una sola letra legible por software. Para los
segundos, la única salida es renderizar la página y pasarle OCR.

Hay un tercer caso, que es el que más se da en la práctica y el que más daño
hace: la página es un escaneo **pero lleva encima una pizca de texto real** —un
número de página, una cabecera, una marca de agua que añadió el escáner o el
gestor documental—. Quien decide «¿hay texto? entonces no hace falta OCR» indexa
esa página con veintinueve caracteres de pie de página y tira el contenido
entero, sin error y sin aviso.

Este módulo existe para que haya **una sola** implementación de esto. Antes
había dos: la de la subida, con OCR, y la del sincronizador, sin él. Como el
botón «Reindexar» usa la del sincronizador, pulsarlo reemplazaba el texto de
todos los manuales escaneados por nada.
"""

import logging
from pathlib import Path
from typing import List, Tuple

from pypdf import PdfReader

logger = logging.getLogger("buscador_manuales.extraccion")

# --- OCR opcional ---------------------------------------------------------
# Sin tesseract la aplicación sigue funcionando: los PDF con capa de texto se
# indexan igual y los escaneados quedan vacíos, que es lo que pasaba antes.
OCR_DISPONIBLE = False
OCR_IDIOMAS = "eng"
try:
    import pytesseract

    pytesseract.get_tesseract_version()
    OCR_DISPONIBLE = True
    try:
        idiomas_instalados = set(pytesseract.get_languages(config=""))
        preferidos = [i for i in ("spa", "eng") if i in idiomas_instalados]
        OCR_IDIOMAS = "+".join(preferidos) if preferidos else "eng"
    except Exception:
        OCR_IDIOMAS = "eng"
except Exception:
    pass

try:
    import pypdfium2 as pdfium

    PYPDFIUM_DISPONIBLE = True
except Exception:
    PYPDFIUM_DISPONIBLE = False


# Por debajo de esto, la capa de texto de una página no se considera el
# contenido de la página, sino un resto: un número de página, una cabecera o una
# marca de agua. Una página real de un manual pasa de largo este umbral con
# holgura, así que los PDF normales siguen sin pagar el coste del OCR.
UMBRAL_TEXTO_FIABLE = 100


def renderizar_pagina_como_imagen(ruta_pdf: Path, numero_pagina: int, escala: float = 2.0):
    """Convierte una página en imagen para poder pasarle OCR."""
    pdf = pdfium.PdfDocument(str(ruta_pdf))
    try:
        pagina = pdf[numero_pagina - 1]
        return pagina.render(scale=escala).to_pil()
    finally:
        pdf.close()


def _ocr_de_pagina(ruta_pdf: Path, numero_pagina: int) -> str:
    if not (OCR_DISPONIBLE and PYPDFIUM_DISPONIBLE):
        return ""
    try:
        imagen = renderizar_pagina_como_imagen(ruta_pdf, numero_pagina)
        return pytesseract.image_to_string(imagen, lang=OCR_IDIOMAS).replace("\x00", "")
    except Exception as e:
        logger.warning(f"Error en OCR para '{ruta_pdf.name}' pág {numero_pagina}: {e}")
        return ""


def extraer_texto_por_pagina(ruta_pdf: Path) -> List[Tuple[str, bool]]:
    """Devuelve una tupla (texto, se_uso_ocr) por cada página del PDF.

    Tres caminos, en este orden:

    1. La página trae una capa de texto con suficiente contenido: se usa y no se
       toca el OCR, que es lento.
    2. La página no trae nada: se renderiza y se le pasa OCR.
    3. La página trae una pizca de texto —un pie, una cabecera— pero el
       contenido está en la imagen: se hace OCR **igualmente** y se conservan
       los dos textos. Este es el caso que antes se perdía entero.

    Si el OCR no está disponible o no saca nada, se devuelve lo que hubiera en
    la capa de texto: nunca se empeora lo que ya se tenía.
    """
    lector = PdfReader(str(ruta_pdf))
    resultado: List[Tuple[str, bool]] = []

    for indice, pagina in enumerate(lector.pages, start=1):
        try:
            texto = (pagina.extract_text() or "").replace("\x00", "")
        except Exception:
            texto = ""

        if len(texto.strip()) >= UMBRAL_TEXTO_FIABLE:
            resultado.append((texto, False))
            continue

        texto_ocr = _ocr_de_pagina(ruta_pdf, indice)

        # El OCR solo manda si aporta más de lo que ya había. Sobre una página
        # casi vacía puede devolver ruido o nada, y en ese caso lo correcto es
        # quedarse con la capa de texto.
        if len(texto_ocr.strip()) > len(texto.strip()):
            capa = texto.strip()
            ocr = texto_ocr.strip()
            # El OCR lee la página entera, así que normalmente ya incluye el pie
            # o la cabecera que traía la capa de texto. Volver a añadirla solo
            # duplicaría esas líneas en el texto indexado.
            partes = [ocr] if (not capa or capa in ocr) else [capa, ocr]
            resultado.append(("\n".join(partes), True))
            continue

        resultado.append((texto, False))

    return resultado
