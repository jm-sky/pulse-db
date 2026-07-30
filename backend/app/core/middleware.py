"""Middleware configuration for the application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.convert_empty_strings_middleware import (
    ConvertEmptyStringsToNoneMiddleware,
)
from app.core.csrf import CSRFMiddleware
from app.core.security_headers import SecurityHeadersMiddleware


def setup_middleware(app: FastAPI) -> None:
    """
    Configure middleware for the FastAPI application.

    Security middleware is configured based on environment:
    - Security Headers: Always enabled (CSP, X-Frame-Options, HSTS in production, etc.)
    - CORS: Always enabled with configurable origins (CORS_ORIGINS env var)
    - Trusted Host: Enabled in production with configurable hosts (ALLOWED_HOSTS env var)
    - CSRF: Double-submit cookie for unsafe methods (exempts Stripe webhooks)

    Args:
        app: FastAPI application instance
    """
    # Security Headers Middleware - always enabled (first in pipeline)
    # Adds CSP, X-Frame-Options, X-Content-Type-Options, HSTS (prod only), etc.
    # Headers match Caddyfile configuration for consistency
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS Middleware - always enabled
    # Configure via CORS_ORIGINS environment variable
    # Example: CORS_ORIGINS='["https://example.com","https://app.example.com"]'
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.server.cors_origins,
        allow_credentials=settings.server.cors_credentials,
        allow_methods=settings.server.cors_methods,
        allow_headers=settings.server.cors_headers,
    )

    # Trusted Host Middleware - production security
    # Prevents HTTP Host header attacks
    # Configure via ALLOWED_HOSTS environment variable
    # Example: ALLOWED_HOSTS='["example.com","*.example.com","api.example.com"]'
    if settings.is_production():
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.server.allowed_hosts,
        )

    # Convert Empty Strings to None Middleware
    # Automatically converts empty strings ('') to None (null in JSON) before Pydantic validation
    # Similar to Laravel's ConvertEmptyStringsToNull middleware
    app.add_middleware(ConvertEmptyStringsToNoneMiddleware)

    # CSRF double-submit (cookie + X-CSRF-Token). Added last → outermost on request.
    # Stripe webhooks are exempt (see WEBHOOK_PATHS). Safe methods skip validation.
    app.add_middleware(CSRFMiddleware)
