"""routers/profesor.py — Materias del profesor, tabla del grupo y carga de Excel."""
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth import requiere_rol
from backend.config import MAX_PARCIALES
from backend.database import get_db
from backend.excel import generar_plantilla, leer_calificaciones
from backend.models import Calificacion, Evaluacion, MateriaPeriodo, Periodo, Usuario
from backend.services import parciales_de, promedio

router = APIRouter(prefix="/profesor", tags=["Profesor"])

# Los administradores también pueden usar estas rutas (ven todos los grupos).
puede_calificar = requiere_rol("profesor", "admin")

MAX_BYTES = 5 * 1024 * 1024  # tamaño máximo del Excel: 5 MB
TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _curso_permitido(db: Session, materia_periodo_id: int, usuario: Usuario) -> MateriaPeriodo:
    """
    Devuelve el grupo solicitado SOLO si el profesor es su titular.
    Esta comprobación evita que un profesor edite grupos de otro.
    """
    mp = db.get(MateriaPeriodo, materia_periodo_id)
    if mp is None:
        raise HTTPException(404, "Ese grupo no existe.")
    if usuario.rol == "profesor" and mp.profesor_id != usuario.profesor_id:
        raise HTTPException(403, "Ese grupo no es tuyo.")
    return mp


@router.get("/materias")
def mis_materias(usuario: Usuario = Depends(puede_calificar), db: Session = Depends(get_db)):
    """Grupos del periodo activo (los del profesor; todos si es admin)."""
    consulta = select(MateriaPeriodo).join(Periodo).where(Periodo.activo.is_(True))
    if usuario.rol == "profesor":
        consulta = consulta.where(MateriaPeriodo.profesor_id == usuario.profesor_id)
    return [
        {
            "id": mp.id,
            "materia": mp.materia.nombre,
            "periodo": mp.periodo.nombre,
            "profesor": mp.profesor.nombre,
            "alumnos": len(mp.inscripciones),
        }
        for mp in db.scalars(consulta).all()
    ]


@router.get("/materias/{materia_periodo_id}/calificaciones")
def calificaciones_del_grupo(
    materia_periodo_id: int,
    usuario: Usuario = Depends(puede_calificar),
    db: Session = Depends(get_db),
):
    mp = _curso_permitido(db, materia_periodo_id, usuario)
    alumnos = []
    for insc in sorted(mp.inscripciones, key=lambda i: i.alumno.nombre):
        parciales = parciales_de(insc)
        alumnos.append({
            "matricula": insc.alumno.matricula,
            "nombre": insc.alumno.nombre,
            "parciales": parciales,
            "promedio": promedio(parciales),
        })
    return {"curso": f"{mp.materia.nombre} ({mp.periodo.nombre})", "alumnos": alumnos}


@router.get("/plantilla")
def descargar_plantilla(_: Usuario = Depends(puede_calificar)):
    """Entrega el Excel vacío con el formato oficial."""
    return Response(
        content=generar_plantilla(),
        media_type=TIPO_XLSX,
        headers={"Content-Disposition": 'attachment; filename="plantilla_calificaciones.xlsx"'},
    )


@router.post("/materias/{materia_periodo_id}/excel")
def subir_excel(
    materia_periodo_id: int,
    archivo: UploadFile = File(...),
    usuario: Usuario = Depends(puede_calificar),
    db: Session = Depends(get_db),
):
    """
    Pipeline: archivo -> validar formato -> validar contra la base de datos
    -> guardar TODO o NADA.
    Si una calificación ya existía para ese alumno y parcial, se actualiza.
    """
    mp = _curso_permitido(db, materia_periodo_id, usuario)

    if not (archivo.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(400, "El archivo debe ser un Excel .xlsx.")
    contenido = archivo.file.read(MAX_BYTES + 1)
    if len(contenido) > MAX_BYTES:
        raise HTTPException(413, "El archivo supera los 5 MB.")

    # 1) Validación del formato del Excel (columnas, números, duplicados)
    filas, errores = leer_calificaciones(BytesIO(contenido), MAX_PARCIALES)

    # 2) Validación contra la BD: la matrícula debe estar inscrita en ESTE grupo
    inscripciones = {i.alumno.matricula: i for i in mp.inscripciones}
    for f in filas:
        if f["matricula"] not in inscripciones:
            errores.append(f"Fila {f['fila']}: la matrícula {f['matricula']} no está inscrita en esta materia.")

    if errores:
        # 422 = "entendí tu archivo pero no es válido". No se guardó nada.
        raise HTTPException(422, detail={"mensaje": "El archivo tiene errores; no se guardó nada.", "errores": errores})

    # 3) Crear los parciales que falten (Parcial 1, 2, 3...)
    evaluaciones = {e.numero: e for e in mp.evaluaciones}
    for numero in sorted({f["parcial"] for f in filas}):
        if numero not in evaluaciones:
            nueva = Evaluacion(materia_periodo_id=mp.id, numero=numero, nombre_parcial=f"Parcial {numero}")
            db.add(nueva)
            evaluaciones[numero] = nueva
    db.flush()  # asigna ids a las evaluaciones recién creadas

    # 4) Insertar o actualizar calificaciones
    ids_insc = [i.id for i in inscripciones.values()]
    existentes = {
        (c.inscripcion_id, c.evaluacion_id): c
        for c in db.scalars(select(Calificacion).where(Calificacion.inscripcion_id.in_(ids_insc)))
    }
    nuevas = actualizadas = 0
    for f in filas:
        insc = inscripciones[f["matricula"]]
        ev = evaluaciones[f["parcial"]]
        previa = existentes.get((insc.id, ev.id))
        if previa:
            previa.calificacion = f["calificacion"]
            actualizadas += 1
        else:
            db.add(Calificacion(inscripcion_id=insc.id, evaluacion_id=ev.id, calificacion=f["calificacion"]))
            nuevas += 1
    db.commit()

    return {"mensaje": f"Listo: {nuevas} calificaciones nuevas y {actualizadas} actualizadas.", "nuevas": nuevas, "actualizadas": actualizadas}
