"""
Router de Autenticación, Sesión y Perfil de Usuario.
"""

from datetime import timedelta
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from .. import database
from ..auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    _check_rate_limit,
    _obtener_ip_cliente,
    _registrar_intento_fallido,
)

router = APIRouter(tags=["Autenticación"])

class CambiarPassword(BaseModel):
    password: str

@router.post("/api/token")
def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    # Rate limiting por IP (contemplando proxies inversos / X-Forwarded-For)
    client_ip = _obtener_ip_cliente(request)
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Demasiados intentos de login. Inténtalo de nuevo en 15 minutos."
        )
    
    username_clean = form_data.username.strip()
    db = database.SessionLocal()
    try:
        if username_clean.lower() == "admin":
            user = db.query(database.User).filter(
                (database.User.email.ilike(username_clean)) | (database.User.email == "admin@empresa.com")
            ).first()
        else:
            user = db.query(database.User).filter(database.User.email.ilike(username_clean)).first()
    finally:
        db.close()
    
    if not user or not bcrypt.checkpw(form_data.password.encode('utf-8'), user.password_hash.encode('utf-8')):
        _registrar_intento_fallido(client_ip)
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role, "email": user.email}

@router.get("/api/me")
def get_me(current_user: database.User = Depends(get_current_user)):
    return {"email": current_user.email, "role": current_user.role, "is_first_login": current_user.is_first_login}

@router.put("/api/usuarios/me/password")
def change_my_password(datos: CambiarPassword, current_user: database.User = Depends(get_current_user)):
    if not database.cambiar_password_usuario(current_user.id, datos.password):
        raise HTTPException(status_code=400, detail="Error al cambiar contraseña")
    return {"ok": True}
