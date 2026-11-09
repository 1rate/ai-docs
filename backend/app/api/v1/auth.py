from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_access_jti,
    get_current_user,
    get_token_expiry_from_access,
)
from app.core.config import settings
from app.core.cookies import clear_auth_cookies, set_auth_cookies
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import LoginRequest, MessageResponse, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.auth_session import (
    issue_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.services.token_blacklist import blacklist_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookies(response: Response, issued) -> None:
    set_auth_cookies(
        response,
        access_token=issued.access_token,
        refresh_token=issued.refresh_token,
        access_expires_at=issued.access_expires_at,
        refresh_expires_at=issued.refresh_expires_at,
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> User:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email.lower(),
        first_name=body.first_name.strip(),
        last_name=body.last_name.strip() if body.last_name else None,
        hashed_password=hash_password(body.password),
        role=UserRole.user,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    issued = await issue_tokens(db, user)
    _set_session_cookies(response, issued)
    return TokenResponse(
        access_token=issued.access_token,
        refresh_token=issued.refresh_token,
        access_expires_at=issued.access_expires_at,
        refresh_expires_at=issued.refresh_expires_at,
    )


@router.post("/login/form", response_model=TokenResponse)
async def login_form(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    return await login(
        LoginRequest(email=form_data.username, password=form_data.password),
        response,
        db,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    raw_refresh: Optional[str] = request.cookies.get(settings.refresh_cookie_name)
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )
    try:
        issued, _user = await rotate_refresh_token(db, raw_refresh_token=raw_refresh)
    except ValueError as exc:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    _set_session_cookies(response, issued)
    return TokenResponse(
        access_token=issued.access_token,
        refresh_token=issued.refresh_token,
        access_expires_at=issued.access_expires_at,
        refresh_expires_at=issued.refresh_expires_at,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    access_token = request.cookies.get(settings.access_cookie_name)
    auth_header = request.headers.get("Authorization")
    if not access_token and auth_header and auth_header.lower().startswith("bearer "):
        access_token = auth_header.split(" ", 1)[1].strip()

    if access_token:
        try:
            jti = get_access_jti(access_token)
            expires_at = get_token_expiry_from_access(access_token)
            await blacklist_access_token(jti=jti, expires_at=expires_at)
        except (jwt.PyJWTError, ValueError):
            pass

    raw_refresh = request.cookies.get(settings.refresh_cookie_name)
    if raw_refresh:
        await revoke_refresh_token(db, raw_refresh)

    clear_auth_cookies(response)
    return MessageResponse(detail="Logged out")


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
