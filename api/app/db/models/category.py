from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.db.types import IntBoolean


class Category(Base):
    __tablename__ = "categories"

    id         = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name       = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    color      = Column(String(7), nullable=True)
    icon       = Column(String(50), nullable=True)
    sort_order = Column(Integer, default=0)
    is_active  = Column(IntBoolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    company   = relationship("Company", backref="categories")
    documents = relationship("Document", back_populates="category")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', company_id={self.company_id})>"
