from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class NotificationEntityType(str, PyEnum):
    DOCUMENT      = "document"
    BUDGET_LIMIT  = "budget_limit"
    KNOWLEDGE_GAP = "knowledge_gap"


class Notification(Base):
    __tablename__ = "notifications"

    id         = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    type_id    = Column(Integer, ForeignKey("notification_types.id"), nullable=False, index=True)

    title   = Column(String(120), nullable=False)
    message = Column(Text, nullable=False)

    entity_type = Column(
        Enum(NotificationEntityType, values_callable=lambda obj: [e.value for e in obj]), nullable=True
    )
    entity_id   = Column(Integer, nullable=True)

    read    = Column(Boolean, nullable=False, default=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    company           = relationship("Company", backref="notifications")
    user              = relationship("User", backref="notifications")
    notification_type = relationship("NotificationType", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(id={self.id}, type_id={self.type_id}, read={self.read})>"
