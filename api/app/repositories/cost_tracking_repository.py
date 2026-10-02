from datetime import datetime
from typing import Any, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.assistant import Assistant
from app.db.models.cost_tracking import CostTracking
from app.db.models.document import Document
from app.db.models.user import User
from app.repositories.base import BaseRepository


class CostTrackingRepository(BaseRepository[CostTracking]):
    """Acceso al registro de costo por solicitud al LLM.

    Todas las consultas filtran por `company_id` y por fecha de corte: el
    seguimiento de costo es por empresa y siempre se mira sobre un período.
    """

    def __init__(self, db: Session):
        super().__init__(CostTracking, db)

    def list_detailed(
        self,
        company_id: int,
        desde: datetime,
        model: Optional[str] = None,
        assistant_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Tuple[CostTracking, Any, Any, Any]]:
        """Registros del período junto al nombre de usuario, documento y
        asistente asociados.

        Los joins son `outer` porque las tres referencias son opcionales: una
        solicitud puede venir del pipeline de ingesta (sin usuario), no estar
        ligada a un documento, o usar la configuración por defecto sin
        asistente. Un `inner join` perdería esas filas en silencio.
        """
        query = (
            self.db.query(
                CostTracking,
                User.full_name.label("user_name"),
                Document.original_filename.label("document_name"),
                Assistant.name.label("assistant_name"),
            )
            .outerjoin(User, CostTracking.user_id == User.id)
            .outerjoin(Document, CostTracking.document_id == Document.id)
            .outerjoin(Assistant, CostTracking.assistant_id == Assistant.id)
            .filter(
                CostTracking.company_id == company_id,
                CostTracking.created_at >= desde,
            )
        )
        if model:
            query = query.filter(CostTracking.model == model)
        if assistant_id:
            query = query.filter(CostTracking.assistant_id == assistant_id)

        return query.order_by(CostTracking.created_at.desc()).offset(skip).limit(limit).all()

    def get_period(self, company_id: int, desde: datetime) -> List[CostTracking]:
        """Registros en crudo del período. El agregado se hace en el router
        porque implica desglosar por modelo, que es presentación, no datos."""
        return (
            self.db.query(CostTracking)
            .filter(
                CostTracking.company_id == company_id,
                CostTracking.created_at >= desde,
            )
            .all()
        )

    def daily_totals(self, company_id: int, desde: datetime) -> List[Any]:
        """Costo, tokens y número de solicitudes agrupados por día."""
        return (
            self.db.query(
                func.date(CostTracking.created_at).label("date"),
                func.sum(CostTracking.total_cost).label("total_cost"),
                func.sum(CostTracking.input_tokens + CostTracking.output_tokens).label("total_tokens"),
                func.count(CostTracking.id).label("total_requests"),
            )
            .filter(
                CostTracking.company_id == company_id,
                CostTracking.created_at >= desde,
            )
            .group_by(func.date(CostTracking.created_at))
            .order_by(func.date(CostTracking.created_at))
            .all()
        )
