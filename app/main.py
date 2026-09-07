"""
Buscador de Manuales - aplicación principal FastAPI.
"""

import asyncio
import io
import logging
import os
import re
import json
import urllib.request
from urllib.parse import unquote
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy import func

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends, status
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pypdf import PdfReader
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from . import database

logger = logging.getLogger("buscador_manuales")

BASE_DIR = Path(__file__).resolve().parent.parent
MANUALES_DIR = BASE_DIR / "manuales"
MANUALES_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Buscador de Manuales")

app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")

# --- OCR opcional
_OCR_DISPONIBLE = False
_OCR_IDIOMAS = "eng"
try:
    import pytesseract
    from PIL import Image
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


# ---------------------------------------------------------------------
# Configuración de Seguridad y JWT
# ---------------------------------------------------------------------
SECRET_KEY = "super-secret-key-cambiar-en-produccion"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 1 semana

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token", auto_error=False)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(request: Request, token: str = Depends(oauth2_scheme)):
    if not token:
        token = request.query_params.get("token")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    db = database.SessionLocal()
    user = db.query(database.User).filter(database.User.email == email).first()
    db.close()
    
    if user is None:
        raise credentials_exception
    return user

def require_admin(current_user: database.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
    return current_user


# ---------------------------------------------------------------------
# Eventos y Utilidades
# ---------------------------------------------------------------------

@app.on_event("startup")
def _startup() -> None:
    database.init_db()
    if not _OCR_DISPONIBLE:
        logger.warning("OCR no disponible. Los PDF escaneados sin texto no se indexarán.")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"ocr_disponible": _OCR_DISPONIBLE},
    )

def _renderizar_pagina_como_imagen(ruta_pdf: Path, numero_pagina: int, escala: float = 2.0):
    pdf = pdfium.PdfDocument(str(ruta_pdf))
    try:
        pagina = pdf[numero_pagina - 1]
        bitmap = pagina.render(scale=escala)
        return bitmap.to_pil()
    finally:
        pdf.close()

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
                pass
        resultado.append(("", False))
    return resultado

def _nombre_archivo_disponible(nombre: str) -> str:
    destino = MANUALES_DIR / nombre
    if not destino.exists():
        return nombre
    stem, suf = destino.stem, destino.suffix
    i = 1
    while (MANUALES_DIR / f"{stem}_{i}{suf}").exists():
        i += 1
    return f"{stem}_{i}{suf}"


# ---------------------------------------------------------------------
# Endpoints de API
# ---------------------------------------------------------------------

@app.post("/api/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    import bcrypt
    db = database.SessionLocal()
    user = db.query(database.User).filter(database.User.email == form_data.username).first()
    db.close()
    
    if not user or not bcrypt.checkpw(form_data.password.encode('utf-8'), user.password_hash.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role, "email": user.email}

@app.get("/api/me")
def get_me(current_user: database.User = Depends(get_current_user)):
    return {"email": current_user.email, "role": current_user.role, "is_first_login": current_user.is_first_login}


# ---------------------------------------------------------------------
# Utilidades de YouTube y Extracción
# ---------------------------------------------------------------------

def _extraer_youtube_id(url_o_id: str) -> str:
    url_o_id = url_o_id.strip()
    if len(url_o_id) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', url_o_id):
        return url_o_id
    patrones = [
        r'(?:v=|\/)([a-zA-Z0-9_-]{11})(?:\?|&|\/|$)',
        r'youtu\.be\/([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})'
    ]
    for p in patrones:
        m = re.search(p, url_o_id)
        if m:
            return m.group(1)
    return ""

def _obtener_metadatos_youtube(video_id: str) -> dict:
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return {
                "titulo": data.get("title", f"Video {video_id}"),
                "canal": data.get("author_name", "MySmartWindow"),
                "miniatura_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
            }
    except Exception as e:
        logger.warning(f"No se pudieron obtener metadatos oEmbed para {video_id}: {e}")
        return {
            "titulo": f"Video {video_id}",
            "canal": "MySmartWindow",
            "miniatura_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        }

def _obtener_transcripcion_youtube(video_id: str) -> Tuple[str, list]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        ytt = YouTubeTranscriptApi()
        transcript = ytt.fetch(video_id, languages=('es', 'es-419', 'en'))
        raw_snippets = []
        texto_acumulado = []
        for s in transcript:
            raw_snippets.append({
                "start": s.start,
                "duration": s.duration,
                "text": s.text.replace("\n", " ").strip()
            })
            texto_acumulado.append(s.text.replace("\n", " ").strip())
        return " ".join(texto_acumulado), raw_snippets
    except Exception as e:
        logger.info(f"No se pudieron obtener subtítulos para {video_id}: {e}")
        return "", []

def _extraer_videos_canal(canal_url: str = "https://www.youtube.com/@MySmartWindow/videos") -> List[str]:
    try:
        req = urllib.request.Request(canal_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode('utf-8')
        matches = re.findall(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', html)
        unicos = []
        for vid in matches:
            if vid not in unicos:
                unicos.append(vid)
        return unicos
    except Exception as e:
        logger.error(f"Error extrayendo videos del canal {canal_url}: {e}")
        return []

def _detectar_dispositivo_video(titulo: str) -> str:
    titulo_upper = titulo.upper()
    if "PULSAR" in titulo_upper:
        return "C-PULSAR"
    elif "WALL" in titulo_upper:
        return "C-WALL"
    elif "CONNECT" in titulo_upper:
        if "CONNECT-2" in titulo_upper or "CONNECT 2" in titulo_upper:
            return "Connect-2"
        return "Connect-1"
    elif "WIFI" in titulo_upper:
        return "Contraseñas Wifi"
    return ""


class VideoCrearDTO(BaseModel):
    url: str
    dispositivo: str = ""
    categoria: str = "Tutoriales y Configuración"
    etiquetas: str = ""
    nivel_acceso: str = "publico"


class VideoEditarDTO(BaseModel):
    dispositivo: str = ""
    categoria: str = ""
    etiquetas: str = ""
    nivel_acceso: str = "publico"


class SincronizarCanalDTO(BaseModel):
    canal_url: str = "https://www.youtube.com/@MySmartWindow/videos"


class EditarManualDTO(BaseModel):
    dispositivo: str = ""
    categoria: str = ""
    nivel_acceso: str = "publico"
    etiquetas: str = ""


@app.post("/api/subir")
async def subir_manuales(
    archivos: List[UploadFile] = File(...),
    dispositivo: str = Form(""),
    categoria: str = Form(""),
    nivel_acceso: str = Form("publico"),
    etiquetas: str = Form(""),
    current_user: database.User = Depends(require_admin)
):
    resultados = []
    for archivo in archivos:
        if not archivo.filename.lower().endswith(".pdf"):
            resultados.append({"archivo": archivo.filename, "ok": False, "error": "No es un PDF"})
            continue

        nombre_guardado = _nombre_archivo_disponible(archivo.filename)
        ruta_destino = MANUALES_DIR / nombre_guardado
        contenido = await archivo.read()
        ruta_destino.write_bytes(contenido)

        try:
            paginas = _extraer_texto_por_pagina(ruta_destino)
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


@app.post("/api/reindexar")
def reindexar_todo(current_user: database.User = Depends(require_admin)):
    import os
    manuales = database.listar_manuales()
    exito = 0
    errores = []
    
    for manual in manuales:
        ruta_pdf = MANUALES_DIR / manual["nombre_archivo"]
        if not ruta_pdf.exists():
            errores.append(f"Archivo no encontrado: {manual['nombre_archivo']}")
            continue
            
        try:
            paginas = _extraer_texto_por_pagina(ruta_pdf)
            database.actualizar_paginas_manual(manual["id"], paginas)
            exito += 1
        except Exception as e:
            errores.append(f"Error procesando {manual['nombre_archivo']}: {e}")
            
    return {"ok": True, "reindexados": exito, "errores": errores}

@app.get("/api/buscar")
def buscar_manuales(
    q: str = "", 
    dispositivo: str = "", 
    categoria: str = "", 
    orden: str = "relevancia",
    current_user: database.User = Depends(get_current_user)
):
    if not q.strip():
        return {
            "resultados": [],
            "manuales": [],
            "videos": [],
            "total_manuales": 0,
            "total_videos": 0
        }
    
    res = database.buscar(q, dispositivo=dispositivo, categoria=categoria, orden=orden, role=current_user.role)
    return {
        "resultados": res.get("todos", []),
        "manuales": res.get("manuales", []),
        "videos": res.get("videos", []),
        "total_manuales": res.get("total_manuales", 0),
        "total_videos": res.get("total_videos", 0)
    }


@app.get("/api/filtros")
def obtener_filtros(current_user: database.User = Depends(get_current_user)):
    dispositivos, categorias, etiquetas = database.listar_filtros()
    return {"dispositivos": dispositivos, "categorias": categorias, "etiquetas": etiquetas}


@app.get("/api/sugerencias")
def obtener_sugerencias(current_user: database.User = Depends(get_current_user)):
    manuales = database.listar_manuales()
    dispositivos, categorias, etiquetas = database.listar_filtros()
    # Filtro básico de nombres según rol para no revelar nombres confidenciales a comerciales
    nombres = [m["nombre_original"] for m in manuales if current_user.role != "comercial" or m["nivel_acceso"] == "publico"]
    return {"nombres": nombres, "dispositivos": dispositivos, "categorias": categorias, "etiquetas": etiquetas}


@app.get("/api/manuales")
def listar_manuales(current_user: database.User = Depends(get_current_user)):
    # Esta vista normalmente la usa el Admin para gestionar la biblioteca
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


@app.put("/api/manuales/{manual_id}")
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


@app.delete("/api/manuales/{manual_id}")
def eliminar_manual(manual_id: int, current_user: database.User = Depends(require_admin)):
    manual = database.obtener_manual(manual_id)
    if not manual:
        raise HTTPException(status_code=404, detail="Manual no encontrado")

    ruta = MANUALES_DIR / manual["nombre_archivo"]
    ruta.unlink(missing_ok=True)
    database.eliminar_manual(manual_id)
    return {"ok": True}


# ---------------------------------------------------------------------
# Sincronización Automática Programada (Background Cron Worker)
# ---------------------------------------------------------------------

_ESTADO_SYNC_CRON = {
    "activo": True,
    "intervalo_horas": int(os.environ.get("YOUTUBE_SYNC_INTERVAL_HOURS", "24")),
    "ultima_ejecucion": None,
    "proxima_ejecucion": None,
    "ultimo_resultado": None
}

def _ejecutar_sincronizacion_canal(canal_url: str = "https://www.youtube.com/@MySmartWindow/videos") -> dict:
    canal_url = canal_url.strip()
    if not canal_url.endswith("/videos"):
        canal_url = canal_url.rstrip("/") + "/videos"
        
    vids = _extraer_videos_canal(canal_url)
    if not vids:
        return {"ok": False, "error": "No se encontraron videos en el canal"}
    
    procesados = 0
    errores = []
    
    for vid in vids:
        try:
            meta = _obtener_metadatos_youtube(vid)
            dispositivo = _detectar_dispositivo_video(meta["titulo"])
            transcripcion_texto, fragmentos = _obtener_transcripcion_youtube(vid)
            
            database.insertar_video(
                video_id=vid,
                titulo=meta["titulo"],
                canal=meta["canal"],
                url=f"https://www.youtube.com/watch?v={vid}",
                miniatura_url=meta["miniatura_url"],
                dispositivo=dispositivo,
                categoria="Tutoriales y Configuración",
                etiquetas="video, tutorial, configuracion, " + (dispositivo.lower() if dispositivo else ""),
                nivel_acceso="publico",
                transcripcion_texto=transcripcion_texto,
                fragmentos=fragmentos
            )
            procesados += 1
        except Exception as e:
            errores.append(f"Error en video {vid}: {e}")
            
    return {
        "ok": True, 
        "sincronizados": procesados, 
        "errores": errores,
        "timestamp": datetime.now().isoformat()
    }

async def _loop_sincronizacion_programada():
    """
    Tarea en segundo plano que sincroniza periódicamente los tutoriales de YouTube.
    """
    # Espera 15 segundos al inicio para asegurar que el servidor y DB estén completamente operativos
    await asyncio.sleep(15)
    
    while True:
        try:
            logger.info("Iniciando tarea programada: Sincronización periódica de YouTube @MySmartWindow...")
            _ESTADO_SYNC_CRON["ultima_ejecucion"] = datetime.now().isoformat()
            
            # Ejecutar en hilo secundario para no bloquear el bucle de eventos asíncrono
            loop = asyncio.get_running_loop()
            resultado = await loop.run_in_executor(None, _ejecutar_sincronizacion_canal, "https://www.youtube.com/@MySmartWindow/videos")
            _ESTADO_SYNC_CRON["ultimo_resultado"] = resultado
            logger.info(f"Sincronización automática de YouTube finalizada: {resultado.get('sincronizados', 0)} videos procesados.")
        except Exception as e:
            logger.error(f"Error en sincronizador programado de YouTube: {e}")
            _ESTADO_SYNC_CRON["ultimo_resultado"] = {"error": str(e)}

        intervalo_segundos = max(1, _ESTADO_SYNC_CRON["intervalo_horas"]) * 3600
        _ESTADO_SYNC_CRON["proxima_ejecucion"] = (datetime.now() + timedelta(seconds=intervalo_segundos)).isoformat()
        await asyncio.sleep(intervalo_segundos)

@app.on_event("startup")
async def iniciar_sincronizacion_en_segundo_plano():
    asyncio.create_task(_loop_sincronizacion_programada())


# ---------------------------------------------------------------------
# Endpoints de Videos (YouTube)
# ---------------------------------------------------------------------

@app.get("/api/videos/sync-status")
def obtener_estado_sincronizacion(current_user: database.User = Depends(require_admin)):
    return _ESTADO_SYNC_CRON


@app.post("/api/videos/sincronizar")
def sincronizar_canal_youtube(datos: SincronizarCanalDTO = None, current_user: database.User = Depends(require_admin)):
    canal_url = (datos.canal_url if datos and datos.canal_url else "https://www.youtube.com/@MySmartWindow/videos").strip()
    resultado = _ejecutar_sincronizacion_canal(canal_url)
    if not resultado.get("ok"):
        raise HTTPException(status_code=400, detail=resultado.get("error", "No se pudieron sincronizar los videos"))
    
    _ESTADO_SYNC_CRON["ultima_ejecucion"] = datetime.now().isoformat()
    _ESTADO_SYNC_CRON["ultimo_resultado"] = resultado
    return resultado


@app.post("/api/videos")
def agregar_video(datos: VideoCrearDTO, current_user: database.User = Depends(require_admin)):
    vid = _extraer_youtube_id(datos.url)
    if not vid:
        raise HTTPException(status_code=400, detail="URL o ID de YouTube inválido")
        
    meta = _obtener_metadatos_youtube(vid)
    dispositivo = datos.dispositivo or _detectar_dispositivo_video(meta["titulo"])
    transcripcion_texto, fragmentos = _obtener_transcripcion_youtube(vid)
    
    video_id_db = database.insertar_video(
        video_id=vid,
        titulo=meta["titulo"],
        canal=meta["canal"],
        url=f"https://www.youtube.com/watch?v={vid}",
        miniatura_url=meta["miniatura_url"],
        dispositivo=dispositivo,
        categoria=datos.categoria or "Tutoriales y Configuración",
        etiquetas=datos.etiquetas,
        nivel_acceso=datos.nivel_acceso,
        transcripcion_texto=transcripcion_texto,
        fragmentos=fragmentos
    )
    return {"ok": True, "id": video_id_db, "titulo": meta["titulo"]}


@app.get("/api/videos")
def listar_videos(current_user: database.User = Depends(get_current_user)):
    videos = database.listar_videos(role=current_user.role)
    return {"videos": videos}


@app.delete("/api/videos/{video_db_id}")
def eliminar_video(video_db_id: int, current_user: database.User = Depends(require_admin)):
    exito = database.eliminar_video(video_db_id)
    if not exito:
        raise HTTPException(status_code=404, detail="Video no encontrado")
    return {"ok": True}


@app.put("/api/videos/{video_db_id}")
def editar_video(video_db_id: int, datos: VideoEditarDTO, current_user: database.User = Depends(require_admin)):
    exito = database.actualizar_video(
        video_db_id=video_db_id,
        dispositivo=datos.dispositivo,
        categoria=datos.categoria,
        nivel_acceso=datos.nivel_acceso,
        etiquetas=datos.etiquetas
    )
    if not exito:
        raise HTTPException(status_code=404, detail="Video no encontrado")
    return {"ok": True, "mensaje": "Video actualizado"}


@app.get("/manuales/{nombre_archivo}")
def ver_manual(nombre_archivo: str, current_user: database.User = Depends(get_current_user)):
    ruta = MANUALES_DIR / nombre_archivo
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
    return FileResponse(
        ruta,
        media_type="application/pdf",
        filename=nombre_archivo,
        content_disposition_type="inline",
        headers={
            "X-Frame-Options": "SAMEORIGIN",
            "Content-Security-Policy": "frame-ancestors 'self'",
        }
    )


# ---------------------------------------------------------------------
# Endpoints de Dispositivos y Packs de Obra (ZIP)
# ---------------------------------------------------------------------

@app.get("/api/dispositivos")
def listar_dispositivos(current_user: database.User = Depends(get_current_user)):
    """
    Lista todos los dispositivos únicos con conteo de manuales y videos disponibles según el rol.
    """
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


@app.get("/api/dispositivos/{dispositivo}/pack")
def descargar_pack_obra(dispositivo: str, current_user: database.User = Depends(get_current_user)):
    """
    Genera y descarga un archivo ZIP con toda la documentación técnica,
    manuales PDF y guía de enlaces de videos de YouTube para un dispositivo específico.
    """
    dispositivo_limpio = unquote(dispositivo).strip()
    db = database.SessionLocal()
    try:
        # Obtener manuales del dispositivo
        query_m = db.query(database.Manual).filter(
            func.lower(database.Manual.dispositivo) == func.lower(dispositivo_limpio)
        )
        if current_user.role == "comercial":
            query_m = query_m.filter(database.Manual.nivel_acceso == "publico")
        manuales = query_m.all()

        # Obtener videos del dispositivo
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

        # Crear archivo ZIP en memoria
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # 1. Añadir archivo README_LEEME.txt explicativo
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

            # 2. Añadir PDFs de manuales
            archivos_incluidos = 0
            nombres_usados = set()
            for m in manuales:
                ruta_pdf = MANUALES_DIR / m.nombre_archivo
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

            # 3. Añadir Guía de Videotutoriales de YouTube
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


@app.get("/api/miniatura/{manual_id}/{numero_pagina}")
def miniatura_pagina(manual_id: int, numero_pagina: int):
    # Sin proteccion auth agresiva para que los tag <img> del frontend carguen facil
    if not _PYPDFIUM_DISPONIBLE:
        raise HTTPException(status_code=501, detail="No disponible")

    manual = database.obtener_manual(manual_id)
    if manual is None:
        raise HTTPException(status_code=404)

    ruta = MANUALES_DIR / manual["nombre_archivo"]
    if not ruta.exists():
        raise HTTPException(status_code=404)

    try:
        imagen = _renderizar_pagina_como_imagen(ruta, numero_pagina, escala=0.6)
        buffer = io.BytesIO()
        imagen.save(buffer, format="PNG")
        return Response(content=buffer.getvalue(), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500)

# ---------------------------------------------------------------------
# Endpoints Gestión de Usuarios (Admin)
# ---------------------------------------------------------------------

from pydantic import BaseModel

class CrearUsuario(BaseModel):
    email: str
    password: str
    role: str

class CambiarRol(BaseModel):
    role: str

class CambiarPassword(BaseModel):
    password: str

@app.get("/api/usuarios")
def get_usuarios(current_user: database.User = Depends(require_admin)):
    return database.listar_usuarios()

@app.post("/api/usuarios")
def create_usuario(usuario: CrearUsuario, current_user: database.User = Depends(require_admin)):
    nuevo = database.crear_usuario(usuario.email, usuario.password, usuario.role)
    if not nuevo:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    return {"id": nuevo.id, "email": nuevo.email, "role": nuevo.role}

@app.delete("/api/usuarios/{user_id}")
def delete_usuario(user_id: int, current_user: database.User = Depends(require_admin)):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta")
    if not database.eliminar_usuario(user_id):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"ok": True}

@app.put("/api/usuarios/{user_id}/rol")
def update_user_role(user_id: int, datos: CambiarRol, current_user: database.User = Depends(require_admin)):
    if user_id == current_user.id and datos.role != "admin":
        raise HTTPException(status_code=400, detail="No puedes quitarte el rol de admin a ti mismo")
    if not database.cambiar_rol_usuario(user_id, datos.role):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"ok": True}

@app.put("/api/usuarios/me/password")
def change_my_password(datos: CambiarPassword, current_user: database.User = Depends(get_current_user)):
    if not database.cambiar_password_usuario(current_user.id, datos.password):
        raise HTTPException(status_code=400, detail="Error al cambiar contraseña")
    return {"ok": True}
