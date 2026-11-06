"""
Pruebas de la API completa con una base SQLite temporal.
Ejecutar desde la carpeta siga/ :   pytest -v
Necesitan haber instalado requirements.txt (fastapi, httpx, python-multipart...).
"""
import os
from io import BytesIO

# IMPORTANTE: definir la base de datos de pruebas ANTES de importar la app.
os.environ["DATABASE_URL"] = "sqlite:///./test_siga.db"

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from backend.database import Base, SessionLocal, engine
from backend.main import app
from backend.seed import cargar_datos_demo

TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture(scope="module")
def cliente():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        cargar_datos_demo(db)
    yield TestClient(app)
    engine.dispose()
    if os.path.exists("test_siga.db"):
        os.remove("test_siga.db")


def entrar(cliente, usuario, password):
    r = cliente.post("/auth/login", json={"usuario": usuario, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def hacer_excel(filas):
    libro = Workbook()
    hoja = libro.active
    hoja.append(["MATRICULA", "NOMBRE", "PARCIAL", "CALIFICACION"])
    for f in filas:
        hoja.append(list(f))
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


def test_login_correcto_e_incorrecto(cliente):
    assert cliente.post("/auth/login", json={"usuario": "20260101", "password": "mala"}).status_code == 401
    assert cliente.post("/auth/login", json={"usuario": "20260101", "password": "20260101"}).status_code == 200


def test_sin_token_no_pasa(cliente):
    assert cliente.get("/alumno/calificaciones").status_code == 401


def test_alumno_ve_solo_lo_suyo_con_historial(cliente):
    r = cliente.get("/alumno/calificaciones", headers=entrar(cliente, "20260101", "20260101"))
    datos = r.json()
    assert r.status_code == 200
    assert len(datos["calificaciones"]) == 4           # 4 materias del periodo activo
    assert [h["periodo"] for h in datos["historial"]] == ["2026-A", "2025-B"]


def test_alumno_no_entra_a_rutas_de_profesor_ni_admin(cliente):
    h = entrar(cliente, "20260101", "20260101")
    assert cliente.get("/profesor/materias", headers=h).status_code == 403
    assert cliente.get("/admin/alumnos", headers=h).status_code == 403


def test_profesor_no_toca_grupos_ajenos(cliente):
    garcia = entrar(cliente, "prof.garcia", "profesor123")
    mendez = entrar(cliente, "prof.mendez", "profesor123")
    id_garcia = cliente.get("/profesor/materias", headers=garcia).json()[0]["id"]
    assert cliente.get(f"/profesor/materias/{id_garcia}/calificaciones", headers=garcia).status_code == 200
    assert cliente.get(f"/profesor/materias/{id_garcia}/calificaciones", headers=mendez).status_code == 403


def test_subir_excel_valido_y_rechazar_invalido(cliente):
    h = entrar(cliente, "prof.garcia", "profesor123")
    grupo = cliente.get("/profesor/materias", headers=h).json()[0]["id"]

    bueno = hacer_excel([("20260101", "Juan", 1, 10), ("20260102", "Ana", 1, 9.5)])
    r = cliente.post(f"/profesor/materias/{grupo}/excel", headers=h, files={"archivo": ("n.xlsx", bueno, TIPO_XLSX)})
    assert r.status_code == 200, r.text

    malo = hacer_excel([("20260101", "Juan", 1, "ocho"), ("99999999", "Nadie", 1, 8)])
    r = cliente.post(f"/profesor/materias/{grupo}/excel", headers=h, files={"archivo": ("n.xlsx", malo, TIPO_XLSX)})
    assert r.status_code == 422
    assert len(r.json()["detail"]["errores"]) == 2      # calificación inválida + matrícula inexistente


def test_admin_crea_alumno_y_este_puede_entrar(cliente):
    h = entrar(cliente, "admin", "admin12345")
    r = cliente.post("/admin/alumnos", headers=h, json={"matricula": "20269999", "nombre": "Nuevo Alumno"})
    assert r.status_code == 200
    assert cliente.post("/admin/alumnos", headers=h, json={"matricula": "20269999", "nombre": "Repetido"}).status_code == 409
    entrar(cliente, "20269999", "20269999")
