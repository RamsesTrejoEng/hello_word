"""
schemas.py — La "forma" de los datos que entran a la API (Pydantic).

Si el frontend manda algo que no cumple (contraseña muy corta, fecha mal
escrita...), FastAPI responde 422 automáticamente SIN que escribas código.
Es tu primera capa de validación.
"""
from datetime import date

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    usuario: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: str
    nombre: str


class CambioPassword(BaseModel):
    actual: str = Field(max_length=72)
    nueva: str = Field(min_length=8, max_length=72)


class ResetPassword(BaseModel):
    usuario: str
    nueva: str = Field(min_length=8, max_length=72)


class AlumnoCreate(BaseModel):
    matricula: str = Field(min_length=1, max_length=20)
    nombre: str = Field(min_length=1, max_length=120)
    generacion: str | None = None
    # Si no se manda, la contraseña inicial es la propia matrícula.
    password: str | None = Field(default=None, min_length=8, max_length=72)


class ProfesorCreate(BaseModel):
    usuario: str = Field(min_length=3, max_length=50)
    nombre: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=72)


class MateriaCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    area: str | None = None


class MateriaUpdate(BaseModel):
    activa: bool


class PeriodoCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=20)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    activo: bool = False


class MateriaPeriodoCreate(BaseModel):
    materia_id: int
    periodo_id: int
    profesor_id: int


class InscripcionMasiva(BaseModel):
    materia_periodo_id: int
    matriculas: list[str] = Field(min_length=1, max_length=1000)
