from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TagCreate(BaseModel):
    name:  str            = Field(..., min_length=2, max_length=100)
    color: Optional[str]  = Field(None, max_length=20)


class TagUpdate(BaseModel):
    name:  Optional[str] = Field(None, min_length=2, max_length=100)
    color: Optional[str] = Field(None, max_length=20)


class TagResponse(BaseModel):
    id:         int
    company_id: int
    name:       str
    color:      Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
