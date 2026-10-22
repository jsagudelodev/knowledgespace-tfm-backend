from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name:        str           = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color:       Optional[str] = Field(None, max_length=20)
    icon:        Optional[str] = Field(None, max_length=50)
    sort_order:  int           = Field(0, ge=0)


class CategoryUpdate(BaseModel):
    name:        Optional[str]  = Field(None, min_length=2, max_length=100)
    description: Optional[str]  = Field(None, max_length=500)
    color:       Optional[str]  = Field(None, max_length=20)
    icon:        Optional[str]  = Field(None, max_length=50)
    sort_order:  Optional[int]  = Field(None, ge=0)
    is_active:   Optional[bool] = None


class CategoryResponse(BaseModel):
    id:          int
    company_id:  int
    name:        str
    description: Optional[str]  = None
    color:       Optional[str]  = None
    icon:        Optional[str]  = None
    sort_order:  int
    is_active:   bool
    created_at:  datetime
    updated_at:  Optional[datetime] = None

    model_config = {"from_attributes": True}
