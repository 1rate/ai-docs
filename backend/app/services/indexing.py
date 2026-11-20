import asyncio
import hashlib
import uuid
from typing import Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.models.document_index_status import DocumentIndexStatus
from app.services import minio_storage, qdrant_store
from app.services.chunking import split_text
from app.services.embeddings import embed_texts
from app.services.text_extract import extract_text


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def index_document(db: AsyncSession, document: Document) -> int:
    raw = await asyncio.to_thread(minio_storage.download_file, document.storage_key)
    text = await asyncio.to_thread(
        extract_text,
        raw=raw,
        content_type=document.mime_type or "",
        filename=document.filename,
    )
    if not text.strip():
        raise ValueError("No extractable text in document")

    chunks = split_text(text)
    if not chunks:
        raise ValueError("No chunks produced from document")

    embeddings = await embed_texts(chunks)

    await qdrant_store.delete_by_document_id(document.id)
    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))

    chunk_ids: list[uuid.UUID] = []
    chunk_indexes: list[int] = []
    char_cursor = 0
    for index, content in enumerate(chunks):
        chunk_id = uuid.uuid4()
        chunk_ids.append(chunk_id)
        chunk_indexes.append(index)
        char_start = char_cursor
        char_end = char_start + len(content)
        char_cursor = char_end
        db.add(
            DocumentChunk(
                id=chunk_id,
                document_id=document.id,
                chunk_index=index,
                content=content,
                content_hash=_content_hash(content),
                token_count=len(content.split()),
                char_start=char_start,
                char_end=char_end,
                qdrant_point_id=chunk_id,
                embedding_model=settings.embedding_model,
            )
        )
    await db.flush()

    await qdrant_store.upsert_chunks(
        document_id=document.id,
        chunk_ids=chunk_ids,
        contents=chunks,
        embeddings=embeddings,
        chunk_indexes=chunk_indexes,
    )

    document.chunk_count = len(chunks)

    await db.execute(
        update(DocumentIndexStatus)
        .where(
            DocumentIndexStatus.document_id == document.id,
            DocumentIndexStatus.is_current.is_(True),
        )
        .values(is_current=False)
    )

    existing_status = await db.execute(
        select(DocumentIndexStatus).where(
            DocumentIndexStatus.document_id == document.id,
            DocumentIndexStatus.qdrant_collection == settings.qdrant_collection,
        )
    )
    status_row = existing_status.scalar_one_or_none()
    if status_row is not None:
        status_row.embedding_model = settings.embedding_model
        status_row.chunk_count = len(chunks)
        status_row.is_current = True
    else:
        db.add(
            DocumentIndexStatus(
                document_id=document.id,
                embedding_model=settings.embedding_model,
                qdrant_collection=settings.qdrant_collection,
                chunk_count=len(chunks),
                is_current=True,
            )
        )

    return len(chunks)


async def get_document_or_none(
    db: AsyncSession,
    document_id: uuid.UUID,
) -> Optional[Document]:
    result = await db.execute(select(Document).where(Document.id == document_id))
    return result.scalar_one_or_none()
