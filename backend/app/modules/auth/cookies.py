"""HttpOnly cookie helpers for the refresh token."""

from fastapi import Request, Response

from ...core.config import settings
from ...core.csrf import get_cookie_security_settings

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth"


def set_refresh_cookie(request: Request, response: Response, refresh_token: str) -> None:
    """Attach the refresh token to the response as an HttpOnly cookie."""
    secure, same_site = get_cookie_security_settings(request)
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite=same_site,
        path=REFRESH_COOKIE_PATH,
        max_age=settings.security.refresh_token_expires_days * 86400,
    )


def clear_refresh_cookie(request: Request, response: Response) -> None:
    """Remove the refresh token cookie (logout / invalidated session)."""
    secure, same_site = get_cookie_security_settings(request)
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=secure,
        samesite=same_site,
    )
