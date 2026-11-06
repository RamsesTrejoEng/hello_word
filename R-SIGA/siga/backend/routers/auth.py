"""routers/auth.py — Login y cambio de contraseña."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth import (crear_token, hashear_password, nombre_visible,
                          usuario_actual, verificar_password)
from backend.database import get_db
from backend.models import Usuario
from backend.schemas import CambioPassword, LoginIn, TokenOut

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenOut)
def login(datos: LoginIn, db: Session = Depends(get_db)):
    usuario = db.scalar(select(Usuario).where(Usuario.usuario == datos.usuario.strip()))
    # Mismo mensaje si el usuario no existe o la contraseña es incorrecta:
    # así nadie puede averiguar qué matrículas existen.
    if usuario is None or not usuario.activo or not verificar_password(datos.password, usuario.password_hash):
        raise HTTPException(401, "Usuario o contraseña incorrectos.")
    return TokenOut(access_token=crear_token(usuario), rol=usuario.rol, nombre=nombre_visible(usuario))


@router.get("/yo")
def quien_soy(usuario: Usuario = Depends(usuario_actual)):
    return {"usuario": usuario.usuario, "rol": usuario.rol, "nombre": nombre_visible(usuario)}


@router.post("/cambiar-password")
def cambiar_password(datos: CambioPassword, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    if not verificar_password(datos.actual, usuario.password_hash):
        raise HTTPException(400, "La contraseña actual es incorrecta.")
    usuario.password_hash = hashear_password(datos.nueva)
    db.commit()
    return {"mensaje": "Contraseña actualizada."}
