from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.tag import Tag
from app.db.models.user import User
from app.repositories.tag_repository import TagRepository
from app.routers.v1.security import get_current_user
from app.schemas.tag import TagCreate, TagResponse, TagUpdate

router = APIRouter()


@router.get("/", response_model=List[TagResponse], summary="Listar etiquetas de la empresa")
async def list_tags(
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return TagRepository(db).get_by_company(current_user.company_id, skip=skip, limit=limit)


@router.get("/search", response_model=List[TagResponse], summary="Buscar etiquetas por nombre")
async def search_tags(
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return TagRepository(db).search_by_name(current_user.company_id, name)


@router.get("/{tag_id}", response_model=TagResponse, summary="Obtener etiqueta por ID")
async def get_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tag = TagRepository(db).get_of_company(tag_id, current_user.company_id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etiqueta no encontrada")
    return tag


@router.post("/", response_model=TagResponse, status_code=status.HTTP_201_CREATED, summary="Crear etiqueta")
async def create_tag(
    tag_data: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = TagRepository(db)
    existing = repo.get_by_name(current_user.company_id, tag_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una etiqueta con el nombre '{tag_data.name}'"
        )
    new_tag = Tag(name=tag_data.name, color=tag_data.color, company_id=current_user.company_id)
    return repo.create(new_tag)


@router.put("/{tag_id}", response_model=TagResponse, summary="Actualizar etiqueta")
async def update_tag(
    tag_id: int,
    tag_update: TagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = TagRepository(db)
    tag = repo.get_of_company(tag_id, current_user.company_id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etiqueta no encontrada")

    if tag_update.name is not None and tag_update.name != tag.name:
        existing = repo.get_by_name(current_user.company_id, tag_update.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una etiqueta con el nombre '{tag_update.name}'"
            )
        tag.name = tag_update.name

    if tag_update.color is not None:
        tag.color = tag_update.color

    return repo.update(tag)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar etiqueta")
async def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = TagRepository(db)
    tag = repo.get_of_company(tag_id, current_user.company_id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etiqueta no encontrada")
    repo.delete(tag)
    return None
