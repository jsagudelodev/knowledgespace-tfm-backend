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


class DashboardMetrics(BaseModel):
    """Lo que muestra el panel de inicio: documentos, usuarios y mensajes.

    No incluye conversaciones ni actividad reciente a propósito. Abrir el chat
    crea una conversación aunque no se pregunte nada, así que el recuento no
    medía uso real y el listado de actividad se llenaba de conversaciones
    vacías. Los mensajes sí reflejan uso.
    """

    documents: DocumentMetrics
    users: CountMetric
    messages: CountMetric
