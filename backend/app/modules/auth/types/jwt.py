"""JWT type definitions for authentication module.

This module defines the unified JWT payload structure that matches
the frontend TypeScript interface. See docs/JWT_FLOW.md for detailed
flow documentation.
"""

from typing import TypedDict


class JWTPayload(TypedDict, total=False):
    """Unified JWT token payload structure.

    This structure matches the frontend TypeScript JWTPayload interface.
    All fields except 'sub', 'iat', 'exp', 'type' are optional.

    Attributes:
        sub: Subject (User ID) - REQUIRED
        email: User email address - RECOMMENDED
        tid: Tenant ID (optional, for multi-tenant support)
        trol: Tenant Role (optional, role within tenant)
        iat: Issued at (Unix timestamp) - REQUIRED
        exp: Expiration time (Unix timestamp) - REQUIRED
        aud: Audience (optional, token audience)
        tfaPending: Whether 2FA verification is required (optional)
        tfaVerified: Whether 2FA has been verified (optional)
        tfaMethod: 2FA method used - 'totp' or 'webauthn' (optional)
        type: Token type - 'access', 'refresh', '2fa_verification', etc. - REQUIRED

    See docs/JWT_FLOW.md for detailed flow documentation.
    """

    sub: str
    email: str | None
    tid: str | None
    trol: str | None
    iat: int
    exp: int
    aud: str | None
    iss: str | None
    tfaPending: bool | None
    tfaVerified: bool | None
    tfaMethod: str | None  # 'totp' | 'webauthn'
    type: str
    emailVerified: bool | None
    jti: str
    tv: int


class CreateAccessTokenOptions(TypedDict, total=False):
    """Options for creating an access token.

    Attributes:
        sub: Subject (User ID) - REQUIRED
        email: User email address - RECOMMENDED
        tid: Tenant ID (optional, for multi-tenant support)
        trol: Tenant Role (optional, role within tenant)
        tfaVerified: Whether 2FA has been verified (default: False)
        tfaMethod: 2FA method used - 'totp' or 'webauthn' (optional)
    """

    sub: str
    email: str | None
    tid: str | None
    trol: str | None
    tfaVerified: bool
    tfaMethod: str | None  # 'totp' | 'webauthn'
    emailVerified: bool | None
    jti: str
    tv: int


class CreateRefreshTokenOptions(TypedDict, total=False):
    """Options for creating a refresh token.

    Attributes:
        sub: Subject (User ID) - REQUIRED
        email: User email address - RECOMMENDED
        tfaVerified: Whether 2FA has been verified (default: False)
        tfaMethod: 2FA method used - 'totp' or 'webauthn' (optional)

    Note: tid/trol are NOT preserved in refresh tokens (security).
    """

    sub: str
    email: str | None
    tfaVerified: bool
    tfaMethod: str | None  # 'totp' | 'webauthn'
    emailVerified: bool | None
    jti: str
    tv: int
