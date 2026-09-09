"""
Buscador de Manuales - Aplicación Principal FastAPI.
Arquitectura modularizada con enrutadores desacoplados y dependencias RBAC.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import database
from .auth import (
    create_access_token,
    _obtener_ip_cliente,
)
from .routers import auth, buscar, manuales, sat, usuarios, videos
from .routers.manuales import (
    DEFAULT_MANUALES_DIR as MANUALES_DIR,
    DEFAULT_CACHE_MINIATURAS_DIR as CACHE_MINIATURAS_DIR,
    _invalidar_cache_miniaturas,
    _OCR_DISPONIBLE,
    _PYPDFIUM_DISPONIBLE,
    _renderizar_pagina_como_imagen,
)
from .routers.videos import _loop_sincronizacion_programada

logger = logging.getLogger("buscador_manuales")

BASE_DIR = Path(__file__).resolve().parent.parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    if not _OCR_DISPONIBLE:
        logger.warning("OCR no disponible. Los PDF escaneados sin texto no se indexarán.")
    try:
        from sync_manuales import sincronizar_manuales
        sincronizar_manuales(dry_run=False, force=False)
    except Exception as e:
        logger.warning(f"Sincronización inicial de manuales no completada en startup: {e}")

    cron_task = asyncio.create_task(_loop_sincronizacion_programada())
    try:
        yield
    finally:
        cron_task.cancel()


app = FastAPI(title="Buscador de Manuales", lifespan=lifespan)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    if "server" in response.headers:
        del response.headers["server"]
    return response

app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """
    Manejador personalizado para devolver páginas HTML amigables en 401, 403 y 404
    cuando la petición proviene de un navegador o un iframe (Accept: text/html o ruta de manuales),
    y mantener respuesta JSON estándar cuando la petición es de una API o suite de tests.
    """
    accept = request.headers.get("accept", "")
    es_html = "text/html" in accept

    if es_html and exc.status_code in (401, 403, 404):
        titulos = {
            401: "Autenticación Requerida",
            403: "Acceso Restringido",
            404: "Documento No Encontrado"
        }
        nombre_archivo = ""
        if request.url.path.startswith("/manuales/"):
            try:
                nombre_archivo = unquote(Path(request.url.path).name)
            except Exception:
                nombre_archivo = ""

        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "status_code": exc.status_code,
                "titulo": titulos.get(exc.status_code, "Aviso de Seguridad"),
                "mensaje": exc.detail,
                "nombre_archivo": nombre_archivo,
                "nivel_acceso": "tecnico" if exc.status_code == 403 else None
            },
            status_code=exc.status_code
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers
    )


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"ocr_disponible": _OCR_DISPONIBLE},
    )


# ---------------------------------------------------------------------
# Registro de Enrutadores Modulares
# ---------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(buscar.router)
app.include_router(manuales.router)
app.include_router(videos.router)
app.include_router(sat.router)
app.include_router(usuarios.router)
