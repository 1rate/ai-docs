from typing import Callable

from fastapi import HTTPException, Request, status

from app.services.queue import get_redis


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


async def enforce_rate_limit(*, key: str, limit: int, window_seconds: int) -> None:
    redis = get_redis()
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window_seconds)
    if count > limit:
        ttl = await redis.ttl(key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(max(ttl, 1))},
        )


def rate_limit_by_ip(scope: str, *, limit: int, window_seconds: int) -> Callable:
    async def dependency(request: Request) -> None:
        key = f"rate:{scope}:{client_ip(request)}"
        await enforce_rate_limit(
            key=key,
            limit=limit,
            window_seconds=window_seconds,
        )

    return dependency
