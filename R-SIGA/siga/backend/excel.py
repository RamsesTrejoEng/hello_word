"""
excel.py — Lee y VALIDA los Excel que suben los profesores.

Este archivo no sabe nada de la base de datos ni de FastAPI: solo recibe un
archivo y devuelve (filas_válidas, errores). Eso lo hace fácil de probar.

Plantilla oficial (una fila por alumno y parcial):
    MATRICULA | NOMBRE | PARCIAL | CALIFICACION
    20260101  | Juan   | 1       | 8.5

Filosofía: si el archivo tiene CUALQUIER error, no se guarda nada y se le
devuelve al profesor la lista completa de errores con número de fila.
"""
import unicodedata
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

MAX_FILAS = 2000
COLUMNAS = ["MATRICULA", "NOMBRE", "PARCIAL", "CALIFICACION"]
OBLIGATORIAS = ("MATRICULA", "PARCIAL", "CALIFICACION")  # NOMBRE es solo informativo


def _normalizar(valor) -> str:
    """'Matrícula ' -> 'MATRICULA' (sin acentos, mayúsculas, sin espacios)."""
    if valor is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode("ascii")
    return texto.strip().upper()


def _a_matricula(valor) -> str:
    """Excel a veces guarda 20260101 como número (20260101.0); lo vuelve texto limpio."""
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return str(valor).strip()


def _a_numero(valor) -> float | None:
    """Convierte a número o devuelve None si no se puede (ej. 'ocho')."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        try:
            return float(valor.strip().replace(",", "."))  # acepta "8,5"
        except ValueError:
            return None
    return None


def leer_calificaciones(archivo, max_parcial: int = 3) -> tuple[list[dict], list[str]]:
    """
    archivo: objeto tipo archivo (BytesIO) con un .xlsx.
    Devuelve (filas, errores). Cada fila válida es un diccionario:
        {"fila": 3, "matricula": "20260101", "parcial": 1, "calificacion": 8.5}
    """
    try:
        libro = load_workbook(archivo, read_only=True, data_only=True)
    except Exception:
        return [], ["El archivo no es un Excel (.xlsx) válido."]

    filas, errores = [], []
    iterador = libro.active.iter_rows(values_only=True)

    encabezado = next(iterador, None)
    if not encabezado:
        libro.close()
        return [], ["El archivo está vacío."]

    # posición de cada columna según su nombre (así no importa el orden)
    posiciones = {_normalizar(n): i for i, n in enumerate(encabezado) if n is not None}
    for columna in OBLIGATORIAS:
        if columna not in posiciones:
            errores.append(f"Falta la columna {columna}.")
    if errores:
        libro.close()
        return [], errores

    def celda(fila, nombre):
        i = posiciones[nombre]
        return fila[i] if i < len(fila) else None

    vistos: dict[tuple[str, int], int] = {}  # (matrícula, parcial) -> fila donde apareció
    for n, fila in enumerate(iterador, start=2):  # start=2: la fila 1 es el encabezado
        if n - 1 > MAX_FILAS:
            errores.append(f"El archivo supera el máximo de {MAX_FILAS} filas.")
            break
        if not fila or all(c is None or str(c).strip() == "" for c in fila):
            continue  # fila vacía

        antes = len(errores)
        matricula = _a_matricula(celda(fila, "MATRICULA"))
        parcial = _a_numero(celda(fila, "PARCIAL"))
        crudo = celda(fila, "CALIFICACION")
        valor = _a_numero(crudo)

        if not matricula:
            errores.append(f"Fila {n}: falta la matrícula.")
        if parcial is None or not parcial.is_integer() or not (1 <= parcial <= max_parcial):
            errores.append(f"Fila {n}: el parcial debe ser un número entero entre 1 y {max_parcial}.")
        if valor is None or not (0 <= valor <= 10):
            errores.append(f'Fila {n}: la calificación "{crudo}" no es un número entre 0 y 10.')
        if len(errores) > antes:
            continue

        clave = (matricula, int(parcial))
        if clave in vistos:
            errores.append(f"Fila {n}: duplicado de la fila {vistos[clave]} (misma matrícula y parcial).")
            continue
        vistos[clave] = n
        filas.append({"fila": n, "matricula": matricula, "parcial": int(parcial), "calificacion": valor})

    libro.close()
    if not filas and not errores:
        errores.append("El archivo no tiene filas de calificaciones.")
    return filas, errores


def generar_plantilla() -> bytes:
    """Crea el .xlsx vacío que descargan los profesores (encabezado + instrucciones)."""
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Calificaciones"
    hoja.append(COLUMNAS)
    for celda in hoja[1]:
        celda.font = Font(bold=True)
    for letra, ancho in zip("ABCD", (16, 34, 10, 16)):
        hoja.column_dimensions[letra].width = ancho

    ayuda = libro.create_sheet("Instrucciones")
    for linea in (
        "Una fila por alumno y por parcial.",
        "MATRICULA: la matrícula del alumno (debe estar inscrito en la materia).",
        "NOMBRE: opcional, solo para tu referencia.",
        "PARCIAL: 1, 2 o 3.",
        "CALIFICACION: número de 0 a 10 (puedes usar decimales).",
        "Si subes de nuevo un parcial ya capturado, se ACTUALIZA la calificación.",
        "Si una sola fila tiene error, el archivo completo se rechaza y se te indica cuáles.",
    ):
        ayuda.append([linea])
    ayuda.column_dimensions["A"].width = 90

    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()
