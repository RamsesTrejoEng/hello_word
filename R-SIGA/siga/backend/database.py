"""
database.py — Conexión con la base de datos.

Piezas de SQLAlchemy (el ORM: te deja usar clases de Python en vez de SQL):
- engine: la conexión física con la base de datos.
- SessionLocal: fábrica de "sesiones"; una sesión es una conversación con la
  base de datos (consultas + guardar cambios).
- Base: clase madre de todos los modelos (tablas) en models.py.
- get_db: dependencia de FastAPI que abre una sesión por petición y la cierra
  al terminar, pase lo que pase.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.config import DATABASE_URL

es_sqlite = DATABASE_URL.startswith("sqlite")

# SQLite exige este parámetro cuando varios hilos usan el mismo archivo.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if es_sqlite else {},
)

# SQLite NO hace respetar las llaves foráneas por defecto; esto lo activa
# para que se comporte como PostgreSQL (no deja inscribir a un alumno que
# no existe, por ejemplo).
if es_sqlite:
    @event.listens_for(engine, "connect")
    def activar_llaves_foraneas(conexion, _registro):
        conexion.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Clase madre de todas las tablas."""


def get_db():
    """Entrega una sesión a cada petición y garantiza que se cierre."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
