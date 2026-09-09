"""
Router de Búsqueda Unificada Híbrida, Filtros y Sugerencias.
"""

from fastapi import APIRouter, Depends

from .. import database
from ..auth import get_current_user

router = APIRouter(tags=["Búsqueda"])

@router.get("/api/buscar")
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

@router.get("/api/filtros")
def obtener_filtros(current_user: database.User = Depends(get_current_user)):
    dispositivos, categorias, etiquetas = database.listar_filtros()
    return {"dispositivos": dispositivos, "categorias": categorias, "etiquetas": etiquetas}

@router.get("/api/sugerencias")
def obtener_sugerencias(current_user: database.User = Depends(get_current_user)):
    manuales = database.listar_manuales()
    dispositivos, categorias, etiquetas = database.listar_filtros()
    # Filtro básico de nombres según rol para no revelar nombres confidenciales a comerciales
    nombres = [m["nombre_original"] for m in manuales if current_user.role != "comercial" or m["nivel_acceso"] == "publico"]
    return {"nombres": nombres, "dispositivos": dispositivos, "categorias": categorias, "etiquetas": etiquetas}
