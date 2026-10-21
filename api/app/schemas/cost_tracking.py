from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CostTrackingResponse(BaseModel):
    id: int
    company_id: int
    user_id: Optional[int] = None
    conversation_id: Optional[int] = None
    assistant_id: Optional[int] = None
    document_id: Optional[int] = None
    model: str
    operation: str
    input_tokens: int
    output_tokens: int
    total_cost: float
    duration_ms: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CostTrackingDetailResponse(CostTrackingResponse):
    user_name: Optional[str] = None
    assistant_name: Optional[str] = None
    document_name: Optional[str] = None


class CostByModel(BaseModel):
    model: str
    total_cost: float
    total_tokens: int
    total_requests: int


class CostSummary(BaseModel):
    period_days: int
    total_cost: float
    total_tokens: int
    total_requests: int
    by_model: list[CostByModel]


class CostTrendPoint(BaseModel):
    date: str
    total_cost: float
    total_tokens: int
    total_requests: int
