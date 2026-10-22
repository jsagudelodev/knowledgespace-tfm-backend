from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.services.cost_tracking_service import MODELOS_CHAT


def _validar_modelo(model: Optional[str]) -> Optional[str]:
    """Solo modelos con precio en `cost_tracking_service.PRICING`; si no, el
    costo de cada consulta se registraría con un precio que no es el suyo."""
    if model is not None and model not in MODELOS_CHAT:
        opciones = ", ".join(sorted(MODELOS_CHAT))
        raise ValueError(f"Modelo no soportado: {model}. Opciones: {opciones}")
    return model


class AssistantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model: str = Field(default="gpt-4o-mini")
    # Sin `temperature`: no es configurable por asistente. El chat usa siempre
    # `RAG_TEMPERATURA` (0), el valor medido en `rag_service.DEFAULT_TEMPERATURE`.
    # Mientras fue editable, el formulario enviaba 0.7 y anulaba esa decisión.
    avatar: Optional[str] = None
    quick_prompts: Optional[List[str]] = None


class AssistantCreate(AssistantBase):
    # La validación va en la entrada y no en `AssistantBase`: si fuera en la
    # base, `AssistantResponse` la heredaría y un asistente antiguo con un
    # modelo fuera de la lista dejaría de poder leerse.
    _modelo_con_precio = field_validator("model")(_validar_modelo)


class AssistantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    avatar: Optional[str] = None
    is_active: Optional[bool] = None
    quick_prompts: Optional[List[str]] = None

    _modelo_con_precio = field_validator("model")(_validar_modelo)


class AssistantResponse(AssistantBase):
    id: int
    company_id: int
    is_active: bool
    document_count: int = 0
    widget_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
