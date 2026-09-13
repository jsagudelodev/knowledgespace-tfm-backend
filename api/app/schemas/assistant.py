from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AssistantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model: str = Field(default="gpt-4o-mini")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    avatar: Optional[str] = None
    quick_prompts: Optional[List[str]] = None


class AssistantCreate(AssistantBase):
    pass


class AssistantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    avatar: Optional[str] = None
    is_active: Optional[bool] = None
    quick_prompts: Optional[List[str]] = None


class AssistantResponse(AssistantBase):
    id: int
    company_id: int
    is_active: bool
    document_count: int = 0
    widget_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
