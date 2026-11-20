import uuid
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    filename: str
    storage_key: str
    file_hash: str
    size_bytes: int
    mime_type: str
    status: DocumentStatus
    error_message: Optional[str]
    doc_type: Optional[str] = None
    doc_number: Optional[str] = None
    doc_date: Optional[date] = None
    jurisdiction: Optional[str] = None
    official_url: Optional[str] = None
    description: Optional[str] = None
    page_count: Optional[int] = None
    chunk_count: int = 0
    language: str = "ru"
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")
    uploaded_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class DocumentUpdate(BaseModel):
    doc_type: Optional[str] = Field(default=None, max_length=50)
    doc_number: Optional[str] = Field(default=None, max_length=100)
    doc_date: Optional[date] = None
    jurisdiction: Optional[str] = Field(default=None, max_length=100)
    official_url: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = Field(default=None, max_length=10)


class DocumentListResponse(BaseModel):
    items: list[DocumentRead]
    total: int
    page: int
    page_size: int


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    status: DocumentStatus = Field(description="pending until worker indexes")
