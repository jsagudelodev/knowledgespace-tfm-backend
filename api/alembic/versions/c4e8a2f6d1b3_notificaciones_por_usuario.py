"""notificaciones por usuario: reparte los avisos compartidos entre los admins

Revision ID: c4e8a2f6d1b3
Revises: b7d2e4f6a813
Create Date: 2026-11-03

Los avisos para administradores (pregunta sin respuesta nueva o resuelta) se
guardaban en una sola fila con `user_id = NULL` que veían todos los admins de la
empresa. "Leída" era entonces compartida —un admin que la marcaba se la quitaba
de "No leídas" a los demás— y borrarla se la habría borrado a todos.

Desde el 2026-11-03 cada aviso se crea como una copia por admin activo. Esta
migración hace lo mismo con las filas antiguas: crea una copia para cada admin
o superadmin activo de la empresa, conservando lectura y fecha, y borra la fila
compartida. Es una migración de datos, no de esquema.

`downgrade` no reconstruye las filas compartidas: las copias son indistinguibles
de las creadas después, y fundirlas podría mezclar avisos distintos.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4e8a2f6d1b3"
down_revision: Union[str, Sequence[str], None] = "b7d2e4f6a813"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO notifications
                (company_id, user_id, type_id, title, message, entity_type, entity_id,
                 read, read_at, created_at)
            SELECT n.company_id, u.id, n.type_id, n.title, n.message, n.entity_type, n.entity_id,
                   n.read, n.read_at, n.created_at
            FROM notifications n
            JOIN users u
              ON u.company_id = n.company_id
             AND u.role IN ('admin', 'superadmin')
             AND u.is_active IS TRUE
            WHERE n.user_id IS NULL
            """
        )
    )
    op.execute(sa.text("DELETE FROM notifications WHERE user_id IS NULL"))


def downgrade() -> None:
    pass
