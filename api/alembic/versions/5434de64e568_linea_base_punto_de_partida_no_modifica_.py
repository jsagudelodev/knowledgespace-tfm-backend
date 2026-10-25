"""linea base: punto de partida, no modifica nada

Revision ID: 5434de64e568
Revises:
Create Date: 2026-10-21 20:57:47.476554

Esta migración está deliberadamente vacía. La base de datos real (Supabase)
ya tenía todas las tablas creadas por `Base.metadata.create_all()` antes de
que existiera Alembic en este proyecto -no había nada que crear-, así que el
único trabajo de esta primera revisión es servir de ancla: a partir de aquí,
`alembic upgrade head` / `alembic downgrade` empiezan a tener sentido.

Un intento de generarla con `--autogenerate` sí produjo diferencias reales
entre los modelos y la base (nombres de índice distintos, varias columnas
`nullable=False` en el modelo que la base permite vacías, un par de tipos de
dato). Se descartó esa migración a propósito: mezclar "empezar a usar
Alembic" con "corregir desviaciones de años de uso manual" en el mismo paso
es correr el riesgo de alterar producción sin haber revisado cada cambio por
separado. Esas diferencias quedan documentadas en `docs/TFM/MODELO_DATOS.md`
como deuda conocida, pendientes de reconciliar una a una, cada una en su
propia migración revisada antes de aplicarse.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5434de64e568'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
