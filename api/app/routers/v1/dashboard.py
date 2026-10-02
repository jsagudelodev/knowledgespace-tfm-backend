"""Métricas agregadas de la empresa para la pantalla de inicio.

Todas las consultas se filtran por el `company_id` del usuario autenticado,
nunca por un parámetro del request: es el mismo aislamiento multi-tenant que
aplican el resto de routers (ver `security.get_current_user`).
"""
from typing import Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.user import User
from app.repositories.document_repository import DocumentRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.user_repository import UserRepository
from app.routers.v1.security import get_current_user
from app.schemas.dashboard import CountMetric, DashboardMetrics, DocumentMetrics

router = APIRouter()


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

    por_estado = DocumentRepository(db).count_grouped_by_status(company_id)

    return DashboardMetrics(
        documents=_metricas_de_documentos(por_estado),
        users=CountMetric(total=UserRepository(db).count_by_company(company_id)),
        messages=CountMetric(total=MessageRepository(db).count_by_company(company_id)),
    )
