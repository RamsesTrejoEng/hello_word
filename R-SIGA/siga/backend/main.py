"""
main.py — Punto de entrada. Arranca con:  uvicorn backend.main:app --reload

Hace tres cosas:
 1. Crea las tablas si no existen.
 2. Registra las rutas de la API (auth, alumno, profesor, admin).
 3. Sirve el frontend (carpeta /frontend) en http://localhost:8000
    -> así frontend y API comparten dirección y no hay problemas de CORS.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend import models  # noqa: F401  (importarlo registra las tablas en Base)
from backend.config import CORS_ORIGINS
from backend.database import Base, engine
from backend.routers import admin, alumno, auth, profesor


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    Base.metadata.create_all(bind=engine)  # crea tablas faltantes al arrancar
    yield


app = FastAPI(title="SIGA", description="Sistema Integral de Gestión Académica", version="1.0", lifespan=ciclo_de_vida)

# CORS: solo hace falta si abres el frontend desde OTRO origen (ej. Live Server).
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router)
app.include_router(alumno.router)
app.include_router(profesor.router)
app.include_router(admin.router)


@app.get("/salud", tags=["Sistema"])
def salud():
    """Para comprobar que el servidor está vivo."""
    return {"estado": "ok"}


# IMPORTANTE: esto va AL FINAL; "/" atrapa todo lo que no sea una ruta de la API.
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
