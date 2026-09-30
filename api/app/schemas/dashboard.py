from datetime import datetime
from typing import List

from pydantic import BaseModel


class DocumentMetrics(BaseModel):
    """Documentos de la empresa, desglosados por estado de procesamiento."""

    total: int
    completed: int
    processing: int


class CountMetric(BaseModel):
    """Métrica de un solo número, envuelta para poder crecer sin romper el
    contrato del frontend (p. ej. añadir `activos` junto a `total`)."""

    total: int


class RecentActivityItem(BaseModel):
    id: int
    title: str
    updated_at: datetime


class DashboardMetrics(BaseModel):
    documents: DocumentMetrics
    users: CountMetric
    conversations: CountMetric
    messages: CountMetric
    recent_activity: List[RecentActivityItem]
