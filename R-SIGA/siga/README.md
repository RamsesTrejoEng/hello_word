# SIGA — Sistema Integral de Gestión Académica

Sistema web para centralizar las calificaciones de la preparatoria: los alumnos
consultan lo suyo, los profesores suben calificaciones desde Excel y el
historial académico se conserva aunque las materias cambien cada semestre.

## 1. Qué hace cada archivo

```
siga/
├── backend/                  ← el "cerebro" (Python + FastAPI)
│   ├── main.py               Arranca la app, registra rutas y sirve el frontend
│   ├── config.py             Lee la configuración (.env): base de datos, llave secreta
│   ├── database.py           Conexión con la base de datos (SQLAlchemy)
│   ├── models.py             Las 9 tablas (tu diagrama ER hecho código)
│   ├── schemas.py            Valida los datos que llegan a la API (Pydantic)
│   ├── auth.py               Hash de contraseñas, tokens JWT y control por roles
│   ├── excel.py              Lee y valida los Excel; genera la plantilla
│   ├── services.py           Cálculos compartidos (promedios, parciales)
│   ├── seed.py               Datos de ejemplo para probar
│   ├── importar_alumnos.py   Alta masiva de alumnos desde Excel
│   └── routers/
│       ├── auth.py           POST /auth/login, /auth/cambiar-password
│       ├── alumno.py         GET /alumno/calificaciones (solo lo del propio alumno)
│       ├── profesor.py       Grupos, tabla del grupo, plantilla, subir Excel
│       └── admin.py          Alta de periodos, materias, profesores, alumnos, grupos
├── frontend/                 ← lo que ve el usuario
│   ├── index.html · login.html · dashboard.html (alumno) · profesor.html (docente/admin)
│   ├── style.css             Estilo (colores en variables al inicio)
│   └── js/
│       ├── comun.js          Sesión, fetch con token, promedios, formato
│       ├── login.js · dashboard.js · profesor.js   Lógica de cada pantalla
├── tests/                    Pruebas automáticas (Excel y API)
├── schema.dbml               Modelo actualizado para dbdiagram.io
├── requirements.txt · .env.example · .gitignore
```

## 2. Arranque rápido (Fedora)

```bash
sudo dnf install python3 python3-pip git
cd siga
python3 -m venv .venv            # entorno aislado de Python
source .venv/bin/activate        # (cada vez que abras una terminal nueva)
pip install -r requirements.txt
cp .env.example .env             # y edita SECRET_KEY (ver dentro del archivo)
python -m backend.seed           # carga datos de ejemplo
uvicorn backend.main:app --reload
```

Abre http://localhost:8000 y entra con:

| Rol | Usuario | Contraseña |
|---|---|---|
| Alumno | 20260101 | 20260101 |
| Profesor | prof.garcia | profesor123 |
| Admin | admin | admin12345 |

La documentación interactiva de la API está en http://localhost:8000/docs.

## 3. Pasar de SQLite a PostgreSQL

Por defecto usa SQLite (un archivo `siga.db`) para que arranques sin instalar nada.
Para PostgreSQL (recomendado antes de usarlo con datos reales):

```bash
sudo dnf install postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl enable --now postgresql
sudo -u postgres psql -c "CREATE USER siga WITH PASSWORD 'TU_CLAVE';"
sudo -u postgres psql -c "CREATE DATABASE siga OWNER siga;"
```

Tropiezo típico en Fedora: edita `/var/lib/pgsql/data/pg_hba.conf` y cambia `ident`
por `scram-sha-256` en las líneas de `127.0.0.1` y `::1`; luego
`sudo systemctl restart postgresql`. Después en `.env`:

```
DATABASE_URL=postgresql+psycopg2://siga:TU_CLAVE@localhost:5432/siga
```

## 4. Cargar los datos REALES de la escuela (en este orden)

1. Borra la base de ejemplo (`rm siga.db`) o usa una base PostgreSQL vacía y arranca el servidor una vez (crea las tablas).
2. Crea tu admin real (ver sección 6) y cambia `admin12345`.
3. Alumnos: `python -m backend.importar_alumnos alumnos.xlsx` (columnas MATRICULA, NOMBRE, GENERACION).
4. En /docs (botón **Authorize** con tu token de admin):
   `POST /admin/periodos` (activo=true) → `POST /admin/materias` →
   `POST /admin/profesores` → `POST /admin/materias-periodo` (un grupo por materia+profesor) →
   `POST /admin/inscripciones` (lista de matrículas por grupo).
5. Los profesores entran a `profesor.html`, descargan la plantilla y suben sus calificaciones.

**Cambio de semestre:** `POST /admin/periodos` con el periodo nuevo (activo=true) y repite
`materias-periodo` + `inscripciones`. El periodo anterior se desactiva solo y pasa al historial.
**Una materia deja de impartirse:** `PATCH /admin/materias/{id}` con `{"activa": false}`.
No se borra nada.

## 5. Plantilla de Excel

`MATRICULA | NOMBRE | PARCIAL | CALIFICACION`, una fila por alumno y parcial. Si una
sola fila tiene error (matrícula inexistente, "ocho", duplicado, parcial 5...), se
rechaza TODO el archivo y se listan los errores con su fila. Volver a subir un parcial
ya capturado actualiza la calificación.

## 6. Crear el primer administrador real

```bash
python3 - <<'PY'
from backend.database import Base, SessionLocal, engine
from backend.models import Usuario
from backend.auth import hashear_password
Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    db.add(Usuario(usuario="TU_USUARIO", rol="admin", password_hash=hashear_password("UNA_CLAVE_LARGA")))
    db.commit()
PY
```

## 7. Seguridad: qué ya está y qué falta

Ya está: contraseñas con bcrypt, sesiones JWT con expiración, roles (alumno/profesor/admin),
el alumno se identifica por token (no por URL), un profesor solo toca sus grupos, la base
rechaza calificaciones fuera de 0-10, validación estricta del Excel (extensión, 5 MB, estructura).

Falta antes de producción real:
- **HTTPS** (certificado) — sin él, las contraseñas viajan en claro por la red.
- **Límite de intentos de login** (anti fuerza bruta).
- Obligar a **cambiar la contraseña inicial** (hoy existe `/auth/cambiar-password` pero no se obliga ni hay pantalla).
- Un **panel visual de administración** (hoy se usa /docs).
- Respaldos automáticos de la base (`pg_dump`) y migraciones con Alembic.
- Cumplir el aviso de privacidad: son datos de menores de edad; consúltalo con la dirección.

## 8. Pruebas

```bash
pytest -v          # Excel (8 pruebas) + API (7 pruebas)
```

## 9. Cómo adaptar

| Quiero... | Cambio |
|---|---|
| 4 parciales en vez de 3 | `MAX_PARCIALES` en `.env`; en el frontend, el `3` de los `for` y un `<th>` en las tablas |
| Otra nota mínima aprobatoria | El `6` en `dashboard.js` y `profesor.js` |
| Colores | Variables al inicio de `style.css` |
| Promedio ponderado | `calcularPromedio` (JS) y `promedio` en `services.py` |
| Más duración de sesión | `TOKEN_MINUTOS` en `.env` |
