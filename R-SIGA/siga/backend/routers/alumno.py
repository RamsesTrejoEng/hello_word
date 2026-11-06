"""routers/alumno.py — Lo que ve un alumno (SOLO sus propios datos)."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth import requiere_rol
from backend.database import get_db
from backend.models import Inscripcion, Usuario
from backend.services import parciales_de, promedio

router = APIRouter(prefix="/alumno", tags=["Alumno"])


@router.get("/calificaciones")
def mis_calificaciones(
    usuario: Usuario = Depends(requiere_rol("alumno")),
    db: Session = Depends(get_db),
):
    """
    SEGURIDAD: el alumno se identifica por el TOKEN (usuario.alumno_id), nunca
    por un número en la URL. Por eso es imposible pedir las notas de otro
    alumno cambiando un id.

    Devuelve:
      calificaciones: materias del periodo ACTIVO con sus parciales
      historial: periodos anteriores con el promedio final por materia
    """
    inscripciones = db.scalars(
        select(Inscripcion).where(Inscripcion.alumno_id == usuario.alumno_id)
    ).all()

    actuales, historial, periodo_actual = [], {}, None
    for insc in inscripciones:
        mp = insc.materia_periodo
        parciales = parciales_de(insc)
        if mp.periodo.activo:
            periodo_actual = mp.periodo.nombre
            actuales.append({"materia": mp.materia.nombre, "parciales": parciales})
        else:
            grupo = historial.setdefault(
                mp.periodo.id,
                {"periodo": mp.periodo.nombre, "inicio": mp.periodo.fecha_inicio or date.min, "materias": []},
            )
            grupo["materias"].append({"materia": mp.materia.nombre, "promedio": promedio(parciales)})

    # periodos más recientes primero
    ordenado = sorted(historial.values(), key=lambda g: g["inicio"], reverse=True)
    for g in ordenado:
        del g["inicio"]

    return {"periodo_actual": periodo_actual, "calificaciones": actuales, "historial": ordenado}
