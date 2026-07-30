"""2FA token utilities for login flow integration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict

import jwt

from app.core.config import settings

from .types.jwt import TwoFactorTokenPayload


class CreateTwoFactorTokenOptions(TypedDict, total=False):
    """Options for creating a 2FA verification token.

    Attributes:
        sub: Subject (User ID) - REQUIRED
        email: User email address - RECOMMENDED
    """

    sub: str
    email: str | None


def create_two_factor_token(data: CreateTwoFactorTokenOptions) -> str:
    """Create a short-lived JWT token for 2FA verification during login.

    This token is issued after password verification when 2FA is enabled.
    It has a short expiration (default 5 minutes) to ensure security.

    Args:
        data: Token options (must include 'sub' for user_id, optionally 'email')

    Returns:
        JWT token string
    """
    # Get expiration from settings (default 5 minutes)
    expires_minutes = getattr(
        getattr(settings, "two_factor", object()),
        "two_factor_token_expires_minutes",
        5,
    )

    now = datetime.now(UTC)
    expires = now + timedelta(minutes=expires_minutes)
    payload: TwoFactorTokenPayload = {
        "sub": data["sub"],
        "email": data.get("email"),
        "type": "2fa_verification",
        "exp": int(expires.timestamp()),
        "iat": int(now.timestamp()),
        "tfaPending": True,
        "tfaVerified": False,
        "tfaMethod": None,
    }
    return jwt.encode(
        dict(payload),
        settings.security.secret_key,
        algorithm=settings.security.jwt_algorithm,
    )


def verify_two_factor_token(token: str) -> TwoFactorTokenPayload:
    """Verify and decode a 2FA verification token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        jwt.ExpiredSignatureError: If token is expired
        jwt.InvalidTokenError: If token is invalid
    """
    payload_dict: dict[str, Any] = jwt.decode(
        token,
        settings.security.secret_key,
        algorithms=[settings.security.jwt_algorithm],
    )

    if payload_dict.get("type") != "2fa_verification":
        raise jwt.InvalidTokenError("Invalid token type")

    # Type cast to TwoFactorTokenPayload
    return payload_dict  # type: ignore[return-value]
