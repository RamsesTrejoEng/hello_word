"""
auth.py — Contraseñas, tokens y control de acceso por roles.

Flujo de una sesión:
 1. El usuario manda usuario+contraseña a /auth/login.
 2. Se compara con el HASH guardado (la contraseña real nunca se guarda).
 3. Si coincide, se entrega un TOKEN (JWT) firmado con SECRET_KEY: es un
    "gafete temporal" que dice quién eres y tu rol.
 4. En cada petición el frontend manda el gafete en la cabecera
    "Authorization: Bearer <token>" y aquí se verifica la firma.
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.config import ALGORITHM, SECRET_KEY, TOKEN_MINUTOS
from backend.database import get_db
from backend.models import Usuario


def _bytes(password: str) -> bytes:
    # bcrypt solo lee los primeros 72 bytes de la contraseña.
    return password.encode("utf-8")[:72]


def hashear_password(password: str) -> str:
    """Convierte 'miClave123' en un hash irreversible tipo '$2b$12$...'."""
    return bcrypt.hashpw(_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verificar_password(password: str, hash_guardado: str) -> bool:
    try:
        return bcrypt.checkpw(_bytes(password), hash_guardado.encode("utf-8"))
    except ValueError:
        return False


def crear_token(usuario: Usuario) -> str:
    """JWT con: sub (id del usuario), rol y fecha de expiración."""
    carga = {
        "sub": str(usuario.id),
        "rol": usuario.rol,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTOS),
    }
    return jwt.encode(carga, SECRET_KEY, algorithm=ALGORITHM)


def nombre_visible(usuario: Usuario) -> str:
    if usuario.alumno:
        return usuario.alumno.nombre
    if usuario.profesor:
        return usuario.profesor.nombre
    return usuario.usuario


# HTTPBearer lee la cabecera Authorization. auto_error=False para dar nuestro
# propio mensaje en español.
_esquema = HTTPBearer(auto_error=False)


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_esquema),
    db: Session = Depends(get_db),
) -> Usuario:
    """Dependencia: devuelve el Usuario dueño del token o responde 401."""
    if credenciales is None:
        raise HTTPException(401, "No has iniciado sesión.")
    try:
        datos = jwt.decode(credenciales.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        usuario = db.get(Usuario, int(datos["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Sesión inválida o expirada.")
    if usuario is None or not usuario.activo:
        raise HTTPException(401, "Sesión inválida o expirada.")
    return usuario


def requiere_rol(*roles: str):
    """
    Fábrica de dependencias. Uso en una ruta:
        usuario = Depends(requiere_rol("profesor", "admin"))
    Si el rol del token no está en la lista -> 403 (prohibido).
    """
    def dependencia(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(403, "No tienes permiso para esta acción.")
        return usuario
    return dependencia
