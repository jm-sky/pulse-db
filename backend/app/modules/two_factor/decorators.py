"""Per-user rate limiting decorators for 2FA verification."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Any

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

# Simple in-memory store (for production: use Redis)
_verification_attempts: dict[str, list[datetime]] = {}
_lockouts: dict[str, datetime] = {}


def extract_user_from_token(request: Request) -> str | None:
    """Extract user_id from 2FA token in request body.

    Returns:
        User ID if successfully extracted from token, None otherwise.

    Note:
        This is a best-effort extraction for rate limiting purposes.
        Failures are logged but don't prevent the request from proceeding.
    """
    try:
        if hasattr(request, "_body") and request._body:
            body = request._body.decode() if isinstance(request._body, bytes) else request._body
            data = json.loads(body)
            token = data.get("twoFactorToken") or data.get("setupToken")
            if token:
                # Simple JWT decode (just to get user_id, not full verification)
                import jwt

                from app.core.config import settings

                payload: dict[str, Any] = jwt.decode(
                    token,
                    settings.security.secret_key,
                    algorithms=[settings.security.jwt_algorithm],
                    options={"verify_exp": False},
                )
                user_id = payload.get("sub")
                return str(user_id) if user_id else None
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        # Expected errors when parsing request body or token
        logger.debug(f"Could not extract user from token: {type(e).__name__}")
    except Exception as e:
        # Unexpected errors
        logger.warning(f"Unexpected error extracting user from token: {type(e).__name__}: {e}")
    return None


def require_2fa_rate_limit(max_attempts: int = 5, window_minutes: int = 15) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Per-user 2FA verification rate limiting decorator.

    Args:
        max_attempts: Maximum failed attempts before lockout
        window_minutes: Time window for counting attempts

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Find Request in kwargs or args
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                # Can't rate limit without request, proceed
                return await func(*args, **kwargs)

            # Extract user_id from token
            user_id = extract_user_from_token(request)
            if not user_id:
                # Can't identify user, proceed (global rate limit will catch abuse)
                return await func(*args, **kwargs)

            # Check if locked out
            now = datetime.now(UTC)
            if user_id in _lockouts:
                if now < _lockouts[user_id]:
                    remaining = (_lockouts[user_id] - now).total_seconds() / 60
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Too many failed attempts. Account temporarily locked. Try again in {int(remaining)} minutes.",
                    )
                else:
                    # Lockout expired
                    del _lockouts[user_id]
                    if user_id in _verification_attempts:
                        del _verification_attempts[user_id]

            # Track attempt
            if user_id not in _verification_attempts:
                _verification_attempts[user_id] = []

            # Clean old attempts outside window
            cutoff = now - timedelta(minutes=window_minutes)
            _verification_attempts[user_id] = [t for t in _verification_attempts[user_id] if t > cutoff]

            # Execute function
            try:
                result = await func(*args, **kwargs)
                # On success, clear attempts
                if user_id in _verification_attempts:
                    del _verification_attempts[user_id]
                return result
            except HTTPException as e:
                # On 401 (verification failure), record attempt
                if e.status_code == status.HTTP_401_UNAUTHORIZED:
                    _verification_attempts[user_id].append(now)

                    # Check if limit exceeded
                    if len(_verification_attempts[user_id]) >= max_attempts:
                        _lockouts[user_id] = now + timedelta(minutes=window_minutes)
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Too many failed attempts. Account locked for {window_minutes} minutes.",
                        ) from e
                raise
            except Exception:
                # Other exceptions - don't count as verification failure
                raise

        return wrapper

    return decorator
