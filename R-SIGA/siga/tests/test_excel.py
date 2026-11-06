"""
Pruebas del lector de Excel (no necesitan servidor ni base de datos).
Ejecutar:  pytest tests/test_excel.py
"""
from io import BytesIO

from openpyxl import Workbook

from backend.excel import generar_plantilla, leer_calificaciones


def hacer_excel(filas, encabezado=("MATRICULA", "NOMBRE", "PARCIAL", "CALIFICACION")):
    libro = Workbook()
    hoja = libro.active
    hoja.append(list(encabezado))
    for fila in filas:
        hoja.append(list(fila))
    salida = BytesIO()
    libro.save(salida)
    salida.seek(0)
    return salida


def test_archivo_valido():
    filas, errores = leer_calificaciones(hacer_excel([("20260101", "Juan", 1, 8.5), (20260102, "Ana", 1, "9,2")]))
    assert errores == []
    assert [f["matricula"] for f in filas] == ["20260101", "20260102"]
    assert filas[1]["calificacion"] == 9.2


def test_falta_columna():
    _, errores = leer_calificaciones(hacer_excel([("20260101", 8.5)], encabezado=("MATRICULA", "CALIFICACION")))
    assert any("PARCIAL" in e for e in errores)


def test_acentos_en_encabezado():
    filas, errores = leer_calificaciones(hacer_excel([("1", "A", 1, 7)], encabezado=("Matrícula", "Nombre", "Parcial", "Calificación")))
    assert errores == [] and len(filas) == 1


def test_calificacion_invalida_y_fuera_de_rango():
    _, errores = leer_calificaciones(hacer_excel([("1", "A", 1, "ocho"), ("2", "B", 1, 11)]))
    assert len(errores) == 2 and "Fila 2" in errores[0] and "Fila 3" in errores[1]


def test_parcial_invalido():
    _, errores = leer_calificaciones(hacer_excel([("1", "A", 4, 8), ("2", "B", 1.5, 8)]))
    assert len(errores) == 2


def test_duplicados():
    _, errores = leer_calificaciones(hacer_excel([("1", "A", 1, 8), ("1", "A", 1, 9)]))
    assert any("duplicado" in e for e in errores)


def test_no_es_excel():
    _, errores = leer_calificaciones(BytesIO(b"esto no es un excel"))
    assert errores == ["El archivo no es un Excel (.xlsx) válido."]


def test_plantilla_se_puede_leer_de_vuelta():
    _, errores = leer_calificaciones(BytesIO(generar_plantilla()))
    assert errores == ["El archivo no tiene filas de calificaciones."]
