"""
Router de Gestión de Manuales PDF, Streaming Seguro, Miniaturas y Packs de Obra.
"""

import asyncio
import io
import logging
import os
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pypdf import PdfReader
from sqlalchemy import func

from .. import database
from ..auth import get_current_user, require_admin, _check_rbac

logger = logging.getLogger("buscador_manuales.manuales")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_MANUALES_DIR = BASE_DIR / "manuales"
DEFAULT_CACHE_MINIATURAS_DIR = BASE_DIR / "cache_miniaturas"

DEFAULT_MANUALES_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_CACHE_MINIATURAS_DIR.mkdir(parents=True, exist_ok=True)

def get_manuales_dir() -> Path:
    main_mod = sys.modules.get("app.main")
    if main_mod and hasattr(main_mod, "MANUALES_DIR"):
        return Path(main_mod.MANUALES_DIR)
    return DEFAULT_MANUALES_DIR

def get_cache_miniaturas_dir() -> Path:
    main_mod = sys.modules.get("app.main")
    if main_mod and hasattr(main_mod, "CACHE_MINIATURAS_DIR"):
        return Path(main_mod.CACHE_MINIATURAS_DIR)
    return DEFAULT_CACHE_MINIATURAS_DIR

# --- OCR opcional
_OCR_DISPONIBLE = False
_OCR_IDIOMAS = "eng"
try:
    import pytesseract
    pytesseract.get_tesseract_version()
    _OCR_DISPONIBLE = True
    try:
        idiomas_instalados = set(pytesseract.get_languages(config=""))
        preferidos = [i for i in ("spa", "eng") if i in idiomas_instalados]
        _OCR_IDIOMAS = "+".join(preferidos) if preferidos else "eng"
    except Exception:
        _OCR_IDIOMAS = "eng"
except Exception:
    pass

try:
    import pypdfium2 as pdfium
    _PYPDFIUM_DISPONIBLE = True
except Exception:
    _PYPDFIUM_DISPONIBLE = False

_MAX_UPLOAD_SIZE = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "50")) * 1024 * 1024

def _renderizar_pagina_como_imagen(ruta_pdf: Path, numero_pagina: int, escala: float = 2.0):
    pdf = pdfium.PdfDocument(str(ruta_pdf))
    try:
        pagina = pdf[numero_pagina - 1]
        bitmap = pagina.render(scale=escala)
        return bitmap.to_pil()
    finally:
        pdf.close()

def _invalidar_cache_miniaturas(manual_id: Optional[int] = None) -> None:
    """
    Invalida miniaturas cacheadas en disco.
    Si se especifica manual_id, elimina únicamente las de dicho manual ({manual_id}_*.png).
    Si es None, elimina todas las miniaturas cacheadas.
    """
    cache_dir = get_cache_miniaturas_dir()
    try:
        if not cache_dir.exists():
            return
        patron = f"{manual_id}_*.png" if manual_id is not None else "*.png"
        for archivo in cache_dir.glob(patron):
            try:
                archivo.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Error eliminando miniatura en caché {archivo.name}: {e}")
    except Exception as e:
        logger.warning(f"Error invalidando caché de miniaturas: {e}")

def _extraer_texto_por_pagina(ruta_pdf: Path):
    lector = PdfReader(str(ruta_pdf))
    resultado = []
    for indice, pagina in enumerate(lector.pages, start=1):
        texto = ""
        try:
            texto = pagina.extract_text() or ""
            texto = texto.replace("\x00", "")
        except Exception:
            texto = ""

        if texto.strip():
            resultado.append((texto, False))
            continue

        if _OCR_DISPONIBLE and _PYPDFIUM_DISPONIBLE:
            try:
                imagen = _renderizar_pagina_como_imagen(ruta_pdf, indice)
                texto_ocr = pytesseract.image_to_string(imagen, lang=_OCR_IDIOMAS)
                texto_ocr = texto_ocr.replace("\x00", "")
                resultado.append((texto_ocr, True))
                continue
            except Exception as e:
                logger.warning(f"Error en OCR para '{ruta_pdf.name}' pág {indice}: {e}")
        resultado.append(("", False))
    return resultado

def _nombre_archivo_disponible(nombre: str) -> str:
    manuales_dir = get_manuales_dir()
    nombre_limpio = Path(nombre).name
    nombre_limpio = re.sub(r'[^a-zA-Z0-9_.\-\(\)\[\] ]', '_', nombre_limpio)
    if not nombre_limpio or nombre_limpio.startswith('.'):
        nombre_limpio = "manual_sin_nombre.pdf"
    
    destino = manuales_dir / nombre_limpio
    if not destino.exists():
        return nombre_limpio
    stem, suf = Path(nombre_limpio).stem, Path(nombre_limpio).suffix
    i = 1
    while (manuales_dir / f"{stem}_{i}{suf}").exists():
        i += 1
    return f"{stem}_{i}{suf}"

class EditarManualDTO(BaseModel):
    dispositivo: str = ""
    categoria: str = ""
    nivel_acceso: str = "publico"
    etiquetas: str = ""

router = APIRouter(tags=["Manuales PDF"])

@router.post("/api/subir")
async def subir_manuales(
    archivos: List[UploadFile] = File(...),
    dispositivo: str = Form(""),
    categoria: str = Form(""),
    nivel_acceso: str = Form("publico"),
    etiquetas: str = Form(""),
    current_user: database.User = Depends(require_admin)
):
    manuales_dir = get_manuales_dir()
    resultados = []
    for archivo in archivos:
        if not archivo.filename.lower().endswith(".pdf"):
            resultados.append({"archivo": archivo.filename, "ok": False, "error": "No es un PDF"})
            continue

        nombre_guardado = _nombre_archivo_disponible(archivo.filename)
        ruta_destino = manuales_dir / nombre_guardado
        
        # Validar que la ruta resuelta está dentro de MANUALES_DIR
        if not str(ruta_destino.resolve()).startswith(str(manuales_dir.resolve())):
            resultados.append({"archivo": archivo.filename, "ok": False, "error": "Nombre de archivo inválido"})
            continue
        
        contenido = await archivo.read()
        
        # Validar tamaño
        if len(contenido) > _MAX_UPLOAD_SIZE:
            resultados.append({"archivo": archivo.filename, "ok": False, "error": f"Archivo demasiado grande (máx {_MAX_UPLOAD_SIZE // (1024*1024)}MB)"})
            continue
        
        ruta_destino.write_bytes(contenido)

        try:
            loop = asyncio.get_running_loop()
            paginas = await loop.run_in_executor(None, _extraer_texto_por_pagina, ruta_destino)
        except Exception as e:
            ruta_destino.unlink(missing_ok=True)
            resultados.append({"archivo": archivo.filename, "ok": False, "error": f"Error: {e}"})
            continue

        manual_id = database.insertar_manual(
            nombre_original=archivo.filename,
            nombre_archivo=nombre_guardado,
            dispositivo=dispositivo,
            categoria=categoria,
            paginas=paginas,
            nivel_acceso=nivel_acceso,
            etiquetas=etiquetas
        )
        resultados.append({
            "archivo": archivo.filename,
            "ok": True,
            "id": manual_id,
            "paginas": len(paginas)
        })

    return {"resultados": resultados}

@router.post("/api/reindexar")
def reindexar_todo(current_user: database.User = Depends(require_admin)):
    _invalidar_cache_miniaturas()
    try:
        from sync_manuales import sincronizar_manuales
        res = sincronizar_manuales(dry_run=False, force=True)
        return {
            "ok": True,
            "total": res["total"],
            "insertados": res["insertados"],
            "actualizados": res["actualizados"],
            "errores": res["errores"]
        }
    except Exception as e:
        logger.error(f"Error en reindexar_todo: {e}")
        return {"ok": False, "error": str(e)}

@router.get("/api/manuales")
def listar_manuales(current_user: database.User = Depends(get_current_user)):
    filas = database.listar_manuales()
    return {
        "manuales": [
            {
                "id": f["id"],
                "nombre": f["nombre_original"],
                "archivo": f["nombre_archivo"],
                "dispositivo": f["dispositivo"],
                "categoria": f["categoria"],
                "etiquetas": f["etiquetas"],
                "paginas": f["num_paginas"],
                "fecha": f["fecha_subida"],
                "nivel_acceso": f["nivel_acceso"]
            }
            for f in filas if current_user.role == "admin" or (current_user.role != "comercial" or f["nivel_acceso"] == "publico")
        ]
    }

@router.put("/api/manuales/{manual_id}")
def editar_manual(manual_id: int, datos: EditarManualDTO, current_user: database.User = Depends(require_admin)):
    exito = database.actualizar_manual(
        manual_id=manual_id,
        dispositivo=datos.dispositivo,
        categoria=datos.categoria,
        nivel_acceso=datos.nivel_acceso,
        etiquetas=datos.etiquetas
    )
    if not exito:
        raise HTTPException(status_code=404, detail="Manual no encontrado")
    return {"ok": True, "mensaje": "Manual actualizado correctamente"}

@router.delete("/api/manuales/{manual_id}")
def eliminar_manual(manual_id: int, current_user: database.User = Depends(require_admin)):
    manual = database.obtener_manual(manual_id)
    if not manual:
        raise HTTPException(status_code=404, detail="Manual no encontrado")

    ruta = get_manuales_dir() / manual["nombre_archivo"]
    ruta.unlink(missing_ok=True)
    _invalidar_cache_miniaturas(manual_id)
    database.eliminar_manual(manual_id)
    return {"ok": True}

@router.get("/manuales/{nombre_archivo}")
def ver_manual(nombre_archivo: str, current_user: database.User = Depends(get_current_user)):
    manuales_dir = get_manuales_dir()
    nombre_decodificado = unquote(nombre_archivo).strip()
    nombre_limpio = Path(nombre_decodificado).name
    
    # Prevenir Path Traversal
    if ".." in nombre_decodificado or "/" in nombre_decodificado or "\\" in nombre_decodificado or nombre_decodificado != nombre_limpio:
        raise HTTPException(status_code=403, detail="Acceso denegado: intento de path traversal detectado")
    
    ruta = (manuales_dir / nombre_limpio).resolve()
    
    # Validar que la ruta resuelta está estrictamente dentro de MANUALES_DIR
    if not str(ruta).startswith(str(manuales_dir.resolve())):
        raise HTTPException(status_code=403, detail="Acceso denegado: ruta no permitida fuera del directorio seguro")
    
    if not ruta.exists() or not ruta.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado en el repositorio")
    
    # Verificar RBAC (fail-closed)
    manual_info = database.obtener_manual_por_archivo(nombre_limpio)
    if not manual_info:
        raise HTTPException(status_code=404, detail="Archivo no registrado en la biblioteca")
    if not _check_rbac(manual_info.get("nivel_acceso", "publico"), current_user.role):
        raise HTTPException(
            status_code=403, 
            detail="No tienes acceso a este documento técnico. Requiere permisos de Técnico o Administrador."
        )
        
    return FileResponse(
        ruta,
        media_type="application/pdf",
        filename=nombre_limpio,
        content_disposition_type="inline",
        headers={
            "X-Frame-Options": "SAMEORIGIN",
            "Content-Security-Policy": "frame-ancestors 'self'",
        }
    )

@router.get("/api/dispositivos")
def listar_dispositivos(current_user: database.User = Depends(get_current_user)):
    db = database.SessionLocal()
    try:
        query_m = db.query(database.Manual.dispositivo, func.count(database.Manual.id)).filter(
            database.Manual.dispositivo.isnot(None), database.Manual.dispositivo != ""
        )
        if current_user.role == "comercial":
            query_m = query_m.filter(database.Manual.nivel_acceso == "publico")
        m_counts = query_m.group_by(database.Manual.dispositivo).all()

        query_v = db.query(database.Video.dispositivo, func.count(database.Video.id)).filter(
            database.Video.dispositivo.isnot(None), database.Video.dispositivo != ""
        )
        if current_user.role == "comercial":
            query_v = query_v.filter(database.Video.nivel_acceso == "publico")
        v_counts = query_v.group_by(database.Video.dispositivo).all()

        mapa = {}
        for d, cm in m_counts:
            if d and d.strip():
                d_norm = d.strip()
                mapa[d_norm] = {"dispositivo": d_norm, "manuales": cm, "videos": 0}
        for d, cv in v_counts:
            if d and d.strip():
                d_norm = d.strip()
                if d_norm not in mapa:
                    mapa[d_norm] = {"dispositivo": d_norm, "manuales": 0, "videos": cv}
                else:
                    mapa[d_norm]["videos"] = cv

        return sorted(list(mapa.values()), key=lambda x: x["dispositivo"].lower())
    finally:
        db.close()

@router.get("/api/dispositivos/{dispositivo}/pack")
def descargar_pack_obra(dispositivo: str, current_user: database.User = Depends(get_current_user)):
    manuales_dir = get_manuales_dir()
    dispositivo_limpio = unquote(dispositivo).strip()
    db = database.SessionLocal()
    try:
        query_m = db.query(database.Manual).filter(
            func.lower(database.Manual.dispositivo) == func.lower(dispositivo_limpio)
        )
        if current_user.role == "comercial":
            query_m = query_m.filter(database.Manual.nivel_acceso == "publico")
        manuales = query_m.all()

        query_v = db.query(database.Video).filter(
            func.lower(database.Video.dispositivo) == func.lower(dispositivo_limpio)
        )
        if current_user.role == "comercial":
            query_v = query_v.filter(database.Video.nivel_acceso == "publico")
        videos = query_v.all()

        if not manuales and not videos:
            raise HTTPException(
                status_code=404, 
                detail=f"No se encontró documentación ni videos para el dispositivo '{dispositivo_limpio}'"
            )

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")
            readme_content = f"""================================================================================
MYSMARTWINDOW - PACK DE OBRA / DOCUMENTACIÓN TÉCNICA OFICIAL
DISPOSITIVO: {dispositivo_limpio.upper()}
================================================================================
Generado el: {fecha_str}
Solicitado por: {current_user.email} (Rol: {current_user.role.upper()})

Este paquete ha sido compilado automáticamente para permitir el acceso offline
a toda la documentación técnica, manuales de instalación y guías audiovisuales
necesarias para la puesta en marcha sobre el terreno.

CONTENIDO DEL PAQUETE:
- Carpeta 'Manuales_PDF/': Contiene {len(manuales)} archivo(s) PDF oficiales.
- Carpeta 'Videos_y_Tutoriales/': Contiene la guía y enlaces directos a los
  tutoriales de YouTube oficiales de @MySmartWindow correspondientes a este modelo.

SOPORTE TÉCNICO OFICIAL:
- Web: https://mysmartwindow.com
- Canal YouTube: https://www.youtube.com/@MySmartWindow
================================================================================
"""
            zip_file.writestr("README_LEEME.txt", readme_content)

            archivos_incluidos = 0
            nombres_usados = set()
            for m in manuales:
                ruta_pdf = manuales_dir / m.nombre_archivo
                if ruta_pdf.exists():
                    nombre_amigable = m.nombre_original or m.nombre_archivo
                    if not nombre_amigable.lower().endswith(".pdf"):
                        nombre_amigable += ".pdf"
                    
                    nombre_final = nombre_amigable
                    contador = 1
                    while nombre_final in nombres_usados:
                        nombre_final = f"{Path(nombre_amigable).stem}_{contador}.pdf"
                        contador += 1
                    nombres_usados.add(nombre_final)

                    zip_file.write(ruta_pdf, arcname=f"Manuales_PDF/{nombre_final}")
                    archivos_incluidos += 1

            if videos:
                guia_videos = f"""================================================================================
MYSMARTWINDOW - GUÍA DE VIDEOTUTORIALES OFICIALES DE YOUTUBE
DISPOSITIVO: {dispositivo_limpio.upper()}
================================================================================
Total videos disponibles: {len(videos)}
Canal oficial: https://www.youtube.com/@MySmartWindow

LISTADO DE TUTORIALES RECOMENDADOS:
--------------------------------------------------------------------------------
"""
                for idx, v in enumerate(videos, 1):
                    guia_videos += f"""
[{idx}] {v.titulo}
    - Enlace directo: {v.url}
    - Canal: {v.canal}
    - Categoría: {v.categoria or 'General'}
    - Etiquetas: {v.etiquetas or 'N/A'}
"""
                guia_videos += """--------------------------------------------------------------------------------
Consejo técnico: Para reproducir un tutorial sin conexión a internet durante
la obra, puedes descargar previamente el video desde la app de YouTube en tu
dispositivo móvil cuando dispongas de conexión Wi-Fi.
================================================================================
"""
                zip_file.writestr("Videos_y_Tutoriales/GUIA_VIDEOTUTORIALES_YOUTUBE.txt", guia_videos)

        zip_buffer.seek(0)
        nombre_sanitizado = re.sub(r'[^a-zA-Z0-9_\-]', '_', dispositivo_limpio)
        nombre_descarga = f"Pack_Obra_MySmartWindow_{nombre_sanitizado}.zip"

        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{nombre_descarga}"',
                "Cache-Control": "no-cache",
            }
        )
    finally:
        db.close()

def is_pypdfium_disponible() -> bool:
    main_mod = sys.modules.get("app.main")
    if main_mod and hasattr(main_mod, "_PYPDFIUM_DISPONIBLE"):
        return bool(main_mod._PYPDFIUM_DISPONIBLE)
    return _PYPDFIUM_DISPONIBLE

def renderizar_pagina(ruta_pdf, numero_pagina, escala=0.6):
    main_mod = sys.modules.get("app.main")
    if main_mod and hasattr(main_mod, "_renderizar_pagina_como_imagen"):
        return main_mod._renderizar_pagina_como_imagen(ruta_pdf, numero_pagina, escala=escala)
    return _renderizar_pagina_como_imagen(ruta_pdf, numero_pagina, escala=escala)

@router.get("/api/miniatura/{manual_id}/{numero_pagina}")
def miniatura_pagina(manual_id: int, numero_pagina: int, current_user: database.User = Depends(get_current_user)):
    if not is_pypdfium_disponible():
        raise HTTPException(status_code=501, detail="No disponible")

    manual = database.obtener_manual(manual_id)
    if manual is None:
        raise HTTPException(status_code=404)
    
    if not _check_rbac(manual.get("nivel_acceso", "publico"), current_user.role):
        raise HTTPException(status_code=403, detail="No tienes acceso a este documento")

    cache_dir = get_cache_miniaturas_dir()
    cache_path = cache_dir / f"{manual_id}_{numero_pagina}.png"
    if cache_path.exists():
        return FileResponse(cache_path, media_type="image/png")

    ruta = get_manuales_dir() / manual["nombre_archivo"]
    if not ruta.exists():
        raise HTTPException(status_code=404)

    try:
        imagen = renderizar_pagina(ruta, numero_pagina, escala=0.6)
        imagen.save(cache_path, format="PNG")
        return FileResponse(cache_path, media_type="image/png")
    except Exception as e:
        logger.warning(f"Error renderizando miniatura manual_id={manual_id} pág={numero_pagina}: {e}")
        raise HTTPException(status_code=500)
