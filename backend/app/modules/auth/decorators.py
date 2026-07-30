"""Custom decorators for authentication, rate limiting, and validation."""

from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import Depends, HTTPException, status

from ...core.limiter import limiter
from .dependencies import get_current_user
from .models import User


def require_auth(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator for endpoints requiring authentication.

    Automatically injects authenticated user into 'current_user' parameter.

    Usage:
        @router.get("/me")
        @require_auth
        async def get_me(current_user: User) -> UserResponse:
            return UserResponse.model_validate(current_user)
    """

    @wraps(func)
    async def wrapper(*args: Any, current_user: User = Depends(get_current_user), **kwargs: Any) -> Any:
        return await func(*args, current_user=current_user, **kwargs)

    return wrapper


def rate_limit(limit: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for rate limiting.

    NOTE: This is just a convenience wrapper around limiter.limit.
    The decorated endpoint MUST include a 'request: Request' parameter.

    Args:
        limit: Rate limit string (e.g., "5/minute", "100/hour")

    Usage:
        @router.post("/login")
        @rate_limit("10/minute")
        async def login(request: Request, credentials: UserLogin) -> LoginResponse:
            # request parameter is required for rate limiting
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Apply limiter.limit directly - it will handle the request parameter
        return limiter.limit(limit)(func)

    return decorator


def recaptcha_protected(
    action: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for endpoints requiring reCAPTCHA verification.

    Expects the request body to have a 'recaptchaToken' field.

    NOTE: This is an optional security feature. Enable by setting:
    RECAPTCHA_ENABLED=true in your .env file and configuring reCAPTCHA keys.

    Args:
        action: reCAPTCHA action name (should match client-side action)

    Usage:
        @router.post("/register")
        @recaptcha_protected("register")
        async def register(user_data: UserRegister) -> LoginResponse:
            # reCAPTCHA already verified
            ...

    Frontend Integration:
        // Add reCAPTCHA token to your request body:
        const response = await fetch('/auth/register', {
            method: 'POST',
            body: JSON.stringify({
                ...userData,
                recaptchaToken: await grecaptcha.execute(siteKey, {action: 'register'})
            })
        });
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            import logging

            from app.core.recaptcha import RecaptchaError, verify_recaptcha

            logger = logging.getLogger(__name__)

            # Find the request data object in args or kwargs
            request_data = None
            for arg in args:
                if hasattr(arg, "recaptchaToken"):
                    request_data = arg
                    break

            if not request_data:
                for kwarg_value in kwargs.values():
                    if hasattr(kwarg_value, "recaptchaToken"):
                        request_data = kwarg_value
                        break

            # Verify reCAPTCHA token (only if enabled and token is provided)
            from app.core.config import settings

            logger.info(f"reCAPTCHA decorator: enabled={settings.recaptcha.enabled}, action={action}")

            if settings.recaptcha.enabled:
                token = None
                if request_data and hasattr(request_data, "recaptchaToken"):
                    token = request_data.recaptchaToken

                logger.debug(f"reCAPTCHA decorator: request_data found={bool(request_data)}, token present={bool(token)}")

                # If reCAPTCHA is enabled, token is required
                if not token:
                    logger.error(f"reCAPTCHA token missing for action: {action}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="reCAPTCHA token is required",
                    )

                try:
                    logger.info(f"Calling verify_recaptcha for action: {action}")
                    await verify_recaptcha(token, action=action)
                    logger.info(f"reCAPTCHA verification passed for action: {action}")
                except RecaptchaError as e:
                    logger.error(f"reCAPTCHA verification failed for action {action}: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"reCAPTCHA verification failed: {str(e)}",
                    ) from e
            else:
                logger.debug(f"reCAPTCHA disabled, skipping verification for action: {action}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator
