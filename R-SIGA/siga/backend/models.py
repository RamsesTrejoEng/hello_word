"""
models.py — Las tablas de la base de datos (tu diagrama ER hecho código).

Cada clase = una tabla. Cada atributo Mapped[...] = una columna.
relationship() NO crea columnas: solo te deja navegar entre tablas en Python
(por ejemplo inscripcion.alumno.nombre) sin escribir JOINs a mano.

Regla de oro del diseño: NADA SE BORRA. Una materia que deja de impartirse
solo deja de recibir registros en materias_periodo; sus calificaciones viejas
siguen ahí y forman el historial académico.

CAMBIO RESPECTO AL DIAGRAMA ORIGINAL: las contraseñas ya no están en
alumnos/profesores sino en la tabla `usuarios` (login único con roles, más
limpio y permite tener administradores).
"""
from datetime import date

from sqlalchemy import (Boolean, CheckConstraint, Date, Float, ForeignKey,
                        String, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Alumno(Base):
    __tablename__ = "alumnos"

    id: Mapped[int] = mapped_column(primary_key=True)
    matricula: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    generacion: Mapped[str | None] = mapped_column(String(20))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    inscripciones: Mapped[list["Inscripcion"]] = relationship(back_populates="alumno")


class Profesor(Base):
    __tablename__ = "profesores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    materias_periodo: Mapped[list["MateriaPeriodo"]] = relationship(back_populates="profesor")


class Materia(Base):
    """Catálogo maestro. Una materia existe aquí para siempre."""
    __tablename__ = "materias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    area: Mapped[str | None] = mapped_column(String(80))
    # activa=False significa "ya no se imparte" (NO se borra; pasa al historial).
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class Periodo(Base):
    """Un semestre/ciclo escolar. Solo uno debería estar activo a la vez."""
    __tablename__ = "periodos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(20), unique=True)  # ej. "2026-B"
    fecha_inicio: Mapped[date | None] = mapped_column(Date)
    fecha_fin: Mapped[date | None] = mapped_column(Date)
    activo: Mapped[bool] = mapped_column(Boolean, default=False)


class MateriaPeriodo(Base):
    """
    TABLA PUENTE CLAVE: "esta materia se imparte en este periodo con este
    profesor". Así las materias pueden cambiar cada semestre sin tocar el
    catálogo ni perder historial.
    """
    __tablename__ = "materias_periodo"
    __table_args__ = (UniqueConstraint("materia_id", "periodo_id", "profesor_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    materia_id: Mapped[int] = mapped_column(ForeignKey("materias.id"))
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodos.id"))
    profesor_id: Mapped[int] = mapped_column(ForeignKey("profesores.id"))

    materia: Mapped[Materia] = relationship()
    periodo: Mapped[Periodo] = relationship()
    profesor: Mapped[Profesor] = relationship(back_populates="materias_periodo")
    inscripciones: Mapped[list["Inscripcion"]] = relationship(back_populates="materia_periodo")
    evaluaciones: Mapped[list["Evaluacion"]] = relationship(back_populates="materia_periodo")


class Inscripcion(Base):
    """Un alumno cursando una materia en un periodo concreto."""
    __tablename__ = "inscripciones"
    __table_args__ = (UniqueConstraint("alumno_id", "materia_periodo_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    alumno_id: Mapped[int] = mapped_column(ForeignKey("alumnos.id"))
    materia_periodo_id: Mapped[int] = mapped_column(ForeignKey("materias_periodo.id"))

    alumno: Mapped[Alumno] = relationship(back_populates="inscripciones")
    materia_periodo: Mapped[MateriaPeriodo] = relationship(back_populates="inscripciones")
    calificaciones: Mapped[list["Calificacion"]] = relationship(back_populates="inscripcion")


class Evaluacion(Base):
    """Un parcial de una materia en un periodo (numero = 1, 2, 3...)."""
    __tablename__ = "evaluaciones"
    __table_args__ = (
        UniqueConstraint("materia_periodo_id", "numero"),
        CheckConstraint("numero >= 1", name="ck_evaluacion_numero"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    materia_periodo_id: Mapped[int] = mapped_column(ForeignKey("materias_periodo.id"))
    numero: Mapped[int]
    nombre_parcial: Mapped[str] = mapped_column(String(60))
    fecha: Mapped[date | None] = mapped_column(Date)

    materia_periodo: Mapped[MateriaPeriodo] = relationship(back_populates="evaluaciones")
    calificaciones: Mapped[list["Calificacion"]] = relationship(back_populates="evaluacion")


class Calificacion(Base):
    """
    La tabla más delgada a propósito: une inscripción + evaluación + número.
    Promedios e historial se CALCULAN con consultas, no se guardan.
    """
    __tablename__ = "calificaciones"
    __table_args__ = (
        UniqueConstraint("inscripcion_id", "evaluacion_id"),
        # La propia base de datos rechaza calificaciones fuera de 0-10.
        CheckConstraint("calificacion >= 0 AND calificacion <= 10", name="ck_calificacion_rango"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    inscripcion_id: Mapped[int] = mapped_column(ForeignKey("inscripciones.id"))
    evaluacion_id: Mapped[int] = mapped_column(ForeignKey("evaluaciones.id"))
    calificacion: Mapped[float] = mapped_column(Float)

    inscripcion: Mapped[Inscripcion] = relationship(back_populates="calificaciones")
    evaluacion: Mapped[Evaluacion] = relationship(back_populates="calificaciones")


class Usuario(Base):
    """
    Login único. Cada usuario tiene un rol:
    - alumno: ligado a un registro de `alumnos`
    - profesor: ligado a un registro de `profesores`
    - admin: no se liga a nadie
    La contraseña NUNCA se guarda en claro, solo su hash (bcrypt).
    """
    __tablename__ = "usuarios"
    __table_args__ = (CheckConstraint("rol IN ('alumno','profesor','admin')", name="ck_usuario_rol"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(20))
    alumno_id: Mapped[int | None] = mapped_column(ForeignKey("alumnos.id"), unique=True)
    profesor_id: Mapped[int | None] = mapped_column(ForeignKey("profesores.id"), unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    alumno: Mapped[Alumno | None] = relationship()
    profesor: Mapped[Profesor | None] = relationship()
