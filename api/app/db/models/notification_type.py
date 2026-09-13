from sqlalchemy import Column, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class NotificationType(Base):
    __tablename__ = "notification_types"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(50), nullable=False, unique=True, index=True)  # slug: "document_ready"
    label       = Column(String(120), nullable=False)                          # "Documento listo"
    description = Column(Text, nullable=True)
    icon        = Column(String(50), nullable=True)                            # "bell", "file-check"
    color       = Column(String(7), nullable=True)                             # "#3B82F6"
    is_active   = Column(Boolean, nullable=False, default=True)

    notifications = relationship("Notification", back_populates="notification_type")

    def __repr__(self):
        return f"<NotificationType(id={self.id}, name='{self.name}')>"
