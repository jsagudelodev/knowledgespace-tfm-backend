from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class KnowledgeGapVariant(BaseModel):
    text: str
    count: int


class KnowledgeGapCandidate(BaseModel):
    document_id: int
    chunk_id: int
    name: str
    score: float


class KnowledgeGapSummary(BaseModel):
    open_count: int
    resolved_count: int
    ignored_count: int
    open_volume: int
    resolved_this_period: int
    coverage_pct: float


class KnowledgeGapResponse(BaseModel):
    id: int
    company_id: int
    user_id: Optional[int] = None
    conversation_id: Optional[int] = None
    widget_id: Optional[str] = None
    assistant_id: Optional[int] = None

    question: str
    sources_count: int = 0
    rag_score: Optional[float] = None
    gap_type: str

    status: str
    answer_text: Optional[str] = None
    resolved_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    resolved_document_id: Optional[int] = None

    ignore_reason: Optional[str] = None

    assigned_to: Optional[int] = None
    requested_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    note: Optional[str] = None

    recurrence_count: int = 0
    reopened_at: Optional[datetime] = None

    verify_score_before: Optional[float] = None
    verify_score_after: Optional[float] = None
    verified_at: Optional[datetime] = None
    verify_passed: Optional[bool] = None

    variants: Optional[List[KnowledgeGapVariant]] = None
    candidates: Optional[List[KnowledgeGapCandidate]] = None

    volume: int = 1
    channel: Optional[str] = None
    trend: Optional[str] = None

    created_at: datetime

    # Enriched fields
    assistant_name: Optional[str] = None
    resolved_document_name: Optional[str] = None
    assignee_name: Optional[str] = None

    model_config = {"from_attributes": True}


class KnowledgeGapLinkRequest(BaseModel):
    document_id: int
    chunk_id: int


class KnowledgeGapAnswerRequest(BaseModel):
    answer_text: str


class KnowledgeGapRequestDocumentRequest(BaseModel):
    assignee_id: Optional[int] = None
    note: Optional[str] = None
    due_days: int = 3


class KnowledgeGapIgnoreRequest(BaseModel):
    reason: str  # out_of_scope | one_off | duplicate
