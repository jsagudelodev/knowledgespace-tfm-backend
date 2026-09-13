from typing import List
from sqlalchemy.orm import Session
from app.db.models.assistant import Assistant
from app.repositories.base import BaseRepository


class AssistantRepository(BaseRepository[Assistant]):
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
