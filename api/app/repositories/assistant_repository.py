from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.assistant import Assistant
from app.db.models.widget import Widget
from app.repositories.base import BaseRepository


class AssistantRepository(BaseRepository[Assistant]):
    """Acceso a asistentes. Todas las consultas excluyen los borrados
    lógicamente (`deleted_at`), que es el criterio de "existe" en este modelo."""

    def __init__(self, db: Session):
        super().__init__(Assistant, db)

    def get_by_company(self, company_id: int, skip: int = 0, limit: int = 100) -> List[Assistant]:
        return (
            self.db.query(Assistant)
            .filter(Assistant.company_id == company_id, Assistant.deleted_at.is_(None))
            .order_by(Assistant.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_of_company(self, assistant_id: int, company_id: int) -> Optional[Assistant]:
        """Un asistente concreto, solo si pertenece a la empresa indicada.

        El filtro por `company_id` va aquí y no en el router a propósito: es
        lo que impide que un identificador de otra empresa resuelva. Quien
        llama recibe `None` y responde 404 — nunca 403, que confirmaría la
        existencia del recurso ajeno.
        """
        return (
            self.db.query(Assistant)
            .filter(
                Assistant.id == assistant_id,
                Assistant.company_id == company_id,
                Assistant.deleted_at.is_(None),
            )
            .first()
        )

    def list_by_company(
        self,
        company_id: int,
        skip: int = 0,
        limit: int = 100,
        active_only: Optional[bool] = None,
    ) -> List[Assistant]:
        query = self.db.query(Assistant).filter(
            Assistant.company_id == company_id,
            Assistant.deleted_at.is_(None),
        )
        if active_only:
            query = query.filter(Assistant.is_active.is_(True))
        return query.order_by(Assistant.name).offset(skip).limit(limit).all()

    def get_active_of_company(self, assistant_id: int, company_id: int) -> Optional[Assistant]:
        """Como `get_of_company`, pero exigiendo además que esté activo. Lo usa
        el chat: un asistente desactivado no debe poder responder consultas."""
        return (
            self.db.query(Assistant)
            .filter(
                Assistant.id == assistant_id,
                Assistant.company_id == company_id,
                Assistant.deleted_at.is_(None),
                Assistant.is_active.is_(True),
            )
            .first()
        )

    def get_first_active(self, company_id: int) -> Optional[Assistant]:
        """El asistente activo más antiguo de la empresa. Es el que usa el chat
        cuando no se especifica ninguno; `None` si la empresa no tiene."""
        return (
            self.db.query(Assistant)
            .filter(
                Assistant.company_id == company_id,
                Assistant.deleted_at.is_(None),
                Assistant.is_active.is_(True),
            )
            .order_by(Assistant.created_at.asc())
            .first()
        )

    def count_widgets(self, assistant_id: int) -> int:
        """Widgets vinculados al asistente.

        El módulo de widgets quedó fuera de esta entrega (ver `ALCANCE_TFM.md`),
        pero el vínculo permanece en el modelo de datos y se sigue contando:
        impide borrar un asistente que dejaría widgets huérfanos.
        """
        return self.db.query(Widget).filter(Widget.assistant_id == assistant_id).count()
