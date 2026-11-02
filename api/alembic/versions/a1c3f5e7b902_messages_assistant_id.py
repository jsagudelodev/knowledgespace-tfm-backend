"""messages.assistant_id: con qué asistente se respondió cada mensaje

Revision ID: a1c3f5e7b902
Revises: 5434de64e568
Create Date: 2026-11-02

Hasta ahora un mensaje no sabía qué asistente lo respondió: el asistente se
elige mensaje a mensaje en el chat y no se guardaba. Dos consecuencias reales,
encontradas en la prueba de punta a punta del 2026-11-02:

- al reabrir una conversación se seleccionaba el primer asistente activo, no
  el de la conversación, y seguir escribiendo preguntaba a otro asistente;
- el feedback se atribuía al asistente seleccionado en pantalla al calificar,
  no al que respondió, y la pregunta sin respuesta derivada podía acabar en el
  espacio de conocimiento equivocado.

Solo añade una columna que admite NULL: no reescribe filas ni toca otras
tablas. Los mensajes anteriores quedan con NULL (no hay forma fiable de
reconstruir el asistente) y el código lo trata como "desconocido".
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1c3f5e7b902"
down_revision: Union[str, Sequence[str], None] = "5434de64e568"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("assistant_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_messages_assistant_id",
        "messages", "assistants",
        ["assistant_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_messages_assistant_id", "messages", ["assistant_id"])


def downgrade() -> None:
    op.drop_index("ix_messages_assistant_id", table_name="messages")
    op.drop_constraint("fk_messages_assistant_id", "messages", type_="foreignkey")
    op.drop_column("messages", "assistant_id")
