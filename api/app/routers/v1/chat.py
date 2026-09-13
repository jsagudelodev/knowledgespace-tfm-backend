"""Chat con el asistente: orquesta RAG (recuperación + generación), persiste
los mensajes con sus fuentes citadas y registra el costo de inferencia."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routers.v1.security import get_current_user
from app.db.models.assistant import Assistant
from app.db.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_service import RAGService
from app.services.cost_tracking_service import CostTrackingService

router = APIRouter()


def _resolve_assistant(db: Session, company_id: int, assistant_id: Optional[int]) -> Optional[Assistant]:
    """
    Resuelve el asistente a usar: el solicitado explícitamente, o si no se
    especifica, el primero activo de la empresa. Si la empresa no tiene
    ningún asistente activo, se sigue permitiendo el chat con la
    configuración por defecto (namespace de empresa, prompt genérico).
    """
    query = db.query(Assistant).filter(
        Assistant.company_id == company_id,
        Assistant.deleted_at.is_(None),
        Assistant.is_active.is_(True),
    )
    if assistant_id:
        assistant = query.filter(Assistant.id == assistant_id).first()
        if not assistant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asistente no encontrado o inactivo")
        return assistant
    return query.order_by(Assistant.created_at.asc()).first()


@router.post("/message", response_model=ChatResponse, summary="Enviar mensaje al chat IA")
async def chat_message(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assistant = _resolve_assistant(db, current_user.company_id, payload.assistant_id)

    conv_repo = ConversationRepository(db)
    if payload.conversation_id:
        conversation = conv_repo.get_by_id_and_user(payload.conversation_id, current_user.id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")
    else:
        conversation = conv_repo.create_for_user(
            company_id=current_user.company_id,
            user_id=current_user.id,
            title=payload.message[:50],
        )

    msg_repo = MessageRepository(db)

    # Historial ANTES de agregar el mensaje actual, para no duplicarlo en el prompt
    history = msg_repo.get_by_conversation(conversation.id, skip=0, limit=20)
    conversation_history = [{"role": m.role, "content": m.content} for m in history]

    msg_repo.create_message(conversation_id=conversation.id, role="user", content=payload.message)

    rag = RAGService()
    result = rag.generate_response(
        query=payload.message,
        company_id=current_user.company_id,
        conversation_history=conversation_history,
        assistant_id=assistant.id if assistant else None,
        system_prompt_override=assistant.system_prompt if assistant else None,
        model_override=assistant.model if assistant else None,
        temperature_override=float(assistant.temperature) if assistant and assistant.temperature is not None else None,
    )

    assistant_message = msg_repo.create_message(
        conversation_id=conversation.id,
        role="assistant",
        content=result["content"],
        sources=result["sources"],
        token_count=result.get("token_count"),
    )

    cost_usd = CostTrackingService(db).record(
        company_id=current_user.company_id,
        model=result["model"],
        operation="chat",
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        user_id=current_user.id,
        conversation_id=conversation.id,
        assistant_id=assistant.id if assistant else None,
    )

    return ChatResponse(
        message_id=assistant_message.id,
        conversation_id=conversation.id,
        role="assistant",
        content=assistant_message.content,
        sources=result["sources"],
        created_at=assistant_message.created_at,
        assistant_id=assistant.id if assistant else None,
        cost_usd=cost_usd,
    )
