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

- **El esquema no se gestiona desde aquí.** Las tablas se crean una sola vez,
  con `Base.metadata.create_all` desde el endpoint de bootstrap
  (`routers/v1/setup.py`), que se autobloquea en cuanto existe un usuario.
  A partir de ahí, cada cambio de esquema se aplica a mano con los
  `migrate_*.sql` de `api/`. **No hay Alembic**, así que no existe historial
  de migraciones ni forma automática de revertir uno: es una limitación
  conocida y el primer punto a resolver si el proyecto siguiera creciendo.
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
