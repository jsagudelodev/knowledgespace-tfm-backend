from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_company(self, company_id: int, skip: int = 0, limit: int = 100) -> List[User]:
        return (
            self.db.query(User)
            .filter(User.company_id == company_id)
            .order_by(User.full_name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_company(self, company_id: int) -> int:
        return self.db.query(User).filter(User.company_id == company_id).count()

    def get_active_by_company(self, company_id: int) -> List[User]:
        return (
            self.db.query(User)
            .filter(User.company_id == company_id, User.is_active.is_(True))
            .order_by(User.full_name)
            .all()
        )
