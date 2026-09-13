from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.routers.v1.security import get_current_user
from app.db.models.category import Category
from app.db.models.user import User
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse

router = APIRouter()


@router.get("/", response_model=List[CategoryResponse], summary="Listar categorías de la empresa")
async def list_categories(
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return CategoryRepository(db).get_by_company(current_user.company_id, skip=skip, limit=limit)


@router.get("/{category_id}", response_model=CategoryResponse, summary="Obtener categoría por ID")
async def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    category = CategoryRepository(db).get(category_id)
    if not category or category.company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")
    return category


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, summary="Crear categoría")
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = CategoryRepository(db)
    existing = repo.get_by_name(current_user.company_id, category_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una categoría con el nombre '{category_data.name}'"
        )
    new_category = Category(**category_data.model_dump(), company_id=current_user.company_id)
    return repo.create(new_category)


@router.put("/{category_id}", response_model=CategoryResponse, summary="Actualizar categoría")
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = CategoryRepository(db)
    category = repo.get(category_id)
    if not category or category.company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")

    if category_data.name is not None and category_data.name != category.name:
        existing = repo.get_by_name(current_user.company_id, category_data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una categoría con el nombre '{category_data.name}'"
            )

    for key, value in category_data.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
    return repo.update(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar categoría")
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = CategoryRepository(db)
    category = repo.get(category_id)
    if not category or category.company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")
    repo.delete(category)
    return None
