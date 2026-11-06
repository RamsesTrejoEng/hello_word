"""
config.py — Configuración central del sistema.

Todo lo que cambia entre tu computadora y un servidor real (base de datos,
llave secreta) se lee de VARIABLES DE ENTORNO, no se escribe en el código.
Así nunca subes contraseñas a GitHub. Las variables se definen en el archivo
.env (copia de .env.example), que python-dotenv carga aquí.
"""
import os
from dotenv import load_dotenv

load_dotenv()  # lee el archivo .env si existe

# Dirección de la base de datos.
# Por defecto usa SQLite (un archivo siga.db) para que puedas arrancar YA sin
# instalar nada. Para PostgreSQL pon en .env:
#   DATABASE_URL=postgresql+psycopg2://usuario:clave@localhost:5432/siga
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./siga.db")

# Llave con la que se FIRMAN los tokens de sesión (JWT). Si alguien la conoce,
# puede fabricar sesiones falsas. En .env pon una cadena larga y aleatoria.
SECRET_KEY = os.getenv("SECRET_KEY", "cambia-esto-por-una-llave-larga-y-aleatoria")
ALGORITHM = "HS256"
TOKEN_MINUTOS = int(os.getenv("TOKEN_MINUTOS", "120"))  # duración de la sesión

# Número de parciales por materia (la plantilla de Excel y la tabla lo usan).
MAX_PARCIALES = int(os.getenv("MAX_PARCIALES", "3"))

# Orígenes del frontend permitidos si lo sirves aparte (ej. Live Server :5500).
# Si usas el frontend que sirve el propio backend, no hace falta tocar esto.
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500").split(",")
    if o.strip()
]
