from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class CostTracking(Base):
    __tablename__ = "cost_tracking"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    assistant_id = Column(Integer, ForeignKey("assistants.id", ondelete="SET NULL"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)

    model = Column(String(50), nullable=False, index=True)  # 'gpt-4o-mini', 'text-embedding-3-small', etc.
    operation = Column(String(20), nullable=False, default="chat")  # chat | embedding
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    total_cost = Column(Numeric(12, 6), nullable=False)  # USD

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    company = relationship("Company", backref="cost_records")
    user = relationship("User", backref="cost_records")
    conversation = relationship("Conversation", backref="cost_records")
    assistant = relationship("Assistant", backref="cost_records")
    document = relationship("Document", backref="cost_records")

    def __repr__(self):
        return f"<CostTracking(id={self.id}, model='{self.model}', total_cost={self.total_cost})>"
