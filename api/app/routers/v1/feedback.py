"""Calificación de las respuestas del asistente (1-5 estrellas) y su analítica.
Una calificación negativa puede convertirse en una pregunta sin respuesta
(`convert-gap`), cerrando el ciclo entre "esto salió mal" y trabajo pendiente."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.conversation import Conversation
from app.db.models.feedback import Feedback
from app.db.models.message import Message
from app.db.models.notification import NotificationEntityType
from app.db.models.user import User
from app.repositories.feedback_repository import FeedbackRepository
from app.routers.v1.security import get_current_user
from app.schemas.feedback import (
    FeedbackConvertGap,
    FeedbackCreate,
    FeedbackResponse,
    FeedbackStats,
    FeedbackUpdate,
)
from app.services.notification_service import NotificationService

router = APIRouter()

VALID_PERIODS = {"month", "90d", "12m"}


def _validate_period(period: str) -> str:
    if period not in VALID_PERIODS:
        return "month"
    return period


def _asistente_del_mensaje(db: Session, message_id: Optional[int], company_id: int) -> Optional[int]:
    """El asistente que de verdad respondió el mensaje calificado.

    Antes se usaba el que mandaba la pantalla —el seleccionado al calificar—, y
    en una conversación reabierta ese no tiene por qué ser el que respondió: la
    pregunta sin respuesta derivada acababa en otro espacio de conocimiento.
    Solo se acepta un mensaje de la propia empresa; si no, o si es anterior a
    que se guardara el asistente (NULL), se vuelve al valor de la pantalla.
    """
    if not message_id:
        return None
    fila = (
        db.query(Message.assistant_id)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .filter(Message.id == message_id, Conversation.company_id == company_id)
        .first()
    )
    return fila[0] if fila else None


@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED, summary="Enviar feedback")
async def submit_feedback(
    data: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    feedback = Feedback(
        company_id=current_user.company_id,
        user_id=current_user.id,
        widget_id=data.widget_id,
        assistant_id=_asistente_del_mensaje(db, data.message_id, current_user.company_id) or data.assistant_id,
        message_id=data.message_id,
        rating=data.rating,
        comment=data.comment,
    )
    return FeedbackRepository(db).create(feedback)


@router.get("/me", response_model=List[FeedbackResponse], summary="Listar mi propio feedback")
async def list_my_feedback(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return FeedbackRepository(db).get_by_user(current_user.id)


@router.get("/stats", response_model=FeedbackStats, summary="Estadísticas de feedback de la empresa")
async def get_feedback_stats(
    assistant_id: Optional[int] = Query(None),
    period: str = Query("month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return FeedbackRepository(db).get_stats(
        current_user.company_id,
        assistant_id=assistant_id,
        period=_validate_period(period),
    )


@router.get("/export", summary="Exportar feedback a CSV")
async def export_feedback(
    assistant_id: Optional[int] = Query(None),
    period: str = Query("month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    csv_content = FeedbackRepository(db).get_export_csv(
        current_user.company_id,
        assistant_id=assistant_id,
        period=_validate_period(period),
    )
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=feedback.csv"},
    )


@router.get("/", response_model=List[FeedbackResponse], summary="Listar feedback de la empresa")
async def list_feedback(
    assistant_id: Optional[int] = Query(None),
    rating: Optional[int] = Query(None, ge=1, le=5),
    period: str = Query("month"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return FeedbackRepository(db).get_by_company(
        current_user.company_id,
        assistant_id=assistant_id,
        rating=rating,
        period=_validate_period(period),
        skip=skip,
        limit=limit,
    )


@router.get("/{feedback_id}", response_model=FeedbackResponse, summary="Obtener feedback por ID")
async def get_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    feedback = FeedbackRepository(db).get_of_company(feedback_id, current_user.company_id)
    if not feedback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback no encontrado")
    return feedback


@router.patch("/{feedback_id}/status", response_model=FeedbackResponse, summary="Actualizar estado del feedback")
async def update_feedback_status(
    feedback_id: int,
    data: FeedbackUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    feedback = FeedbackRepository(db).get_of_company(feedback_id, current_user.company_id)
    if not feedback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback no encontrado")
    feedback.status = data.status
    if data.knowledge_gap_id is not None:
        feedback.knowledge_gap_id = data.knowledge_gap_id
    db.commit()
    db.refresh(feedback)
    return feedback


@router.post("/{feedback_id}/convert-gap", response_model=FeedbackResponse, summary="Enviar a preguntas sin respuesta")
async def convert_to_gap(
    feedback_id: int,
    data: FeedbackConvertGap,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = FeedbackRepository(db)
    feedback = repo.get_of_company(feedback_id, current_user.company_id)
    if not feedback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback no encontrado")
    if feedback.knowledge_gap_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Este feedback ya tiene una pregunta sin respuesta asociada"
        )
    gap = repo.convert_to_gap(
        feedback=feedback,
        question=data.question,
        company_id=current_user.company_id,
        user_id=current_user.id,
    )

    import logging
    try:
        NotificationService(db).create_for_admins(
            company_id=current_user.company_id,
            type_name="knowledge_gap_found",
            title="Brecha de conocimiento",
            message=f'Nueva pregunta sin responder: "{gap.question[:120]}"',
            entity_type=NotificationEntityType.KNOWLEDGE_GAP,
            entity_id=gap.id,
        )
    except Exception:
        logging.getLogger("uvicorn.error").warning(
            f"[Notification] No se pudo crear notificación 'knowledge_gap_found' para gap_id={gap.id}",
            exc_info=True,
        )

    # El `feedback` de arriba (de `get_of_company`) nunca pasó por el
    # enriquecimiento (`question`, `answer`, `assistant_name`...): esos
    # campos son atributos calculados en memoria, no columnas de la tabla, y
    # solo `get_by_company`/`_enrich` los rellenan. Sin esto, el frontend
    # reemplaza la fila entera con esta respuesta
    # (`feedback-list.component.ts`) y la deja sin pregunta, sin la
    # respuesta citada ni el nombre del asistente hasta que se recarga la
    # página — verificado contra un feedback real antes de corregirlo.
    repo._enrich([feedback])
    return feedback
