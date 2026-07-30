"""Double-submit CSRF protection for cookie-authenticated browser clients.

The SPA sends the non-HttpOnly ``csrf_token`` cookie value in the
``X-CSRF-Token`` header on unsafe methods. Middleware rejects mismatches.

Exempt: safe methods (GET/HEAD/OPTIONS) and Stripe webhook paths (signature
auth, no browser cookie). OAuth callback / WebAuthn / 2FA / refresh are
SPA-initiated and must send the header like any other mutation — they are
not exempted.
"""

from __future__ import annotations

import hmac
from collections.abc import Awaitable, Callable
from secrets import token_urlsafe
from typing import Literal
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

try:
    from app.modules.billing.constants import WEBHOOK_PATHS
except ImportError:
    WEBHOOK_PATHS = []

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_COOKIE_PATH = "/"

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
type CookieSameSite = Literal["lax", "strict", "none"]


def get_cookie_security_settings(request: Request) -> tuple[bool, CookieSameSite]:
    """Choose cookie attributes that work for same-origin and cross-origin SPAs.

    For the default same-origin deployment we keep ``SameSite=Strict``.
    If the request comes from another origin, browsers require
    ``SameSite=None; Secure`` for the cookie to be sent back on XHR/fetch.
    """
    origin = request.headers.get("origin")
    if origin:
        parsed_origin = urlparse(origin)
        if parsed_origin.hostname and parsed_origin.hostname != request.url.hostname:
            return True, "none"

    return settings.is_production(), "strict"


def set_csrf_cookie(request: Request, response: Response, token: str) -> None:
    """Attach the CSRF cookie (readable by JS for the double-submit header)."""
    secure, same_site = get_cookie_security_settings(request)
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,
        secure=secure,
        samesite=same_site,
        path=CSRF_COOKIE_PATH,
        max_age=60 * 60 * 24 * 7,
    )


def _is_webhook_path(path: str) -> bool:
    return any(path.startswith(webhook_path) for webhook_path in WEBHOOK_PATHS)


def _tokens_match(header_token: str | None, cookie_token: str | None) -> bool:
    if not header_token or not cookie_token:
        return False
    return hmac.compare_digest(header_token, cookie_token)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Validate double-submit CSRF on unsafe HTTP methods; issue cookie if missing."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.method not in _SAFE_METHODS and not _is_webhook_path(request.url.path):
            header_token = request.headers.get(CSRF_HEADER_NAME)
            cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
            if not _tokens_match(header_token, cookie_token):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF token missing or invalid"},
                )

        issued_token = None
        if CSRF_COOKIE_NAME not in request.cookies:
            issued_token = token_urlsafe(32)
            request.state.csrf_token = issued_token

        response = await call_next(request)

        if issued_token is not None:
            set_csrf_cookie(request, response, issued_token)

        return response
