from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models.tag import Tag
from app.repositories.base import BaseRepository


class TagRepository(BaseRepository[Tag]):
    def __init__(self, db: Session):
        super().__init__(Tag, db)

    def get_by_company(self, company_id: int, skip: int = 0, limit: int = 100) -> List[Tag]:
        return (
            self.db.query(Tag)
            .filter(Tag.company_id == company_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_name(self, company_id: int, name: str) -> Optional[Tag]:
        return (
            self.db.query(Tag)
            .filter(Tag.company_id == company_id, Tag.name == name)
            .first()
        )

    def search_by_name(self, company_id: int, name: str) -> List[Tag]:
        return (
            self.db.query(Tag)
            .filter(Tag.company_id == company_id, Tag.name.ilike(f"%{name}%"))
            .all()
        )
