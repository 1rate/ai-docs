import asyncio
import logging
import uuid

from app.db.session import AsyncSessionLocal
from app.models.enums import DocumentStatus
from app.services.indexing import get_document_or_none, index_document
from app.services.queue import dequeue_document_indexing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("indexer")


async def process_document(document_id: str) -> None:
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        logger.warning("Invalid document id in queue: %s", document_id)
        return

    async with AsyncSessionLocal() as db:
        document = await get_document_or_none(db, doc_uuid)
        if document is None:
            logger.info("Document %s missing, skip", document_id)
            return

        document.status = DocumentStatus.processing
        document.error_message = None
        await db.commit()

        try:
            logger.info("Indexing %s (%s)", document.id, document.filename)
            chunk_count = await index_document(db, document)
            document.status = DocumentStatus.ready
            document.error_message = None
            await db.commit()
            logger.info("Document %s ready, chunks=%s", document.id, chunk_count)
        except Exception as exc:
            await db.rollback()
            document = await get_document_or_none(db, doc_uuid)
            if document is not None:
                document.status = DocumentStatus.failed
                document.error_message = str(exc)[:2000]
                await db.commit()
            logger.exception("Failed to index %s", document_id)


async def run_worker() -> None:
    logger.info("Indexer worker started")
    while True:
        document_id = await dequeue_document_indexing(timeout_seconds=5)
        if document_id is None:
            continue
        await process_document(document_id)


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
