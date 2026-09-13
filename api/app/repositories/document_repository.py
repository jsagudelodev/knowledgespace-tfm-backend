from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models.document import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db: Session):
        super().__init__(Document, db)

    def get_by_company(self, company_id: int, skip: int = 0, limit: int = 100) -> List[Document]:
        return (
            self.db.query(Document)
            .filter(Document.company_id == company_id)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_category(self, category_id: int) -> List[Document]:
        return self.db.query(Document).filter(Document.category_id == category_id).all()

    def get_by_status(self, company_id: int, status: str) -> List[Document]:
        return (
            self.db.query(Document)
            .filter(Document.company_id == company_id, Document.status == status)
            .all()
        )

    def count_by_company(self, company_id: int) -> int:
        return self.db.query(Document).filter(Document.company_id == company_id).count()
