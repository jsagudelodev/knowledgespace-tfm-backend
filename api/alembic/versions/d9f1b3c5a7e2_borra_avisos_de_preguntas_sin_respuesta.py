"""borra los avisos de preguntas sin respuesta ya emitidos

Revision ID: d9f1b3c5a7e2
Revises: c4e8a2f6d1b3
Create Date: 2026-11-04

"Nueva pregunta sin respuesta" y "Pregunta resuelta" se dejaron de emitir el
2026-11-04: los creaba la acción de un admin (convertir, resolver) y le
llegaban a él mismo. Esta migración borra los que ya existían, para que no
sigan ocupando la bandeja en "Todas". Es una migración de datos.

Los tipos (`knowledge_gap_found`, `knowledge_gap_resolved`) se quedan en
`notification_types`: borrarlos no aporta nada y el catálogo es compartido.

`downgrade` no puede devolver los avisos borrados.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9f1b3c5a7e2"
down_revision: Union[str, Sequence[str], None] = "c4e8a2f6d1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM notifications
            WHERE type_id IN (
                SELECT id FROM notification_types
                WHERE name IN ('knowledge_gap_found', 'knowledge_gap_resolved')
            )
            """
        )
    )


def downgrade() -> None:
    pass
