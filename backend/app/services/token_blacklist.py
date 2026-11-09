from datetime import datetime, timezone

from app.services.queue import get_redis

BLACKLIST_PREFIX = "auth:blacklist:"


async def blacklist_access_token(*, jti: str, expires_at: datetime) -> None:
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    ttl = int((expires_at - now).total_seconds())
    if ttl <= 0:
        return
    await get_redis().setex(f"{BLACKLIST_PREFIX}{jti}", ttl, "1")


async def is_access_token_blacklisted(jti: str) -> bool:
    return bool(await get_redis().exists(f"{BLACKLIST_PREFIX}{jti}"))
