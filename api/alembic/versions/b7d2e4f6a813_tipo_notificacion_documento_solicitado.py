"""tipo de notificación document_requested

Revision ID: b7d2e4f6a813
Revises: a1c3f5e7b902
Create Date: 2026-11-02

"Pedir documento" en Preguntas sin respuesta asignaba a una persona pero no le
avisaba: no existía ningún tipo de notificación para eso. Ahora el responsable
recibe "Documento solicitado", y como los usuarios ya pueden subir documentos,
el ciclo se cierra sin depender del administrador.

Es una migración de datos, no de esquema: inserta una fila en el catálogo
`notification_types` solo si no existe (el servicio resuelve los tipos por
nombre y, si falta, la notificación se pierde en silencio). `setup` siembra el
mismo tipo en instalaciones nuevas.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7d2e4f6a813"
down_revision: Union[str, Sequence[str], None] = "a1c3f5e7b902"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO notification_types (name, label, description, icon, color, is_active)
            SELECT 'document_requested', 'Documento solicitado',
                   'Un administrador te pidió un documento para responder una pregunta.',
                   'file-plus', '#2563EB', true
            WHERE NOT EXISTS (SELECT 1 FROM notification_types WHERE name = 'document_requested')
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM notification_types
            WHERE name = 'document_requested'
              AND NOT EXISTS (
                  SELECT 1 FROM notifications n WHERE n.type_id = notification_types.id
              )
            """
        )
    )
