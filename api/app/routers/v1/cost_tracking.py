"""Consulta del costo de inferencia acumulado (solo lectura, solo admin).
Los registros los escribe `CostTrackingService` desde el chat y la ingesta de
documentos — aquí solo se agregan y consultan."""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routers.v1.security import get_current_admin_user
from app.db.models.cost_tracking import CostTracking
from app.db.models.user import User
from app.db.models.document import Document
from app.db.models.assistant import Assistant
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
    query = (
        db.query(
            CostTracking,
            User.full_name.label("user_name"),
            Document.original_filename.label("document_name"),
            Assistant.name.label("assistant_name"),
        )
        .outerjoin(User, CostTracking.user_id == User.id)
        .outerjoin(Document, CostTracking.document_id == Document.id)
        .outerjoin(Assistant, CostTracking.assistant_id == Assistant.id)
        .filter(
            CostTracking.company_id == current_user.company_id,
            CostTracking.created_at >= _period_start(days),
        )
    )
    if model:
        query = query.filter(CostTracking.model == model)
    if assistant_id:
        query = query.filter(CostTracking.assistant_id == assistant_id)

    rows = query.order_by(CostTracking.created_at.desc()).offset(skip).limit(limit).all()

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
    base = db.query(CostTracking).filter(
        CostTracking.company_id == current_user.company_id,
        CostTracking.created_at >= _period_start(days),
    )
    rows = base.all()

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
    results = (
        db.query(
            func.date(CostTracking.created_at).label("date"),
            func.sum(CostTracking.total_cost).label("total_cost"),
            func.sum(CostTracking.input_tokens + CostTracking.output_tokens).label("total_tokens"),
            func.count(CostTracking.id).label("total_requests"),
        )
        .filter(
            CostTracking.company_id == current_user.company_id,
            CostTracking.created_at >= _period_start(days),
        )
        .group_by(func.date(CostTracking.created_at))
        .order_by(func.date(CostTracking.created_at).asc())
        .all()
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
