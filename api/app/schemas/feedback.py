from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, List, Literal, Optional

FeedbackStatus = Literal["new", "reviewed", "converted", "dismissed", "stale"]
FeedbackPeriod = Literal["month", "90d", "12m"]


class FeedbackCreate(BaseModel):
    assistant_id: Optional[int] = None
    message_id: Optional[int] = None
    widget_id: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class FeedbackUpdate(BaseModel):
    status: FeedbackStatus
    knowledge_gap_id: Optional[int] = None


class FeedbackConvertGap(BaseModel):
    question: str


class FeedbackResponse(BaseModel):
    id: int
    company_id: int
    user_id: Optional[int] = None
    widget_id: Optional[str] = None
    assistant_id: Optional[int] = None
    message_id: Optional[int] = None
    rating: int
    comment: Optional[str] = None
    status: str = "new"
    knowledge_gap_id: Optional[int] = None
    knowledge_gap_status: Optional[str] = None  # 'open' | 'resolved' | 'ignored'
    created_at: datetime
    # enriched at query time
    assistant_name: Optional[str] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    conversation_id: Optional[int] = None
    sources_count: Optional[int] = None
    rag_score: Optional[float] = None
    user_full_name: Optional[str] = None

    model_config = {"from_attributes": True}


class WeekStats(BaseModel):
    week: str
    avg: float


class ThemeCount(BaseModel):
    label: str
    count: int


class SignalBand(BaseModel):
    copied: float = 0.0        # % "Copió o siguió adelante"
    source_opened: float = 0.0 # % "Abrió la fuente citada"
    reformulated: float = 0.0  # % "Reformuló la pregunta"
    abandoned: float = 0.0     # % "Se fue sin más"


class FeedbackStats(BaseModel):
    # KPI 1 – Satisfacción
    average_rating: float
    average_rating_delta: Optional[float] = None

    # KPI 2 – Respuestas calificadas
    rated_count: int
    messages_count: int
    rated_pct: float

    # KPI 3 – Negativas
    negatives: int

    # KPI 4 – En seguimiento
    with_gap: int

    # Para filtros y distribución
    total: int
    thumbs_up: int
    thumbs_down: int
    satisfaction_rate: float
    distribution: Dict[int, int]

    # Banda de señal implícita (requiere tabla message_events; retorna ceros hasta implementar)
    signal_band: SignalBand = Field(default_factory=SignalBand)

    # Temas en quejas
    themes: List[ThemeCount] = []

    # Semanal — retenido para compatibilidad, no se muestra en UI
    weeks: List[WeekStats] = []
