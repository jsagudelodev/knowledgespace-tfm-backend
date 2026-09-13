from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routers.v1.security import get_current_user
from app.db.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.message import MessageCreate, MessageResponse

router = APIRouter()


@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED, summary="Crear mensaje")
async def create_message(
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conversation = ConversationRepository(db).get_by_id_and_user(
        message_data.conversation_id, current_user.id
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")

    return MessageRepository(db).create_message(
        conversation_id=message_data.conversation_id,
        role=message_data.role,
        content=message_data.content,
        sources=message_data.sources,
        token_count=message_data.token_count,
    )


@router.get("/", response_model=List[MessageResponse], summary="Listar mensajes de una conversación")
async def list_messages(
    conversation_id: int = Query(..., description="ID de la conversación"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conversation = ConversationRepository(db).get_by_id_and_user(conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")

    return MessageRepository(db).get_by_conversation(conversation_id, skip=skip, limit=limit)
