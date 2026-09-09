"""
Router de Gestión y Administración de Cuentas de Usuario (Solo Admin).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import database
from ..auth import require_admin

router = APIRouter(tags=["Usuarios y Roles"])

class CrearUsuario(BaseModel):
    email: str
    password: str
    role: str

class CambiarRol(BaseModel):
    role: str

@router.get("/api/usuarios")
def get_usuarios(current_user: database.User = Depends(require_admin)):
    return database.listar_usuarios()

@router.post("/api/usuarios")
def create_usuario(usuario: CrearUsuario, current_user: database.User = Depends(require_admin)):
    nuevo = database.crear_usuario(usuario.email, usuario.password, usuario.role)
    if not nuevo:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    return {"id": nuevo.id, "email": nuevo.email, "role": nuevo.role}

@router.delete("/api/usuarios/{user_id}")
def delete_usuario(user_id: int, current_user: database.User = Depends(require_admin)):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta")
    if not database.eliminar_usuario(user_id):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"ok": True}

@router.put("/api/usuarios/{user_id}/rol")
def update_user_role(user_id: int, datos: CambiarRol, current_user: database.User = Depends(require_admin)):
    if datos.role not in database.ROLES_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Rol inválido. Roles válidos: {database.ROLES_VALIDOS}")
    if user_id == current_user.id and datos.role != "admin":
        raise HTTPException(status_code=400, detail="No puedes quitarte el rol de admin a ti mismo")
    if not database.cambiar_rol_usuario(user_id, datos.role):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"ok": True}
