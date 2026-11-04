"""Preguntas sin respuesta: convierte lo que el asistente no supo responder en
conocimiento indexado. Dos vías de resolución (vincular documento existente,
escribir respuesta) y verificación automática contra el índice al resolver,
para demostrar que la pregunta ahora sí se responde.

"Pedir documento" (asignar la pregunta a una persona y dejarla "en curso") se
retiró el 2026-11-03: el administrador resuelve respondiendo o con un documento,
y una tercera vía que no resolvía nada confundía. Las columnas `assigned_to` y
`requested_at` se conservan en el modelo; una pregunta que quedara `in_progress`
se sigue listando y resolviendo como abierta."""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.assistant import Assistant
from app.db.models.document import Document
from app.db.models.knowledge_gap import KnowledgeGap
from app.db.models.notification import NotificationEntityType
from app.db.models.user import User
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_gap_repository import KnowledgeGapRepository
from app.routers.v1.security import get_current_admin_user, get_current_user
from app.schemas.knowledge_gap import (
    KnowledgeGapAnswerRequest,
    KnowledgeGapIgnoreRequest,
    KnowledgeGapLinkRequest,
    KnowledgeGapResponse,
    KnowledgeGapSummary,
)
from app.services.knowledge_gap_index_service import best_score, index_alias, index_answer
from app.services.notification_service import NotificationService

# Todo el módulo es de administración: lista las preguntas de todos los usuarios
# y sus resoluciones escriben en la base de conocimiento que reciben todos. Antes
# cualquier usuario podía, p. ej., indexar una respuesta escrita a mano.
router = APIRouter(dependencies=[Depends(get_current_admin_user)])

PAGE_SIZE = 25
VALID_STATUSES = {"open", "resolved", "ignored"}
VALID_REASONS = {"out_of_scope", "one_off", "duplicate"}
VERIFY_THRESHOLD = 0.7


def _enrich(gap: KnowledgeGap, db: Session) -> KnowledgeGapResponse:
    """
    Convierte el registro de BD en la respuesta de la API, resolviendo los IDs
    a nombres legibles (asistente y documento con el que se resolvió).

    La pantalla muestra "Vinculado a «Manual de RRHH»", no "documento 42", y
    hacerlo aquí evita que el frontend tenga que pedir cada nombre por
    separado. Cada lookup es tolerante a nulos: los IDs son FKs con SET NULL,
    así que un documento o usuario borrado deja el nombre en None en vez de
    romper la respuesta.
    """
    assistant_name = None
    if gap.assistant_id:
        a = db.get(Assistant, gap.assistant_id)
        if a:
            assistant_name = a.name

    resolved_document_name = None
    if gap.resolved_document_id:
        d = db.get(Document, gap.resolved_document_id)
        if d:
            resolved_document_name = d.original_filename or d.filename

    data = {c.name: getattr(gap, c.name) for c in gap.__table__.columns}
    data["assistant_name"] = assistant_name
    data["resolved_document_name"] = resolved_document_name
    return KnowledgeGapResponse(**data)


def _base(db: Session, company_id: int):
    return KnowledgeGapRepository(db).query_by_company(company_id)


def _get_or_404(db: Session, gap_id: int, company_id: int) -> KnowledgeGap:
    gap = KnowledgeGapRepository(db).get_of_company(gap_id, company_id)
    if not gap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pregunta no encontrada")
    return gap


def _notify_resolved(db: Session, gap: KnowledgeGap) -> None:
    """Avisa a los admins de que una pregunta sin respuesta se resolvió. Efecto secundario —
    no debe romper el flujo de resolución si falla."""
    import logging
    try:
        NotificationService(db).create_for_admins(
            company_id=gap.company_id,
            type_name="knowledge_gap_resolved",
            title="Pregunta resuelta",
            message=f'Se resolvió: "{gap.question[:120]}"',
            entity_type=NotificationEntityType.KNOWLEDGE_GAP,
            entity_id=gap.id,
        )
    except Exception:
        logging.getLogger("uvicorn.error").warning(
            f"[Notification] No se pudo crear notificación 'knowledge_gap_resolved' para gap_id={gap.id}",
            exc_info=True,
        )


def _auto_verify(gap: KnowledgeGap) -> None:
    """Reejecuta la pregunta contra el índice en el momento de resolver, para
    que "resuelto" venga con la prueba de que ahora responde (decisión de
    diseño #3 del handoff: resolver no es cerrar, es demostrar que funciona).
    Efecto secundario — si falla, el gap queda "sin verificar" y admite
    reintento manual vía /verify; no debe romper la resolución."""
    import logging
    try:
        gap.verify_score_before = gap.rag_score or 0.0
        gap.verify_score_after = best_score(gap.question, gap.company_id, gap.assistant_id)
        gap.verify_passed = gap.verify_score_after >= VERIFY_THRESHOLD
        gap.verified_at = datetime.now(timezone.utc)
    except Exception:
        logging.getLogger("uvicorn.error").warning(
            f"[KnowledgeGap] No se pudo autoverificar gap_id={gap.id} al resolver",
            exc_info=True,
        )


def _period_cutoff(period: str) -> datetime:
    now = datetime.now(timezone.utc)
    if period == "90d":
        return now - timedelta(days=90)
    if period == "12m":
        return now - timedelta(days=365)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


@router.get("/summary", response_model=KnowledgeGapSummary, summary="Resumen de preguntas sin respuesta")
async def get_summary(
    period: str = Query("month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base = _base(db, current_user.company_id)
    cutoff = _period_cutoff(period)

    open_gaps = base.filter(KnowledgeGap.status.in_(["open", "in_progress"])).all()
    resolved_count = base.filter(KnowledgeGap.status == "resolved").count()
    ignored_count = base.filter(KnowledgeGap.status == "ignored").count()

    open_count = len(open_gaps)
    open_volume = sum(g.volume or 1 for g in open_gaps)

    resolved_this_period = base.filter(
        KnowledgeGap.status == "resolved",
        KnowledgeGap.resolved_at >= cutoff,
    ).count()

    all_gaps = base.all()
    total_volume = sum(g.volume or 1 for g in all_gaps)
    open_vol = sum(g.volume or 1 for g in all_gaps if g.status in ("open", "in_progress"))
    coverage_pct = round((total_volume - open_vol) / total_volume * 100, 1) if total_volume > 0 else 0.0

    return KnowledgeGapSummary(
        open_count=open_count,
        resolved_count=resolved_count,
        ignored_count=ignored_count,
        open_volume=open_volume,
        resolved_this_period=resolved_this_period,
        coverage_pct=coverage_pct,
    )


@router.get("/", response_model=List[KnowledgeGapResponse], summary="Listar preguntas sin respuesta")
async def list_gaps(
    status_filter: Optional[str] = Query(None, alias="status"),
    sort: str = Query("recent"),
    q: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(PAGE_SIZE, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = _base(db, current_user.company_id)

    if status_filter in VALID_STATUSES:
        if status_filter == "open":
            query = query.filter(KnowledgeGap.status.in_(["open", "in_progress"]))
        else:
            query = query.filter(KnowledgeGap.status == status_filter)

    if q:
        query = query.filter(KnowledgeGap.question.ilike(f"%{q}%"))

    # "recent": lo último que se preguntó, arriba. "impact": las más consultadas.
    if sort == "impact":
        query = query.order_by(KnowledgeGap.volume.desc(), KnowledgeGap.created_at.desc())
    else:
        query = query.order_by(KnowledgeGap.created_at.desc())

    gaps = query.offset(skip).limit(limit).all()
    return [_enrich(g, db) for g in gaps]


@router.get("/{gap_id}", response_model=KnowledgeGapResponse, summary="Detalle de una pregunta sin respuesta")
async def get_gap(
    gap_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    gap = _get_or_404(db, gap_id, current_user.company_id)
    return _enrich(gap, db)


@router.post(
    "/{gap_id}/link", response_model=KnowledgeGapResponse, summary="Vincular a documento existente y reindexar"
)
async def link_document(
    gap_id: int,
    data: KnowledgeGapLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    gap = _get_or_404(db, gap_id, current_user.company_id)
    if gap.status in ("resolved", "ignored"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La pregunta ya está cerrada")

    doc = DocumentRepository(db).get_of_company(data.document_id, current_user.company_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")

    alias_texts = [gap.question] + [
        v.get("text") for v in (gap.variants or [])[:3] if isinstance(v, dict) and v.get("text")
    ]
    try:
        index_alias(
            gap_id=gap.id,
            texts=alias_texts,
            document_id=doc.id,
            document_name=doc.original_filename or doc.filename,
            chunk_id=data.chunk_id,
            company_id=gap.company_id,
            assistant_id=gap.assistant_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo reindexar el alias en el índice. Intenta de nuevo.",
        ) from e

    now = datetime.now(timezone.utc)
    gap.status = "resolved"
    gap.resolved_document_id = data.document_id
    gap.resolved_by = current_user.id
    gap.resolved_at = now
    _auto_verify(gap)
    db.commit()
    db.refresh(gap)
    _notify_resolved(db, gap)
    return _enrich(gap, db)


@router.post("/{gap_id}/answer", response_model=KnowledgeGapResponse, summary="Resolver escribiendo respuesta directa")
async def write_answer(
    gap_id: int,
    data: KnowledgeGapAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    gap = _get_or_404(db, gap_id, current_user.company_id)
    if gap.status in ("resolved", "ignored"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La pregunta ya está cerrada")

    try:
        index_answer(
            gap_id=gap.id,
            question=gap.question,
            answer_text=data.answer_text,
            company_id=gap.company_id,
            assistant_id=gap.assistant_id,
            answered_by=current_user.id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo indexar la respuesta en el índice. Intenta de nuevo.",
        ) from e

    now = datetime.now(timezone.utc)
    gap.status = "resolved"
    gap.answer_text = data.answer_text
    gap.resolved_by = current_user.id
    gap.resolved_at = now
    _auto_verify(gap)
    db.commit()
    db.refresh(gap)
    _notify_resolved(db, gap)
    return _enrich(gap, db)


@router.post("/{gap_id}/ignore", response_model=KnowledgeGapResponse, summary="Ignorar con motivo obligatorio")
async def ignore_gap(
    gap_id: int,
    data: KnowledgeGapIgnoreRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.reason not in VALID_REASONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Motivo no válido. Opciones: {', '.join(VALID_REASONS)}",
        )

    gap = _get_or_404(db, gap_id, current_user.company_id)
    if gap.status in ("resolved", "ignored"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La pregunta ya está cerrada")

    gap.status = "ignored"
    gap.ignore_reason = data.reason
    db.commit()
    db.refresh(gap)
    return _enrich(gap, db)


@router.post("/{gap_id}/verify", response_model=KnowledgeGapResponse, summary="Reverificar resolución contra el índice")
async def verify_gap(
    gap_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    gap = _get_or_404(db, gap_id, current_user.company_id)
    if gap.status != "resolved":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo se pueden verificar preguntas resueltas")

    # Score antes: el que tenía la pregunta original al detectarse (baseline).
    if gap.verify_score_before is None:
        gap.verify_score_before = gap.rag_score or 0.0

    try:
        gap.verify_score_after = best_score(gap.question, gap.company_id, gap.assistant_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo reejecutar la verificación contra el índice. Intenta de nuevo.",
        ) from e

    now = datetime.now(timezone.utc)
    gap.verify_passed = (gap.verify_score_after or 0.0) >= VERIFY_THRESHOLD
    gap.verified_at = now
    db.commit()
    db.refresh(gap)
    return _enrich(gap, db)
