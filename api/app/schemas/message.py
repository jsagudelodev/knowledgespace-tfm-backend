from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


class MessageCreate(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    conversation_id: int
    sources: Optional[List[Dict[str, Any]]] = None
    token_count: Optional[int] = None


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    token_count: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}
