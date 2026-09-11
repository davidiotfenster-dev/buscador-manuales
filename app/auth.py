"""
Módulo de Autenticación, Seguridad y RBAC para Buscador de Manuales.
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from . import database

logger = logging.getLogger("buscador_manuales.auth")

SECRET_KEY = os.environ.get("SECRET_KEY", "").strip()
if not SECRET_KEY:
    # Sin clave propia, los tokens se firmarían con un valor que está en el repositorio
    # y cualquiera podría emitirse uno de administrador. Es preferible no arrancar.
    raise RuntimeError(
        "SECRET_KEY no está definida. Genera una con "
        "`python -c \"import secrets; print(secrets.token_urlsafe(32))\"` "
        "y defínela en el entorno antes de arrancar."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("TOKEN_EXPIRE_MINUTES", "1440"))  # 24h por defecto

def _obtener_ip_cliente(request: Request) -> str:
    """
    Obtiene la IP del cliente contemplando proxies inversos (X-Forwarded-For).
    Toma la primera IP de la cadena si existe o request.client.host como fallback.
    """
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# Rate limiting simple en memoria para /api/token
_login_intentos: dict = {}  # {ip: [(timestamp, ...)]}
_LOGIN_MAX_INTENTOS = 5
_LOGIN_VENTANA_SEGUNDOS = 900  # 15 minutos

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token", auto_error=False)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": int(expire.timestamp())})
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
    try:
        user = db.query(database.User).filter(database.User.email == email).first()
    finally:
        db.close()
    
    if user is None:
        raise credentials_exception
    return user

def get_current_user_optional(request: Request, token: Optional[str] = Depends(oauth2_scheme)) -> Optional[database.User]:
    """Obtiene el usuario actual si el token es válido, o None si no hay token o es inválido."""
    if not token:
        token = request.query_params.get("token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            return None
    except JWTError:
        return None

    db = database.SessionLocal()
    try:
        user = db.query(database.User).filter(database.User.email == email).first()
    finally:
        db.close()
    return user

def require_admin(current_user: database.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
    return current_user

def require_tecnico_or_admin(current_user: database.User = Depends(get_current_user)):
    if current_user.role not in ("admin", "tecnico"):
        raise HTTPException(status_code=403, detail="Acceso restringido a personal técnico o administrador")
    return current_user

def _check_rbac(nivel_acceso: str, role: str) -> bool:
    """Verifica si un rol tiene acceso a un recurso según su nivel_acceso."""
    if role in ("admin", "tecnico"):
        return True
    if nivel_acceso == "publico":
        return True
    return False

def _check_rate_limit(ip: str) -> bool:
    """Devuelve True si el IP está dentro del límite de intentos."""
    if not ip or ip in ("127.0.0.1", "localhost", "::1", "unknown") or ip.startswith("172.") or ip.startswith("192.168.") or ip.startswith("10."):
        return True
    ahora = datetime.now(timezone.utc)
    if ip in _login_intentos:
        _login_intentos[ip] = [t for t in _login_intentos[ip] if (ahora - t).total_seconds() < _LOGIN_VENTANA_SEGUNDOS]
        if len(_login_intentos[ip]) >= _LOGIN_MAX_INTENTOS:
            return False
    return True

def _registrar_intento_fallido(ip: str):
    ahora = datetime.now(timezone.utc)
    if ip not in _login_intentos:
        _login_intentos[ip] = []
    _login_intentos[ip].append(ahora)

def _reset_rate_limit(ip: str):
    """Limpia los intentos fallidos al tener éxito o resetear."""
    _login_intentos.pop(ip, None)

