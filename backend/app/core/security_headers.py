"""Security headers middleware for FastAPI application.

This middleware adds security headers to all HTTP responses to protect against
common web vulnerabilities such as XSS, clickjacking, MIME type sniffing, etc.

Headers are configured to match the Caddyfile configuration for consistency.
"""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all HTTP responses.

    Adds the following security headers:
    - Content-Security-Policy: Restricts resource loading to prevent XSS
    - X-Frame-Options: Prevents clickjacking attacks
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-XSS-Protection: Enables XSS filter for legacy browsers
    - Strict-Transport-Security: Forces HTTPS (production only)
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Disables sensitive browser features

    CSP policy supports:
    - Google reCaptcha (script-src, frame-src)
    - Sentry error monitoring (connect-src)
    - Web Workers (worker-src blob:)
    - Vue.js inline styles (style-src 'unsafe-inline')
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """
        Process request and add security headers to response.

        Args:
            request: Starlette request object
            call_next: Next middleware/route handler

        Returns:
            Response with security headers added
        """
        response = await call_next(request)

        # Content Security Policy
        # Matches Caddyfile configuration for consistency
        csp_directives = [
            "default-src 'self'",
            # NOTE: 'unsafe-inline' intentionally omitted from script-src — it would
            # largely defeat CSP's XSS protection. reCAPTCHA/Sentry only need the
            # allow-listed hosts below, not inline scripts. 'unsafe-inline' remains
            # on style-src because Vue/shadcn emit inline styles.
            "script-src 'self' blob: https://www.google.com https://www.gstatic.com",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self' https://www.google.com https://*.sentry.io",
            "worker-src 'self' blob:",
            "frame-src 'self' https://www.google.com https://www.gstatic.com",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable XSS filter for legacy browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HTTP Strict Transport Security (HSTS) - production only
        # Force HTTPS for 1 year, include subdomains, allow preload listing
        if settings.is_production():
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Control information sent in Referer header
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy - disable sensitive features
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response
