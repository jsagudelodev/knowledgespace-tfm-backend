from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from app.db.models.notification import NotificationEntityType  # noqa: F401 — re-exported for routers
from app.schemas.notification_type import NotificationTypeResponse


class NotificationCreate(BaseModel):
    company_id: int
    user_id: Optional[int] = None
    type_id: int
    title: str
    message: str
    entity_type: Optional[NotificationEntityType] = None
    entity_id: Optional[int] = None


class NotificationResponse(BaseModel):
    id: int
    company_id: int
    user_id: Optional[int] = None
    notification_type: NotificationTypeResponse
    title: str
    message: str
    entity_type: Optional[NotificationEntityType] = None
    entity_id: Optional[int] = None
    read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationUnreadCount(BaseModel):
    count: int


class NotificationCounts(BaseModel):
    todas: int
    unread: int
    documents: int
    budget: int
    knowledge_gap: int
