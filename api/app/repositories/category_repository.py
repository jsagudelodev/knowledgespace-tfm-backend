from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.category import Category
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    def __init__(self, db: Session):
        super().__init__(Category, db)

    def get_by_company(self, company_id: int, skip: int = 0, limit: int = 200) -> List[Category]:
        return (
            self.db.query(Category)
            .filter(Category.company_id == company_id)
            .order_by(Category.sort_order, Category.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_name(self, company_id: int, name: str) -> Optional[Category]:
        return (
            self.db.query(Category)
            .filter(Category.company_id == company_id, Category.name == name)
            .first()
        )
