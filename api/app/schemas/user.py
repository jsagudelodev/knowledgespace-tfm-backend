

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field



class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    role: Literal["superadmin", "admin", "user"] = "user"
    



class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    company_id: int

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[Literal["superadmin", "admin", "user"]] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)


class ProfileUpdate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)


class ChangePassword(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class AdminPasswordReset(BaseModel):
    new_password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    company_id: int
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}