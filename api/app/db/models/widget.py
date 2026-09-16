import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Widget(Base):
    __tablename__ = "widgets"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name       = Column(String(255), nullable=False)
    is_active  = Column(Boolean, default=True)

    # Posición y tamaño
    position    = Column(String(20), default="bottom-right")  # bottom-right, bottom-left
    widget_size = Column(String(20), default="medium")        # small, medium, large

    # Apariencia (JSONB)
    theme_config = Column(JSON, default=lambda: {
        "primary_color":    "#0052CC",
        "chat_bg_color":    "#FFFFFF",
        "bot_bubble_color": "#F4F5F7",
        "user_bubble_color":"#0052CC",
        "bot_text_color":   "#172B4D",
        "user_text_color":  "#FFFFFF",
        "placeholder_text": "Escribe tu consulta aquí...",
        "welcome_message":  "¡Hola! ¿En qué puedo ayudarte hoy?",
        "font_family":      "Inter, sans-serif",
        "border_radius":    "12px",
    })

    # Identidad del bot (presentación — el modelo/prompt/documentos viven en
    # el Assistant enlazado, el widget solo los hereda, no los duplica)
    bot_name        = Column(String(100), default="Asistente Virtual")
    bot_avatar_url  = Column(Text, nullable=True)
    company_logo_url = Column(Text, nullable=True)

    # Respuestas rápidas sugeridas
    quick_replies = Column(JSON, default=list)

    # Idioma
    default_language    = Column(String(5), default="es")
    supported_languages = Column(JSON, default=lambda: ["es", "en"])

    # Límites (rate-limiting de acceso público/anónimo — el Assistant, al
    # estar detrás de JWT, no lo necesita)
    daily_message_limit = Column(Integer, default=100)

    # Todo widget representa el despliegue público de UN asistente — sin
    # asistente no hay modelo, prompt ni documentos que consultar, así que
    # el enlace es obligatorio (antes era nullable con SET NULL, permitiendo
    # un widget "huérfano" con su propia config duplicada; corregido para
    # que herede siempre del Assistant, sin duplicación).
    assistant_id = Column(Integer, ForeignKey("assistants.id", ondelete="CASCADE"), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    company   = relationship("Company", backref="widgets")
    assistant = relationship("Assistant", back_populates="widgets")

    def __repr__(self):
        return f"<Widget(id={self.id}, name='{self.name}', company_id={self.company_id})>"
