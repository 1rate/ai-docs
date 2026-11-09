import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_token,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User


@dataclass
class IssuedTokens:
    access_token: str
    refresh_token: str
    access_jti: str
    access_expires_at: datetime
    refresh_expires_at: datetime


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


async def issue_tokens(db: AsyncSession, user: User) -> IssuedTokens:
    access_token, access_jti, access_expires_at = create_access_token(
        subject=str(user.id),
        role=user.role.value,
    )
    raw_refresh = generate_refresh_token()
    refresh_expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    db.add(
        RefreshToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            expires_at=refresh_expires_at,
        )
    )
    await db.commit()
    return IssuedTokens(
        access_token=access_token,
        refresh_token=raw_refresh,
        access_jti=access_jti,
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
    )


async def rotate_refresh_token(
    db: AsyncSession,
    *,
    raw_refresh_token: str,
) -> tuple[IssuedTokens, User]:
    token_hash = hash_token(raw_refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if stored is None:
        raise ValueError("Invalid refresh token")
    if stored.revoked_at is not None:
        raise ValueError("Refresh token revoked")
    if _as_utc(stored.expires_at) <= now:
        raise ValueError("Refresh token expired")

    user_result = await db.execute(select(User).where(User.id == stored.user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise ValueError("User inactive")

    access_token, access_jti, access_expires_at = create_access_token(
        subject=str(user.id),
        role=user.role.value,
    )
    new_raw_refresh = generate_refresh_token()
    refresh_expires_at = now + timedelta(days=settings.refresh_token_expire_days)
    new_row = RefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_token(new_raw_refresh),
        expires_at=refresh_expires_at,
    )
    stored.revoked_at = now
    db.add(new_row)
    await db.flush()
    stored.replaced_by = new_row.id
    await db.commit()

    issued = IssuedTokens(
        access_token=access_token,
        refresh_token=new_raw_refresh,
        access_jti=access_jti,
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
    )
    return issued, user


async def revoke_refresh_token(db: AsyncSession, raw_refresh_token: str) -> bool:
    token_hash = hash_token(raw_refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()
    if stored is None:
        return False
    if stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
        await db.commit()
    return True
