
from sqlalchemy import Boolean, Column, Integer, Numeric, String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

class Assistant(Base):
    __tablename__ = "assistants"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)
    model = Column(String(50), default="gpt-4o-mini", nullable=False)
    temperature = Column(Numeric(3, 2), default=0.7, nullable=False)
    avatar = Column(String(255), nullable=True)
    quick_prompts = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    company = relationship("Company", backref="assistants")
    documents = relationship("Document", back_populates="assistant")
    widgets = relationship("Widget", back_populates="assistant")

    def __repr__(self):
        return f"<Assistant(id={self.id}, name='{self.name}', company_id={self.company_id})>"
