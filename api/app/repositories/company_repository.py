from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.company import Company
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, db: Session):
        super().__init__(Company, db)

    def get_by_email(self, email: str) -> Optional[Company]:
        return self.db.query(Company).filter(Company.email == email).first()

    def get_active(self) -> List[Company]:
        return (
            self.db.query(Company)
            # `== True` y no `.is_(True)`: la columna es INTEGER (ver IntBoolean) y
            # Postgres no acepta `IS true` sobre un entero.
            .filter(Company.is_active == True)  # noqa: E712
            .order_by(Company.name)
            .all()
        )

    def get_by_plan(self, plan: str) -> List[Company]:
        return (
            self.db.query(Company)
            .filter(Company.plan == plan)
            .order_by(Company.name)
            .all()
        )
