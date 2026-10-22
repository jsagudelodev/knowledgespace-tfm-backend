from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    widget_id = Column(String(36), nullable=True, index=True)
    assistant_id = Column(Integer, ForeignKey("assistants.id"), nullable=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True, index=True)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    comment = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="new", index=True)  # new | reviewed | converted | dismissed
    knowledge_gap_id = Column(Integer, ForeignKey("knowledge_gaps.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_feedback_message_user"),
        Index("ix_feedback_created_at", "created_at"),
    )

    # Relationships
    company = relationship("Company", backref="feedback")
    user = relationship("User", backref="feedback")
    assistant = relationship("Assistant", backref="feedback")
    message = relationship("Message", backref="feedback")
    knowledge_gap = relationship("KnowledgeGap", backref="feedback_items")

    def __repr__(self):
        return f"<Feedback(id={self.id}, user_id={self.user_id}, rating={self.rating}, status='{self.status}')>"
