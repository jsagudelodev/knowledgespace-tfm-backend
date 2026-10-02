"""Consulta del costo de inferencia acumulado (solo lectura, solo admin).
Los registros los escribe `CostTrackingService` desde el chat y la ingesta de
documentos — aquí solo se agregan y consultan."""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routers.v1.security import get_current_admin_user
from app.db.models.user import User
from app.repositories.cost_tracking_repository import CostTrackingRepository
from app.schemas.cost_tracking import (
    CostTrackingDetailResponse,
    CostSummary,
    CostByModel,
    CostTrendPoint,
)

router = APIRouter()


def _period_start(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


@router.get("/", response_model=List[CostTrackingDetailResponse], summary="Listar registros de costo")
async def list_cost_tracking(
    days: int = Query(30, ge=1, le=365),
    model: Optional[str] = Query(None),
    assistant_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    rows = CostTrackingRepository(db).list_detailed(
        company_id=current_user.company_id,
        desde=_period_start(days),
        model=model,
        assistant_id=assistant_id,
        skip=skip,
        limit=limit,
    )

    return [
        CostTrackingDetailResponse(
            **{c.name: getattr(cost, c.name) for c in cost.__table__.columns},
            user_name=user_name,
            document_name=document_name,
            assistant_name=assistant_name,
        )
        for cost, user_name, document_name, assistant_name in rows
    ]


@router.get("/summary", response_model=CostSummary, summary="Resumen de costo del período")
async def get_cost_summary(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    rows = CostTrackingRepository(db).get_period(
        current_user.company_id, _period_start(days)
    )

    total_cost = sum(float(r.total_cost) for r in rows)
    total_tokens = sum(r.input_tokens + r.output_tokens for r in rows)

    by_model: dict[str, dict] = {}
    for r in rows:
        acc = by_model.setdefault(r.model, {"total_cost": 0.0, "total_tokens": 0, "total_requests": 0})
        acc["total_cost"] += float(r.total_cost)
        acc["total_tokens"] += r.input_tokens + r.output_tokens
        acc["total_requests"] += 1

    return CostSummary(
        period_days=days,
        total_cost=round(total_cost, 6),
        total_tokens=total_tokens,
        total_requests=len(rows),
        by_model=[CostByModel(model=m, **v) for m, v in sorted(by_model.items(), key=lambda kv: -kv[1]["total_cost"])],
    )


@router.get("/daily-trend", response_model=List[CostTrendPoint], summary="Tendencia diaria de costo")
async def get_daily_trend(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    results = CostTrackingRepository(db).daily_totals(
        current_user.company_id, _period_start(days)
    )

    return [
        CostTrendPoint(
            date=str(row.date),
            total_cost=round(float(row.total_cost), 6),
            total_tokens=row.total_tokens,
            total_requests=row.total_requests,
        )
        for row in results
    ]
