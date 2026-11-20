from unittest.mock import AsyncMock, patch

import pytest
from app.core.rate_limit import enforce_rate_limit
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_enforce_rate_limit_allows_within_window() -> None:
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()
    with patch("app.core.rate_limit.get_redis", return_value=redis):
        await enforce_rate_limit(key="rate:test:1", limit=2, window_seconds=60)
    redis.incr.assert_awaited_once_with("rate:test:1")
    redis.expire.assert_awaited_once_with("rate:test:1", 60)


@pytest.mark.asyncio
async def test_enforce_rate_limit_blocks_when_exceeded() -> None:
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=3)
    redis.ttl = AsyncMock(return_value=42)
    with (
        patch("app.core.rate_limit.get_redis", return_value=redis),
        pytest.raises(HTTPException) as exc_info,
    ):
        await enforce_rate_limit(key="rate:test:1", limit=2, window_seconds=60)
    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["Retry-After"] == "42"
