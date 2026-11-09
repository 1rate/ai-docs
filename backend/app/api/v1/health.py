from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.schemas.health import HealthResponse
from app.services import qdrant_store

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    checks = {}

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc.__class__.__name__}"

    try:
        await qdrant_store.ping()
        checks["qdrant"] = "ok"
    except Exception as exc:
        checks["qdrant"] = f"error: {exc.__class__.__name__}"

    status_value = "ok" if all(value == "ok" for value in checks.values()) else "degraded"

    return HealthResponse(
        status=status_value,
        app=settings.app_name,
        env=settings.app_env,
        checks=checks,
    )
