from typing import List

import httpx

from app.core.config import settings


async def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY is not configured")

    url = settings.llm_api_base.rstrip("/") + "/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    vectors: List[List[float]] = []
    batch_size = 64
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await client.post(
                url,
                headers=headers,
                json={
                    "model": settings.embedding_model,
                    "input": batch,
                },
            )
            response.raise_for_status()
            payload = response.json()
            items = sorted(payload["data"], key=lambda item: item["index"])
            for item in items:
                vectors.append(item["embedding"])
    return vectors
