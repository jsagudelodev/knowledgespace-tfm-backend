from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id          = Column(Integer, primary_key=True, index=True)
    company_id  = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    assistant_id = Column(Integer, ForeignKey("assistants.id"), nullable=True)

    filename          = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path         = Column(String, nullable=False)
    file_size         = Column(BigInteger, nullable=True)
    mime_type         = Column(String, nullable=True)

    page_count    = Column(Integer, nullable=True)
    chunk_count   = Column(Integer, nullable=False, default=0)
    status        = Column(String, nullable=False, default="pending")
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    company  = relationship("Company", backref="documents")
    uploader = relationship("User", foreign_keys=[uploaded_by], backref="uploaded_documents")
    category = relationship("Category", back_populates="documents")
    assistant = relationship("Assistant", back_populates="documents")

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.original_filename}', status='{self.status}')>"
