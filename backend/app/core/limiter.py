"""Rate limiting configuration."""

from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings


def get_client_ip(request: Request) -> str:
    """
    Get client IP address with support for proxy headers.

    Checks X-Forwarded-For and X-Real-IP headers commonly used by reverse proxies.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address
    """
    # Check proxy headers first
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs. The leftmost entries are
        # client-supplied and untrusted (an attacker can send a fresh fake one
        # per request to dodge rate limits). We deploy behind exactly one
        # trusted reverse proxy (Caddy), which appends the real connecting IP
        # as the last hop, so that's the only entry we can trust.
        return forwarded_for.split(",")[-1].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct client IP
    return get_remote_address(request)


# Create limiter instance at module level
class _NoOpLimiter:
    def limit(self, *_: Any, **__: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func

        return decorator


_limiter: Limiter | _NoOpLimiter
if settings.rate_limit.enabled:
    _limiter = Limiter(key_func=get_client_ip)
else:
    _limiter = _NoOpLimiter()

limiter: Limiter | _NoOpLimiter = _limiter


def setup_limiter(app: FastAPI) -> None:
    """
    Configure rate limiting for the application.

    Args:
        app: FastAPI application instance
    """
    if settings.rate_limit.enabled:
        app.state.limiter = limiter
        app.add_exception_handler(
            RateLimitExceeded,
            lambda request, exc: _rate_limit_exceeded_handler(request, exc),
        )


def rate_limit(limit_string: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for rate limiting FastAPI endpoints.

    Usage:
        @rate_limit("5/minute")
        async def my_endpoint():
            ...

    Args:
        limit_string: Rate limit string (e.g., "5/minute", "100/hour")

    Returns:
        Decorated function with rate limiting applied
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Apply slowapi's limit decorator unless disabled
        decorated_func = limiter.limit(limit_string)(func)

        @wraps(decorated_func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await decorated_func(*args, **kwargs)

        return wrapper

    return decorator


# Custom rate limit exceeded handler (optional, for custom responses)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.

    Args:
        request: FastAPI request object
        exc: RateLimitExceeded exception

    Returns:
        JSON response with rate limit details
    """
    content = {"detail": f"Rate limit exceeded: {exc.detail}"}
    headers = {}

    # Safely handle retry_after
    if hasattr(exc, "retry_after") and exc.retry_after is not None:
        content["retry_after"] = exc.retry_after
        headers["Retry-After"] = str(exc.retry_after)

    return JSONResponse(status_code=429, content=content, headers=headers)
