"""
seed.py — Datos de ejemplo para probar todo.   Uso:  python -m backend.seed

Crea: 1 admin, 2 profesores, 5 alumnos, 3 periodos (2 pasados + 1 activo),
materias (algunas ya NO activas para ver el historial) y calificaciones.
BORRA estos usuarios de prueba antes de usar el sistema con datos reales.
"""
import random
from datetime import date

from sqlalchemy import select

from backend.auth import hashear_password
from backend.database import Base, SessionLocal, engine
from backend.models import (Alumno, Calificacion, Evaluacion, Inscripcion, Materia,
                            MateriaPeriodo, Periodo, Profesor, Usuario)


def cargar_datos_demo(db) -> None:
    rng = random.Random(7)  # semilla fija: siempre salen las mismas notas

    # --- Usuarios: admin y profesores ---
    db.add(Usuario(usuario="admin", password_hash=hashear_password("admin12345"), rol="admin"))
    garcia, mendez = Profesor(nombre="Laura García"), Profesor(nombre="Carlos Méndez")
    db.add_all([garcia, mendez])
    db.add(Usuario(usuario="prof.garcia", password_hash=hashear_password("profesor123"), rol="profesor", profesor=garcia))
    db.add(Usuario(usuario="prof.mendez", password_hash=hashear_password("profesor123"), rol="profesor", profesor=mendez))

    # --- Alumnos: usuario y contraseña inicial = matrícula ---
    nombres = ["Juan Pérez", "Ana López", "Luis Hernández", "María Torres", "Pedro Ramírez"]
    alumnos = []
    for i, nombre in enumerate(nombres):
        matricula = f"2026010{i + 1}"
        a = Alumno(matricula=matricula, nombre=nombre, generacion="2026")
        db.add(a)
        db.add(Usuario(usuario=matricula, password_hash=hashear_password(matricula), rol="alumno", alumno=a))
        alumnos.append(a)

    # --- Periodos: 2 pasados (historial) y 1 activo ---
    p1 = Periodo(nombre="2025-B", fecha_inicio=date(2025, 8, 18), fecha_fin=date(2025, 12, 12), activo=False)
    p2 = Periodo(nombre="2026-A", fecha_inicio=date(2026, 2, 2), fecha_fin=date(2026, 6, 12), activo=False)
    p3 = Periodo(nombre="2026-B", fecha_inicio=date(2026, 8, 17), fecha_fin=date(2026, 12, 11), activo=True)
    db.add_all([p1, p2, p3])

    # --- Catálogo de materias (Ética y Geografía ya no se imparten) ---
    def m(nombre, area, activa=True):
        materia = Materia(nombre=nombre, area=area, activa=activa)
        db.add(materia)
        return materia

    mate, bio, prog, hist = m("Matemáticas", "Ciencias"), m("Biología", "Ciencias"), m("Programación", "Tecnología"), m("Historia", "Humanidades")
    fis, qui = m("Física", "Ciencias", False), m("Química", "Ciencias", False)
    etica, geo = m("Ética", "Humanidades", False), m("Geografía", "Humanidades", False)

    # --- Qué se impartió en cada periodo: (materia, periodo, profesor, parciales capturados) ---
    cursos = [
        (fis, p1, mendez, 3), (qui, p1, mendez, 3),
        (etica, p2, garcia, 3), (geo, p2, mendez, 3),
        (mate, p3, garcia, 3), (bio, p3, mendez, 2), (prog, p3, garcia, 2), (hist, p3, mendez, 2),
    ]
    for materia, periodo, profesor, n_parciales in cursos:
        mp = MateriaPeriodo(materia=materia, periodo=periodo, profesor=profesor)
        db.add(mp)
        evaluaciones = []
        for n in range(1, n_parciales + 1):
            ev = Evaluacion(materia_periodo=mp, numero=n, nombre_parcial=f"Parcial {n}")
            db.add(ev)
            evaluaciones.append(ev)
        for alumno in alumnos:
            insc = Inscripcion(alumno=alumno, materia_periodo=mp)
            db.add(insc)
            for ev in evaluaciones:
                db.add(Calificacion(inscripcion=insc, evaluacion=ev, calificacion=round(rng.uniform(5.0, 10.0), 1)))
    db.commit()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(Usuario).where(Usuario.usuario == "admin")):
            print("Ya hay datos de ejemplo; no se hizo nada.")
            return
        cargar_datos_demo(db)
    print("Datos de ejemplo cargados.")
    print("  admin / admin12345    profesor: prof.garcia / profesor123    alumno: 20260101 / 20260101")


if __name__ == "__main__":
    main()
