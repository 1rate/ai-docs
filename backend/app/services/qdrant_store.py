from functools import lru_cache
from typing import Any, Optional
from uuid import UUID

from qdrant_client import AsyncQdrantClient, models

from app.core.config import settings


@lru_cache
def get_qdrant_client() -> AsyncQdrantClient:
    kwargs: dict[str, Any] = {
        "url": settings.qdrant_url,
        "check_compatibility": False,
    }
    if settings.qdrant_api_key:
        kwargs["api_key"] = settings.qdrant_api_key
    return AsyncQdrantClient(**kwargs)


async def ensure_collection() -> None:
    client = get_qdrant_client()
    exists = await client.collection_exists(settings.qdrant_collection)
    if exists:
        return
    await client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=models.VectorParams(
            size=settings.embedding_dimensions,
            distance=models.Distance.COSINE,
        ),
    )
    await client.create_payload_index(
        collection_name=settings.qdrant_collection,
        field_name="document_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )


async def upsert_chunks(
    *,
    document_id: UUID,
    chunk_ids: list[UUID],
    contents: list[str],
    embeddings: list[list[float]],
    chunk_indexes: list[int],
) -> None:
    await ensure_collection()
    points = [
        models.PointStruct(
            id=str(chunk_id),
            vector=embedding,
            payload={
                "document_id": str(document_id),
                "chunk_id": str(chunk_id),
                "chunk_index": chunk_index,
                "content": content,
            },
        )
        for chunk_id, content, embedding, chunk_index in zip(
            chunk_ids,
            contents,
            embeddings,
            chunk_indexes,
        )
    ]
    await get_qdrant_client().upsert(
        collection_name=settings.qdrant_collection,
        points=points,
    )


async def delete_by_document_id(document_id: UUID) -> None:
    client = get_qdrant_client()
    exists = await client.collection_exists(settings.qdrant_collection)
    if not exists:
        return
    await client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=str(document_id)),
                    )
                ]
            )
        ),
    )


async def search_similar(
    query_embedding: list[float],
    *,
    limit: int = 5,
    document_id: Optional[UUID] = None,
) -> list[models.ScoredPoint]:
    await ensure_collection()
    query_filter = None
    if document_id is not None:
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=str(document_id)),
                )
            ]
        )
    result = await get_qdrant_client().query_points(
        collection_name=settings.qdrant_collection,
        query=query_embedding,
        limit=limit,
        query_filter=query_filter,
        with_payload=True,
    )
    return list(result.points)


async def ping() -> None:
    await get_qdrant_client().get_collections()
