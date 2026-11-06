"""services.py — Cálculos compartidos por varias rutas."""
from backend.config import MAX_PARCIALES
from backend.models import Inscripcion


def promedio(valores) -> float | None:
    """Promedio ignorando huecos (None). Devuelve None si no hay datos."""
    numeros = [v for v in valores if v is not None]
    return round(sum(numeros) / len(numeros), 2) if numeros else None


def parciales_de(inscripcion: Inscripcion) -> list[float | None]:
    """
    Lista con una posición por parcial: [8.5, 9.0, None].
    None = ese parcial todavía no tiene calificación.
    """
    lista: list[float | None] = [None] * MAX_PARCIALES
    for c in inscripcion.calificaciones:
        posicion = c.evaluacion.numero - 1
        if 0 <= posicion < MAX_PARCIALES:
            lista[posicion] = c.calificacion
    return lista
