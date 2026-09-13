from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class KnowledgeGap(Base):
    __tablename__ = "knowledge_gaps"
    __table_args__ = (
        Index("ix_knowledge_gaps_company_status_created", "company_id", "status", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    widget_id = Column(String(36), nullable=True, index=True)
    assistant_id = Column(Integer, ForeignKey("assistants.id", ondelete="SET NULL"), nullable=True, index=True)

    question = Column(Text, nullable=False)
    sources_count = Column(Integer, default=0)
    rag_score = Column(Float, nullable=True)
    gap_type = Column(String(20), nullable=False, default="hard")  # hard | soft

    status = Column(String(20), nullable=False, default="open", index=True)  # open | in_progress | resolved | ignored
    answer_text = Column(Text, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)

    # Ignore
    ignore_reason = Column(String(30), nullable=True)  # out_of_scope | one_off | duplicate

    # Request document (in_progress state)
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    requested_at = Column(DateTime(timezone=True), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    note = Column(Text, nullable=True)

    # Recurrence tracking
    recurrence_count = Column(Integer, default=0)
    reopened_at = Column(DateTime(timezone=True), nullable=True)

    # Verification post-resolution
    verify_score_before = Column(Float, nullable=True)
    verify_score_after = Column(Float, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verify_passed = Column(Boolean, nullable=True)

    # Semantic grouping / enriched data (JSONB — populated by background jobs)
    variants = Column(JSONB, nullable=True)   # [{text: str, count: int}]
    candidates = Column(JSONB, nullable=True)  # [{document_id: int, chunk_id: int, name: str, score: float}]

    # Priority calculation inputs
    volume = Column(Integer, default=1)
    channel = Column(String(20), nullable=True)   # widget | chat
    trend = Column(String(20), nullable=True)      # rising | stable | declining

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    company = relationship("Company", backref="knowledge_gaps")
    user = relationship("User", foreign_keys=[user_id], backref="knowledge_gaps_reported")
    conversation = relationship("Conversation", backref="knowledge_gaps")
    resolver = relationship("User", foreign_keys=[resolved_by], backref="knowledge_gaps_resolved")
    assignee = relationship("User", foreign_keys=[assigned_to], backref="knowledge_gaps_assigned")
    resolved_document = relationship("Document", foreign_keys=[resolved_document_id], backref="knowledge_gaps_linked")

    def __repr__(self):
        return f"<KnowledgeGap(id={self.id}, gap_type='{self.gap_type}', status='{self.status}')>"
