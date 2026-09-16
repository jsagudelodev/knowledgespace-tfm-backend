from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_THEME_CONFIG = {
    "primary_color": "#0052CC",
    "chat_bg_color": "#FFFFFF",
    "bot_bubble_color": "#F4F5F7",
    "user_bubble_color": "#0052CC",
    "bot_text_color": "#172B4D",
    "user_text_color": "#FFFFFF",
    "placeholder_text": "Escribe tu consulta aquí...",
    "welcome_message": "¡Hola! ¿En qué puedo ayudarte hoy?",
    "font_family": "Inter, sans-serif",
    "border_radius": "12px",
}


class WidgetBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(..., min_length=1, max_length=255)
    is_active: bool = True
    position: str = "bottom-right"
    widget_size: str = "medium"
    theme_config: Dict[str, Any] = Field(default_factory=lambda: dict(DEFAULT_THEME_CONFIG))
    bot_name: str = "Asistente Virtual"
    bot_avatar_url: Optional[str] = None
    company_logo_url: Optional[str] = None
    quick_replies: List[str] = Field(default_factory=list)
    default_language: str = "es"
    supported_languages: List[str] = Field(default_factory=lambda: ["es", "en"])
    daily_message_limit: int = Field(default=100, gt=0)
    # Obligatorio: un widget es el despliegue público de UN asistente — sin
    # él no hay modelo/prompt/documentos que heredar (ver widget.py).
    assistant_id: int


class WidgetCreate(WidgetBase):
    pass


class WidgetUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None
    position: Optional[str] = None
    widget_size: Optional[str] = None
    theme_config: Optional[Dict[str, Any]] = None
    bot_name: Optional[str] = None
    bot_avatar_url: Optional[str] = None
    company_logo_url: Optional[str] = None
    quick_replies: Optional[List[str]] = None
    default_language: Optional[str] = None
    supported_languages: Optional[List[str]] = None
    daily_message_limit: Optional[int] = Field(None, gt=0)
    assistant_id: Optional[int] = None


class WidgetResponse(WidgetBase):
    id: UUID
    company_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
