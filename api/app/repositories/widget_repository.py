from typing import List
from sqlalchemy.orm import Session
from app.db.models.widget import Widget
from app.repositories.base import BaseRepository


class WidgetRepository(BaseRepository[Widget]):
    def __init__(self, db: Session):
        super().__init__(Widget, db)

    def get_by_company(self, company_id: int, skip: int = 0, limit: int = 100) -> List[Widget]:
        return (
            self.db.query(Widget)
            .filter(Widget.company_id == company_id)
            .order_by(Widget.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
