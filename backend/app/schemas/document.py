import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    storage_key: str
    content_type: Optional[str]
    status: DocumentStatus
    error_message: Optional[str]
    uploaded_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: List[DocumentRead]
    total: int
    page: int
    page_size: int


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    status: DocumentStatus = Field(description="pending until worker indexes")
