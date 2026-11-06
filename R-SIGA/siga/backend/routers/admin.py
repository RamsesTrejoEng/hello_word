"""
routers/admin.py — Alta de datos de la escuela (solo rol admin).

Se usan desde la documentación interactiva http://localhost:8000/docs
(botón "Authorize" para pegar tu token) hasta que exista un panel visual.
"""
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import hashear_password, requiere_rol
from backend.database import get_db
from backend.models import (Alumno, Inscripcion, Materia, MateriaPeriodo,
                            Periodo, Profesor, Usuario)
from backend.schemas import (AlumnoCreate, InscripcionMasiva, MateriaCreate,
                             MateriaPeriodoCreate, MateriaUpdate, PeriodoCreate,
                             ProfesorCreate, ResetPassword)

# dependencies=[...] aplica el candado "solo admin" a TODAS las rutas del archivo.
router = APIRouter(prefix="/admin", tags=["Administración"], dependencies=[Depends(requiere_rol("admin"))])


@contextmanager
def transaccion(db: Session):
    """Guarda al salir del bloque; si hay duplicado/dato inválido responde 409 y deshace todo."""
    try:
        yield
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ya existe un registro igual, o falta un dato relacionado (alumno, materia, periodo...).")


# ---------- Periodos ----------
@router.post("/periodos")
def crear_periodo(datos: PeriodoCreate, db: Session = Depends(get_db)):
    with transaccion(db):
        if datos.activo:  # solo un periodo activo a la vez
            db.execute(update(Periodo).values(activo=False))
        periodo = Periodo(**datos.model_dump())
        db.add(periodo)
    return {"id": periodo.id, "nombre": periodo.nombre, "activo": periodo.activo}


@router.get("/periodos")
def listar_periodos(db: Session = Depends(get_db)):
    return [{"id": p.id, "nombre": p.nombre, "activo": p.activo} for p in db.scalars(select(Periodo).order_by(Periodo.id))]


@router.post("/periodos/{periodo_id}/activar")
def activar_periodo(periodo_id: int, db: Session = Depends(get_db)):
    """Cambia de semestre: el anterior pasa solo al historial (activo=False)."""
    if db.get(Periodo, periodo_id) is None:
        raise HTTPException(404, "Periodo no encontrado.")
    db.execute(update(Periodo).values(activo=False))
    db.execute(update(Periodo).where(Periodo.id == periodo_id).values(activo=True))
    db.commit()
    return {"mensaje": "Periodo activado. Los anteriores quedan como historial."}


# ---------- Materias ----------
@router.post("/materias")
def crear_materia(datos: MateriaCreate, db: Session = Depends(get_db)):
    with transaccion(db):
        materia = Materia(**datos.model_dump())
        db.add(materia)
    return {"id": materia.id, "nombre": materia.nombre}


@router.get("/materias")
def listar_materias(db: Session = Depends(get_db)):
    return [{"id": m.id, "nombre": m.nombre, "area": m.area, "activa": m.activa}
            for m in db.scalars(select(Materia).order_by(Materia.nombre))]


@router.patch("/materias/{materia_id}")
def marcar_materia(materia_id: int, datos: MateriaUpdate, db: Session = Depends(get_db)):
    """activa=false -> la materia ya no se imparte; su historial se CONSERVA."""
    materia = db.get(Materia, materia_id)
    if materia is None:
        raise HTTPException(404, "Materia no encontrada.")
    materia.activa = datos.activa
    db.commit()
    return {"id": materia.id, "nombre": materia.nombre, "activa": materia.activa}


# ---------- Profesores y alumnos (cada uno con su usuario de login) ----------
@router.post("/profesores")
def crear_profesor(datos: ProfesorCreate, db: Session = Depends(get_db)):
    with transaccion(db):
        profesor = Profesor(nombre=datos.nombre)
        db.add(profesor)
        db.flush()  # para conocer profesor.id antes de crear su usuario
        db.add(Usuario(usuario=datos.usuario, password_hash=hashear_password(datos.password),
                       rol="profesor", profesor_id=profesor.id))
    return {"id": profesor.id, "usuario": datos.usuario}


@router.get("/profesores")
def listar_profesores(db: Session = Depends(get_db)):
    return [{"id": p.id, "nombre": p.nombre, "activo": p.activo} for p in db.scalars(select(Profesor))]


@router.post("/alumnos")
def crear_alumno(datos: AlumnoCreate, db: Session = Depends(get_db)):
    """El usuario de login es la matrícula; la contraseña inicial, la matrícula si no se indica otra."""
    with transaccion(db):
        alumno = Alumno(matricula=datos.matricula, nombre=datos.nombre, generacion=datos.generacion)
        db.add(alumno)
        db.flush()
        db.add(Usuario(usuario=datos.matricula, rol="alumno", alumno_id=alumno.id,
                       password_hash=hashear_password(datos.password or datos.matricula)))
    return {"id": alumno.id, "matricula": datos.matricula}


@router.get("/alumnos")
def listar_alumnos(buscar: str | None = None, db: Session = Depends(get_db)):
    consulta = select(Alumno).order_by(Alumno.nombre).limit(200)
    if buscar:
        patron = f"%{buscar}%"
        consulta = consulta.where(Alumno.nombre.ilike(patron) | Alumno.matricula.ilike(patron))
    return [{"id": a.id, "matricula": a.matricula, "nombre": a.nombre, "activo": a.activo} for a in db.scalars(consulta)]


# ---------- Qué se imparte cada periodo e inscripciones ----------
@router.post("/materias-periodo")
def abrir_grupo(datos: MateriaPeriodoCreate, db: Session = Depends(get_db)):
    """Declara 'esta materia se imparte este periodo con este profesor'."""
    with transaccion(db):
        grupo = MateriaPeriodo(**datos.model_dump())
        db.add(grupo)
    return {"id": grupo.id}


@router.get("/materias-periodo")
def listar_grupos(periodo_id: int | None = None, db: Session = Depends(get_db)):
    consulta = select(MateriaPeriodo)
    if periodo_id:
        consulta = consulta.where(MateriaPeriodo.periodo_id == periodo_id)
    return [{"id": g.id, "materia": g.materia.nombre, "periodo": g.periodo.nombre, "profesor": g.profesor.nombre,
             "alumnos": len(g.inscripciones)} for g in db.scalars(consulta)]


@router.post("/inscripciones")
def inscribir(datos: InscripcionMasiva, db: Session = Depends(get_db)):
    """Inscribe una lista de matrículas a un grupo. Ignora las ya inscritas."""
    grupo = db.get(MateriaPeriodo, datos.materia_periodo_id)
    if grupo is None:
        raise HTTPException(404, "Ese grupo no existe.")
    alumnos = {a.matricula: a for a in db.scalars(select(Alumno).where(Alumno.matricula.in_(datos.matriculas)))}
    ya_inscritos = {i.alumno_id for i in grupo.inscripciones}
    nuevas = 0
    with transaccion(db):
        for matricula in dict.fromkeys(datos.matriculas):  # quita repetidas conservando el orden
            alumno = alumnos.get(matricula)
            if alumno and alumno.id not in ya_inscritos:
                db.add(Inscripcion(alumno_id=alumno.id, materia_periodo_id=grupo.id))
                nuevas += 1
    return {"inscritos_nuevos": nuevas, "matriculas_no_encontradas": [m for m in dict.fromkeys(datos.matriculas) if m not in alumnos]}


# ---------- Recuperar acceso ----------
@router.post("/usuarios/reset-password")
def resetear_password(datos: ResetPassword, db: Session = Depends(get_db)):
    """Sin correo institucional no hay 'olvidé mi contraseña': el admin la restablece."""
    usuario = db.scalar(select(Usuario).where(Usuario.usuario == datos.usuario))
    if usuario is None:
        raise HTTPException(404, "Usuario no encontrado.")
    usuario.password_hash = hashear_password(datos.nueva)
    db.commit()
    return {"mensaje": f"Contraseña de {datos.usuario} restablecida."}
