"""Métricas agregadas de la empresa para la pantalla de inicio.

Todas las consultas se filtran por el `company_id` del usuario autenticado,
nunca por un parámetro del request: es el mismo aislamiento multi-tenant que
aplican el resto de routers (ver `security.get_current_user`).
"""
from typing import Dict

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.conversation import Conversation
from app.db.models.document import Document
from app.db.models.message import Message
from app.db.models.user import User
from app.routers.v1.security import get_current_user
from app.schemas.dashboard import (
    CountMetric,
    DashboardMetrics,
    DocumentMetrics,
    RecentActivityItem,
)

router = APIRouter()

# Cuántas conversaciones recientes devuelve el panel de actividad.
RECENT_ACTIVITY_LIMIT = 10


def _documentos_por_estado(db: Session, company_id: int) -> Dict[str, int]:
    """Cuenta los documentos agrupados por estado en una sola consulta, en vez
    de lanzar una por estado."""
    filas = (
        db.query(Document.status, func.count(Document.id))
        .filter(Document.company_id == company_id)
        .group_by(Document.status)
        .all()
    )
    return {estado: total for estado, total in filas}


def _metricas_de_documentos(por_estado: Dict[str, int]) -> DocumentMetrics:
    """Traduce el recuento por estado a lo que muestra la tarjeta del panel.

    `total` suma todos los estados, incluidos los `failed`: son documentos que
    la empresa subió y que siguen ocupando sitio en la lista, aunque no se
    hayan indexado.

    `processing` agrupa `pending` y `processing`: un documento recién subido
    está en `pending` hasta que el worker lo toma, y para quien mira el panel
    ambos estados significan lo mismo — "todavía no puedo consultarlo".
    """
    return DocumentMetrics(
        total=sum(por_estado.values()),
        completed=por_estado.get("completed", 0),
        processing=por_estado.get("processing", 0) + por_estado.get("pending", 0),
    )


@router.get(
    "/metrics",
    response_model=DashboardMetrics,
    summary="Métricas agregadas de la empresa del usuario autenticado",
)
async def get_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_id = current_user.company_id

    documentos = _metricas_de_documentos(_documentos_por_estado(db, company_id))

    usuarios = (
        db.query(func.count(User.id)).filter(User.company_id == company_id).scalar() or 0
    )

    conversaciones = (
        db.query(func.count(Conversation.id))
        .filter(Conversation.company_id == company_id)
        .scalar()
        or 0
    )

    # Los mensajes no llevan company_id: se llega a la empresa por su
    # conversación, lo que además garantiza el filtrado multi-tenant.
    mensajes = (
        db.query(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.company_id == company_id)
        .scalar()
        or 0
    )

    # `updated_at` es NULL hasta la primera modificación (no tiene
    # server_default, solo onupdate), así que se cae a `created_at` para que
    # las conversaciones nuevas no queden al final del listado.
    ultima_actividad = func.coalesce(Conversation.updated_at, Conversation.created_at)
    recientes = (
        db.query(
            Conversation.id,
            Conversation.title,
            ultima_actividad.label("updated_at"),
        )
        .filter(Conversation.company_id == company_id)
        .order_by(ultima_actividad.desc())
        .limit(RECENT_ACTIVITY_LIMIT)
        .all()
    )

    return DashboardMetrics(
        documents=documentos,
        users=CountMetric(total=usuarios),
        conversations=CountMetric(total=conversaciones),
        messages=CountMetric(total=mensajes),
        recent_activity=[
            RecentActivityItem(id=c.id, title=c.title, updated_at=c.updated_at)
            for c in recientes
        ],
    )
