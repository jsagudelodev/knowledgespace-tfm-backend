from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.routers.v1.security import get_current_user
from app.schemas.conversation import ConversationCreateRequest, ConversationResponse, ConversationUpdateRequest

router = APIRouter()


@router.post(
    "/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED, summary="Crear conversación"
)
async def create_conversation(
    conversation_data: ConversationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ConversationRepository(db).create_for_user(
        company_id=current_user.company_id,
        user_id=current_user.id,
        title=conversation_data.title,
    )


@router.get("/", response_model=List[ConversationResponse], summary="Listar conversaciones del usuario")
async def list_conversations(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ConversationRepository(db).get_by_user(current_user.id, skip=skip, limit=limit)


@router.get("/{conversation_id}", response_model=ConversationResponse, summary="Obtener conversación por ID")
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = ConversationRepository(db).get_by_id_and_user(conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")
    return conversation


@router.put("/{conversation_id}", response_model=ConversationResponse, summary="Actualizar conversación")
async def update_conversation(
    conversation_id: int,
    conversation_data: ConversationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = ConversationRepository(db)
    conversation = repo.get_by_id_and_user(conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")
    for field, value in conversation_data.model_dump(exclude_unset=True).items():
        setattr(conversation, field, value)
    return repo.update(conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar conversación")
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = ConversationRepository(db)
    conversation = repo.get_by_id_and_user(conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")
    repo.delete(conversation)
    return None
