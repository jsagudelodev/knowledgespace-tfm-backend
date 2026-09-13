from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


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