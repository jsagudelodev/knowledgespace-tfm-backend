from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: Optional[int] = None
    assistant_id: Optional[int] = None


class ChatResponse(BaseModel):
    message_id: int
    conversation_id: int
    role: str
    content: str
    sources: List[Dict[str, Any]] = []
    created_at: datetime
    assistant_id: Optional[int] = None
    cost_usd: Optional[float] = None
