from typing import Dict, List

from sqlalchemy import func
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

    def count_grouped_by_status(self, company_id: int) -> Dict[str, int]:
        """Recuento de documentos por estado, en una sola consulta agrupada en
        vez de una por estado. Lo usa el panel de inicio."""
        filas = (
            self.db.query(Document.status, func.count(Document.id))
            .filter(Document.company_id == company_id)
            .group_by(Document.status)
            .all()
        )
        return {estado: total for estado, total in filas}

    def count_by_assistant(self, assistant_id: int) -> int:
        return self.db.query(Document).filter(Document.assistant_id == assistant_id).count()

    def get_by_assistant(self, assistant_id: int) -> List[Document]:
        return (
            self.db.query(Document)
            .filter(Document.assistant_id == assistant_id)
            .order_by(Document.created_at.desc())
            .all()
        )
