"""
Router para Tutoriales de YouTube, Extracción Multimedia y Sincronizador Automático.
"""

import asyncio
import json
import logging
import os
import re
import urllib.request
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import database
from ..auth import get_current_user, require_admin

logger = logging.getLogger("buscador_manuales.videos")

_YOUTUBE_DOMINIOS_PERMITIDOS = (
    "https://www.youtube.com/",
    "https://youtube.com/",
)

def _validar_url_youtube(url: str) -> str:
    """Valida que la URL pertenece a YouTube para prevenir SSRF."""
    url = url.strip()
    if not any(url.startswith(d) for d in _YOUTUBE_DOMINIOS_PERMITIDOS):
        raise ValueError("URL no permitida. Solo se aceptan URLs de youtube.com")
    return url

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

_ESTADO_SYNC_CRON = {
    "activo": True,
    "intervalo_horas": int(os.environ.get("YOUTUBE_SYNC_INTERVAL_HOURS", "24")),
    "ultima_ejecucion": None,
    "proxima_ejecucion": None,
    "ultimo_resultado": None
}

def _ejecutar_sincronizacion_canal(canal_url: str = "https://www.youtube.com/@MySmartWindow/videos") -> dict:
    canal_url = canal_url.strip()
    try:
        canal_url = _validar_url_youtube(canal_url)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    
    if not canal_url.endswith("/videos"):
        canal_url = canal_url.rstrip("/") + "/videos"
        
    vids = _extraer_videos_canal(canal_url)
    if not vids:
        return {"ok": False, "error": "No se encontraron videos en el canal"}
    
    procesados = 0
    errores = []
    
    for vid in vids:
        try:
            # Si el video ya está registrado en la base de datos, evitar peticiones externas redundantes
            v_existente = database.obtener_video_por_youtube_id(vid)
            if v_existente and v_existente.get("titulo"):
                procesados += 1
                continue

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
            err_msg = str(e)
            errores.append(f"Error en video {vid}: {err_msg}")
            if "429" in err_msg or "Too Many Requests" in err_msg:
                logger.warning("Límite de peticiones de YouTube (429) alcanzado. Deteniendo ciclo para evitar bloqueos.")
                break
            
    return {
        "ok": True, 
        "sincronizados": procesados, 
        "errores": errores,
        "timestamp": datetime.now().isoformat()
    }

async def _loop_sincronizacion_programada():
    """Tarea en segundo plano que sincroniza periódicamente los tutoriales de YouTube (tras 5 min de arranque)."""
    await asyncio.sleep(300)
    while True:
        try:
            logger.info("Iniciando tarea programada: Sincronización periódica de YouTube @MySmartWindow...")
            _ESTADO_SYNC_CRON["ultima_ejecucion"] = datetime.now().isoformat()
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

router = APIRouter(tags=["Videos YouTube"])

@router.get("/api/videos/sync-status")
def obtener_estado_sincronizacion(current_user: database.User = Depends(require_admin)):
    return _ESTADO_SYNC_CRON

@router.post("/api/videos/sincronizar")
def sincronizar_canal_youtube(datos: SincronizarCanalDTO = None, current_user: database.User = Depends(require_admin)):
    canal_url = (datos.canal_url if datos and datos.canal_url else "https://www.youtube.com/@MySmartWindow/videos").strip()
    try:
        canal_url = _validar_url_youtube(canal_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    resultado = _ejecutar_sincronizacion_canal(canal_url)
    if not resultado.get("ok"):
        raise HTTPException(status_code=400, detail=resultado.get("error", "No se pudieron sincronizar los videos"))
    
    _ESTADO_SYNC_CRON["ultima_ejecucion"] = datetime.now().isoformat()
    _ESTADO_SYNC_CRON["ultimo_resultado"] = resultado
    return resultado

@router.post("/api/videos")
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

@router.get("/api/videos")
def listar_videos(current_user: database.User = Depends(get_current_user)):
    videos = database.listar_videos(role=current_user.role)
    return {"videos": videos}

@router.delete("/api/videos/{video_db_id}")
def eliminar_video(video_db_id: int, current_user: database.User = Depends(require_admin)):
    exito = database.eliminar_video(video_db_id)
    if not exito:
        raise HTTPException(status_code=404, detail="Video no encontrado")
    return {"ok": True}

@router.put("/api/videos/{video_db_id}")
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
