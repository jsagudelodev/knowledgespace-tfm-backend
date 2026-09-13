from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Literal, Optional


CompanyPlan = Literal["basic", "pro", "enterprise"]


class CompanyCreate(BaseModel):
    name:                  str       = Field(..., min_length=2, max_length=255)
    email:                 EmailStr
    phone:                 Optional[str] = Field(None, max_length=50)
    address:               Optional[str] = None
    plan:                  CompanyPlan   = "basic"
    max_users:             int       = Field(5,   ge=1)
    max_documents:         int       = Field(100, ge=1)
    monthly_message_limit: Optional[int] = Field(None, ge=1)


class CompanyUpdate(BaseModel):
    name:                  Optional[str]         = Field(None, min_length=2, max_length=255)
    email:                 Optional[EmailStr]    = None
    phone:                 Optional[str]         = Field(None, max_length=50)
    address:               Optional[str]         = None
    plan:                  Optional[CompanyPlan] = None
    max_users:             Optional[int]         = Field(None, ge=1)
    max_documents:         Optional[int]         = Field(None, ge=1)
    monthly_message_limit: Optional[int]         = Field(None, ge=1)
    is_active:             Optional[bool]        = None


class CompanyResponse(BaseModel):
    id:                    int
    name:                  str
    email:                 str
    phone:                 Optional[str]  = None
    address:               Optional[str]  = None
    plan:                  str
    max_users:             int
    max_documents:         int
    monthly_message_limit: Optional[int]  = None
    is_active:             bool
    created_at:            datetime
    updated_at:            Optional[datetime] = None

    model_config = {"from_attributes": True}
