"""Authentication utilities for JWT token management and password hashing."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import uuid4

import bcrypt
import jwt

from ...core.config import settings
from .types.jwt import CreateAccessTokenOptions, CreateRefreshTokenOptions, JWTPayload


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _encode_token(
    claims: dict[str, Any],
    *,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    """Encode a JWT, injecting the claims common to every token type.

    Centralizes the encode/``exp``/``iat``/``type`` boilerplate previously copied
    across every ``create_*_token`` builder, and stamps ``iss``/``aud`` so tokens
    are bound to this deployment and can't be replayed against a sibling that
    shares the same signing key (see verify_token).

    Args:
        claims: Token-type-specific payload claims (``sub``, ``email``, ...).
        token_type: Value for the ``type`` claim (``access``, ``refresh``, ...).
        expires_delta: Lifetime of the token from now.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(UTC)
    expire = now + expires_delta
    payload: dict[str, Any] = {
        **claims,
        "type": token_type,
        "iss": settings.security.jwt_issuer,
        "aud": settings.security.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(
        payload,
        settings.security.secret_key,
        algorithm=settings.security.jwt_algorithm,
    )


def create_access_token(
    data: CreateAccessTokenOptions,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token with optional tenant and 2FA context.

    Args:
        data: Token options including sub (required), email, tid, trol, tfaVerified, tfaMethod
        expires_delta: Optional custom expiration time. If not provided, uses default from settings.

    Returns:
        Encoded JWT token string
    """
    claims: dict[str, Any] = {
        "sub": data["sub"],
        "email": data.get("email"),
        "tid": data.get("tid"),
        "trol": data.get("trol"),
        "tfaPending": False,
        "tfaVerified": data.get("tfaVerified", False),
        "tfaMethod": data.get("tfaMethod"),
        "emailVerified": data.get("emailVerified"),
        "jti": data.get("jti", str(uuid4())),
        "tv": data.get("tv", 0),
    }
    return _encode_token(
        claims,
        token_type="access",
        expires_delta=expires_delta or timedelta(minutes=settings.security.access_token_expires_minutes),
    )


def verify_token(token: str, expected_type: str | None = None) -> JWTPayload:
    """Verify and decode a JWT token.

    Verifies signature, expiration, and — because every token minted by this
    module carries them — the ``iss`` and ``aud`` claims, binding the token to
    this deployment.

    Args:
        token: Encoded JWT string.
        expected_type: If given, the token's ``type`` claim must equal this
            value or ``InvalidTokenError`` is raised. Lets reset/verification
            flows assert token purpose at decode time instead of relying solely
            on downstream checks.

    Returns:
        Decoded JWT payload.

    Raises:
        ExpiredTokenError: Token signature has expired.
        InvalidTokenError: Signature, issuer, audience, or type is invalid.
    """
    from .exceptions import ExpiredTokenError, InvalidTokenError

    try:
        payload = jwt.decode(
            token,
            settings.security.secret_key,
            algorithms=[settings.security.jwt_algorithm],
            audience=settings.security.jwt_audience,
            issuer=settings.security.jwt_issuer,
        )
    except jwt.ExpiredSignatureError:
        raise ExpiredTokenError() from None
    except jwt.InvalidTokenError:
        raise InvalidTokenError() from None

    if expected_type is not None and payload.get("type") != expected_type:
        raise InvalidTokenError()

    return cast(JWTPayload, payload)


def create_refresh_token(data: CreateRefreshTokenOptions) -> str:
    """Create a JWT refresh token with longer expiration and 2FA context.

    Args:
        data: Token options including sub (required), email, tfaVerified, tfaMethod
            Note: tid/trol are NOT preserved in refresh tokens (security).

    Returns:
        Encoded JWT token string
    """
    claims: dict[str, Any] = {
        "sub": data["sub"],
        "email": data.get("email"),
        "tfaVerified": data.get("tfaVerified", False),
        "tfaMethod": data.get("tfaMethod"),
        "emailVerified": data.get("emailVerified"),
        "jti": data.get("jti", str(uuid4())),
        "tv": data.get("tv", 0),
        # NOTE: tid/trol are NOT preserved in refresh token (security)
    }
    return _encode_token(
        claims,
        token_type="refresh",
        expires_delta=timedelta(days=settings.security.refresh_token_expires_days),
    )


def create_password_reset_token(data: dict[str, str]) -> str:
    """Create a JWT password reset token with 1-hour expiration."""
    return _encode_token(
        dict(data),
        token_type="password_reset",
        expires_delta=timedelta(hours=settings.security.password_reset_token_expires_hours),
    )


def create_email_verification_token(data: dict[str, str]) -> str:
    """Create a JWT token for email verification."""
    return _encode_token(
        dict(data),
        token_type="email_verification",
        expires_delta=timedelta(hours=settings.security.email_verification_token_expires_hours),
    )
