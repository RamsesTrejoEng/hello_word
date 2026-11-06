"""
importar_alumnos.py — Da de alta MUCHOS alumnos desde un Excel (ej. los ~350 de tu escuela).

Excel con columnas:  MATRICULA | NOMBRE | GENERACION (opcional)
Uso (desde la carpeta siga/):   python -m backend.importar_alumnos alumnos.xlsx

Cada alumno queda con usuario = matrícula y contraseña inicial = matrícula.
Los que ya existen se omiten (puedes volver a correrlo sin miedo).
Tarda un poco: cada contraseña se hashea con bcrypt a propósito (es lento para
que adivinarlas por fuerza bruta sea inviable). ~350 alumnos = 1-2 minutos.
"""
import sys

from openpyxl import load_workbook
from sqlalchemy import select

from backend.auth import hashear_password
from backend.database import Base, SessionLocal, engine
from backend.excel import _a_matricula, _normalizar
from backend.models import Alumno, Usuario


def importar(ruta: str) -> None:
    libro = load_workbook(ruta, read_only=True, data_only=True)
    filas = libro.active.iter_rows(values_only=True)
    encabezado = next(filas, None) or []
    pos = {_normalizar(n): i for i, n in enumerate(encabezado) if n is not None}
    for columna in ("MATRICULA", "NOMBRE"):
        if columna not in pos:
            sys.exit(f"Falta la columna {columna} en el Excel.")

    def valor(fila, nombre):
        i = pos.get(nombre)
        return fila[i] if i is not None and i < len(fila) else None

    Base.metadata.create_all(bind=engine)
    creados = omitidos = 0
    with SessionLocal() as db:
        existentes = set(db.scalars(select(Alumno.matricula)))
        for fila in filas:
            matricula = _a_matricula(valor(fila, "MATRICULA"))
            nombre = str(valor(fila, "NOMBRE") or "").strip()
            if not matricula or not nombre:
                continue
            if matricula in existentes:
                omitidos += 1
                continue
            generacion = valor(fila, "GENERACION")
            alumno = Alumno(matricula=matricula, nombre=nombre, generacion=str(generacion).strip() if generacion else None)
            db.add(alumno)
            db.add(Usuario(usuario=matricula, rol="alumno", alumno=alumno, password_hash=hashear_password(matricula)))
            existentes.add(matricula)
            creados += 1
        db.commit()
    print(f"Alumnos creados: {creados}. Omitidos (ya existían): {omitidos}.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m backend.importar_alumnos alumnos.xlsx")
    importar(sys.argv[1])
