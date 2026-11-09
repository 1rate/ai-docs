from datetime import datetime, timezone

from fastapi import Response

from app.core.config import settings


def _cookie_kwargs() -> dict:
    params = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
    }
    if settings.cookie_domain:
        params["domain"] = settings.cookie_domain
    return params


def set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
    access_expires_at: datetime,
    refresh_expires_at: datetime,
) -> None:
    now = datetime.now(timezone.utc)
    if access_expires_at.tzinfo is None:
        access_expires_at = access_expires_at.replace(tzinfo=timezone.utc)
    if refresh_expires_at.tzinfo is None:
        refresh_expires_at = refresh_expires_at.replace(tzinfo=timezone.utc)

    common = _cookie_kwargs()
    response.set_cookie(
        key=settings.access_cookie_name,
        value=access_token,
        max_age=max(int((access_expires_at - now).total_seconds()), 0),
        path="/",
        **common,
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        max_age=max(int((refresh_expires_at - now).total_seconds()), 0),
        path="/api/v1/auth",
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    common = _cookie_kwargs()
    response.delete_cookie(
        key=settings.access_cookie_name,
        path="/",
        **common,
    )
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path="/api/v1/auth",
        **common,
    )
