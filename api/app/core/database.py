"""Fuente única de la conexión a PostgreSQL: `Base`, `engine`, `SessionLocal`
y `get_db`.

Todos los modelos heredan de la `Base` definida aquí, y todos los endpoints
obtienen su sesión con `Depends(get_db)`. Es deliberado que exista un solo
sitio: dos `declarative_base()` distintos producen dos registros de metadatos
separados, y las relaciones entre modelos de uno y otro no resuelven.

Notas de implementación:

- **Una sesión por request.** `get_db` es un generador que FastAPI cierra al
  terminar la petición, pase lo que pase. No hay sesión compartida entre
  peticiones ni estado en memoria entre usuarios.

- **`pool_pre_ping`** — ver el comentario junto a `create_engine`.

- **El esquema no se gestiona desde aquí.** El primer arranque crea las
  tablas con `Base.metadata.create_all` desde el endpoint de bootstrap
  (`routers/v1/setup.py`), que se autobloquea en cuanto existe un usuario.
  **A partir del 21 de octubre de 2026, los cambios de esquema posteriores
  se gestionan con Alembic** (`api/alembic/`), no con los `migrate_*.sql`
  sueltos de versiones anteriores —esos quedan como registro histórico de
  cómo se llegó al esquema actual, no como el procedimiento vigente—.
  Flujo: `alembic revision --autogenerate -m "..."`, revisar el archivo
  generado a mano (autogenerate propone, no decide) y `alembic upgrade
  head`. La URL de conexión la toma `alembic/env.py` de
  `settings.DATABASE_URL`, la misma que usa la aplicación.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# pool_pre_ping=True envía un SELECT 1 antes de cada conexión para detectar
# y reemplazar conexiones idle cerradas por Supabase / el load balancer.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
