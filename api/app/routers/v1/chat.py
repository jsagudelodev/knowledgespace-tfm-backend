"""Chat con el asistente: orquesta RAG (recuperación + generación), persiste
los mensajes con sus fuentes citadas y registra el costo de inferencia."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routers.v1.security import get_current_user
from app.db.models.assistant import Assistant
from app.db.models.user import User
from app.repositories.assistant_repository import AssistantRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_factory import crear_rag_service
from app.services.rag_service import RAGUnavailableError
from app.services.cost_tracking_service import CostTrackingService

router = APIRouter()


def _resolve_assistant(db: Session, company_id: int, assistant_id: Optional[int]) -> Optional[Assistant]:
    """
    Resuelve el asistente a usar: el solicitado explícitamente, o si no se
    especifica, el primero activo de la empresa. Si la empresa no tiene
    ningún asistente activo, se sigue permitiendo el chat con la
    configuración por defecto (namespace de empresa, prompt genérico).
    """
    repo = AssistantRepository(db)
    if assistant_id:
        assistant = repo.get_active_of_company(assistant_id, company_id)
        if not assistant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asistente no encontrado o inactivo")
        return assistant
    return repo.get_first_active(company_id)


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

    # El pipeline depende de dos servicios externos —OpenAI y Pinecone— que
    # pueden fallar por cuota, tiempo de espera o caída. Sin esta traducción, el
    # cliente recibía un 500 con la traza en lugar de un mensaje accionable.
    # Se responde 503 y no 500 porque el fallo es de disponibilidad y reintentar
    # tiene sentido; el detalle técnico queda en el log, no en la respuesta.
    #
    # El mensaje del usuario ya se guardó arriba y se conserva aunque esto
    # falle: la pregunta se hizo, y perderla haría que el reintento no tuviera
    # el historial completo.
    # Qué configuración atiende la consulta lo decide `RAG_CONFIGURACION`, no
    # este enrutador: las tres clases conviven y el chat no tiene por qué saber
    # cuál está activa. Ver `rag_factory` para el porqué de cada una.
    rag = crear_rag_service()
    try:
        result = rag.generate_response(
            query=payload.message,
            company_id=current_user.company_id,
            conversation_history=conversation_history,
            assistant_id=assistant.id if assistant else None,
            system_prompt_override=assistant.system_prompt if assistant else None,
            model_override=assistant.model if assistant else None,
            temperature_override=float(assistant.temperature) if assistant and assistant.temperature is not None else None,
        )
    except RAGUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "El asistente no está disponible en este momento "
                f"(falló la etapa: {e.etapa}). Vuelve a intentarlo en unos segundos."
            ),
        ) from e

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

    # Embeber la pregunta es una segunda llamada de pago a OpenAI, aparte de la
    # del modelo generativo. Se registra aparte para que `operation` distinga
    # ambas. El importe redondea a cero por la precisión de la columna
    # (Numeric(12,6)), pero los tokens quedan exactos: el costo real siempre es
    # recomputable a partir de ellos y del modelo, ambos almacenados.
    CostTrackingService(db).record(
        company_id=current_user.company_id,
        model=result["embedding_model"],
        operation="embedding",
        input_tokens=result["embedding_tokens"],
        user_id=current_user.id,
        conversation_id=conversation.id,
        assistant_id=assistant.id if assistant else None,
    )

    # Las configuraciones avanzadas llaman al modelo una vez más —para
    # descomponer la consulta o para reordenar los fragmentos— y esas llamadas
    # se facturan igual que las otras dos. Se registran con su propia
    # `operation` para que el desglose por tipo siga siendo legible y para
    # poder responder cuánto cuesta cada mejora, no solo si funciona.
    # En la configuración básica la lista viene vacía y este bucle no se ejecuta.
    for llamada in result.get("llamadas_auxiliares", []):
        CostTrackingService(db).record(
            company_id=current_user.company_id,
            model=llamada["modelo"],
            operation=llamada["operacion"],
            input_tokens=llamada["tokens_entrada"],
            output_tokens=llamada["tokens_salida"],
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
