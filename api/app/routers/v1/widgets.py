from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routers.v1.security import get_current_user
from app.db.models.user import User
from app.db.models.widget import Widget
from app.repositories.widget_repository import WidgetRepository
from app.schemas.widget import WidgetCreate, WidgetUpdate, WidgetResponse

router = APIRouter()


@router.post("/", response_model=WidgetResponse, status_code=status.HTTP_201_CREATED, summary="Crear widget")
async def create_widget(
    data: WidgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    widget_data = data.model_dump()
    widget_data["company_id"] = current_user.company_id
    return WidgetRepository(db).create(Widget(**widget_data))


@router.get("/", response_model=List[WidgetResponse], summary="Listar widgets")
async def list_widgets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return WidgetRepository(db).get_by_company(current_user.company_id, skip=skip, limit=limit)


@router.get("/{widget_id}", response_model=WidgetResponse, summary="Obtener widget")
async def get_widget(
    widget_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    widget = WidgetRepository(db).get(widget_id)
    if not widget or widget.company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget no encontrado")
    return widget


@router.put("/{widget_id}", response_model=WidgetResponse, summary="Actualizar widget")
async def update_widget(
    widget_id: UUID,
    data: WidgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = WidgetRepository(db)
    widget = repo.get(widget_id)
    if not widget or widget.company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget no encontrado")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(widget, key, value)
    return repo.update(widget)


@router.delete("/{widget_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar widget")
async def delete_widget(
    widget_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = WidgetRepository(db)
    widget = repo.get(widget_id)
    if not widget or widget.company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget no encontrado")
    repo.delete(widget)
    return None
