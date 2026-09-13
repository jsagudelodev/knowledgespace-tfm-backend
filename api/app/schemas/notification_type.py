from pydantic import BaseModel
from typing import Optional


class NotificationTypeResponse(BaseModel):
    id: int
    name: str
    label: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}
