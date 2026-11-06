import asyncio
import uuid
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.services import minio_storage
from app.services.chunking import split_text
from app.services.embeddings import embed_texts
from app.services.text_extract import extract_text


async def index_document(db: AsyncSession, document: Document) -> int:
    raw = await asyncio.to_thread(minio_storage.download_file, document.storage_key)
    text = await asyncio.to_thread(
        extract_text,
        raw=raw,
        content_type=document.content_type or "",
        filename=document.filename,
    )
    if not text.strip():
        raise ValueError("No extractable text in document")

    chunks = split_text(text)
    if not chunks:
        raise ValueError("No chunks produced from document")

    embeddings = await embed_texts(chunks)

    await db.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
    )

    for index, (content, embedding) in enumerate(zip(chunks, embeddings)):
        db.add(
            DocumentChunk(
                id=uuid.uuid4(),
                document_id=document.id,
                chunk_index=index,
                content=content,
                embedding=embedding,
            )
        )
    await db.flush()
    return len(chunks)


async def get_document_or_none(
    db: AsyncSession,
    document_id: uuid.UUID,
) -> Optional[Document]:
    result = await db.execute(select(Document).where(Document.id == document_id))
    return result.scalar_one_or_none()
