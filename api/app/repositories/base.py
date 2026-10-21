from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Repositorio genérico con CRUD básico.

    Uso:
        class UserRepository(BaseRepository[User]):
            def __init__(self, db: Session):
                super().__init__(User, db)
    """

    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get(self, id) -> Optional[ModelType]:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_of_company(self, id, company_id: int) -> Optional[ModelType]:
        """Como `get`, pero exige que el registro pertenezca a `company_id`.

        Centraliza la verificación de aislamiento multi-tenant que se repetía
        router a router (`if not x or x.company_id != current_user.company_id:
        raise HTTPException(404, ...)`) — generalizada aquí desde el patrón
        que ya existía, duplicado, en `KnowledgeGapRepository.get_of_company`.
        Asume que `ModelType` tiene una columna `company_id`; no usar en
        repositorios de modelos que no la tengan.
        """
        obj = self.get(id)
        return obj if obj and obj.company_id == company_id else None

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: ModelType) -> ModelType:
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: ModelType) -> None:
        self.db.delete(obj)
        self.db.commit()
