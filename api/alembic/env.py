"""Configuración de Alembic para este proyecto.

Dos cosas no vienen en la plantilla por defecto y son las que hacen que esto
funcione contra la base real:

1. **La URL de conexión sale de `settings.DATABASE_URL`**, la misma que usa
   la aplicación — no se duplica en `alembic.ini` ni se vuelve a escribir a
   mano, para que no puedan divergir.

2. **`include_object` excluye lo que existe en Supabase pero no tiene
   modelo.** La base de datos real tiene ocho tablas de funcionalidades
   fuera del alcance del TFM (`budget_limits`, `quota_alerts`, `audit_logs`,
   `support_tickets`, `courses`, `quizzes`, `quiz_results`, `enrollments` —
   ver `ALCANCE_TFM.md`) y varias columnas huérfanas de una integración
   anterior (`assistants.suggested_prompts`, `cost_tracking.metadata`,
   `documents.source_url/fetched_at/source_type/source_domain`). Sin este
   filtro, `alembic revision --autogenerate` propondría borrarlas —son
   reales, con datos, y no es decisión de una migración automática quitarlas.
"""
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

# Registra todos los modelos en Base.metadata antes de que autogenerate
# los necesite — importar el paquete basta, __init__.py importa cada módulo.
import app.db.models  # noqa: F401
from alembic import context
from app.core.config import get_settings
from app.core.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().DATABASE_URL)

target_metadata = Base.metadata

# (tabla, None) para una tabla entera sin modelo; (tabla, columna) para una
# columna huérfana dentro de una tabla que sí tiene modelo.
TABLAS_SIN_MODELO = {
    "budget_limits", "quota_alerts", "audit_logs", "support_tickets",
    "courses", "quizzes", "quiz_results", "enrollments",
}
COLUMNAS_HUERFANAS = {
    ("assistants", "suggested_prompts"),
    ("cost_tracking", "metadata"),
    ("documents", "source_url"),
    ("documents", "fetched_at"),
    ("documents", "source_type"),
    ("documents", "source_domain"),
}


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name in TABLAS_SIN_MODELO:
        return False
    if type_ == "column" and (object.table.name, name) in COLUMNAS_HUERFANAS:
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
