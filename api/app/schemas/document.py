from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator

from app.schemas.mensajes_documento import mensaje_legible


class DocumentStatus(str, Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"


class DocumentUpdate(BaseModel):
    filename: Optional[str] = None
    original_filename: Optional[str] = None
    page_count: Optional[int] = None
    chunk_count: Optional[int] = None
    status: Optional[DocumentStatus] = None
    error_message: Optional[str] = None
    category_id: Optional[int] = None
    assistant_id: Optional[int] = None


class DocumentResponse(BaseModel):
    id: int
    company_id: Optional[int] = None
    uploaded_by: Optional[int] = None
    category_id: Optional[int] = None
    assistant_id: Optional[int] = None
    filename: Optional[str] = None
    original_filename: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    page_count: Optional[int] = None
    chunk_count: int
    status: DocumentStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    # El error original se queda en la base de datos y en el log; al usuario le
    # llega qué pasó y qué hacer. Ver `mensajes_documento.py`.
    @field_validator("error_message")
    @classmethod
    def _legible(cls, v: Optional[str]) -> Optional[str]:
        return mensaje_legible(v)