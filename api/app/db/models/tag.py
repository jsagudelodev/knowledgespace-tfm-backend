from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from app.core.database import Base


class Tag(Base):
    # Módulo retirado el 2026-11-02 (ver ALCANCE_TFM.md): las etiquetas nunca se
    # vincularon a documentos y la categoría ya cubre la organización. Se
    # conserva solo el modelo para que Alembic no proponga borrar la tabla.
    __tablename__ = "tags"

    id         = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name       = Column(String(100), nullable=False)
    color      = Column(String(7), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Tag(id={self.id}, name='{self.name}', company_id={self.company_id})>"
