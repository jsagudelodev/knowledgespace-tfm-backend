from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ConversationCreateRequest(BaseModel):
    title: str = "Nueva Conversación"


class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: int
    title: str
    company_id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

