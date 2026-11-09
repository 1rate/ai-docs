import uuid
from datetime import datetime, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.services.token_blacklist import is_access_token_blacklisted

bearer_scheme = HTTPBearer(auto_error=False)


def _extract_access_token(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    if bearer and bearer.credentials:
        return bearer.credentials
    return request.cookies.get(settings.access_cookie_name)


async def get_current_user(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = _extract_access_token(request, bearer)
    if not token:
        raise credentials_exception

    try:
        payload = decode_access_token(token)
        subject: Optional[str] = payload.get("sub")
        jti: Optional[str] = payload.get("jti")
        if subject is None or jti is None:
            raise credentials_exception
        user_id = uuid.UUID(subject)
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception from None

    if await is_access_token_blacklisted(jti):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


def get_token_expiry_from_access(token: str) -> datetime:
    payload = decode_access_token(token)
    exp = payload.get("exp")
    if isinstance(exp, datetime):
        return exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
    return datetime.fromtimestamp(int(exp), tz=timezone.utc)


def get_access_jti(token: str) -> str:
    payload = decode_access_token(token)
    jti = payload.get("jti")
    if not jti:
        raise ValueError("Missing jti")
    return str(jti)
