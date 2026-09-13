from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func

from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id                    = Column(Integer, primary_key=True, index=True)
    name                  = Column(String(255), nullable=False)
    email                 = Column(String(255), unique=True, nullable=False, index=True)
    phone                 = Column(String(50), nullable=True)
    address               = Column(Text, nullable=True)
    plan                  = Column(String(20), nullable=False, default="basic")
    max_users             = Column(Integer, nullable=False, default=5)
    max_documents         = Column(Integer, nullable=False, default=100)
    monthly_message_limit = Column(Integer, nullable=True)
    is_active             = Column(Boolean, nullable=False, default=True)
    created_at            = Column(DateTime(timezone=True), server_default=func.now())
    updated_at            = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Company(id={self.id}, name='{self.name}', plan='{self.plan}')>"
