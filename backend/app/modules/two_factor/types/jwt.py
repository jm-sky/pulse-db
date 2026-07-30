"""JWT type definitions for Two-Factor Authentication module."""

from typing import TypedDict


class TwoFactorTokenPayload(TypedDict, total=False):
    """JWT token payload for 2FA verification during login.

    This extends the unified JWTPayload structure with 2FA-specific fields.
    See docs/JWT_FLOW.md for detailed flow documentation.

    Attributes:
        sub: Subject (user ID) - REQUIRED
        email: User email address - RECOMMENDED
        exp: Expiration time (Unix timestamp) - REQUIRED
        iat: Issued at (Unix timestamp) - REQUIRED
        type: Token type - "2fa_verification" - REQUIRED
        tfaPending: Whether 2FA verification is required (always True for this token type)
        tfaVerified: Whether 2FA has been verified (always False for this token type)
        tfaMethod: 2FA method used - 'totp' or 'webauthn' (null until verified)
    """

    sub: str
    email: str | None
    exp: int
    iat: int
    type: str  # "2fa_verification"
    tfaPending: bool | None
    tfaVerified: bool | None
    tfaMethod: str | None  # 'totp' | 'webauthn'


class TotpSetupTokenPayload(TypedDict, total=False):
    """JWT token payload for TOTP setup verification.

    Attributes:
        sub: Subject (user ID)
        secret: Plain TOTP secret (temporary, only in token)
        backup_codes_hashed: List of hashed backup codes
        exp: Expiration time (Unix timestamp)
        iat: Issued at (Unix timestamp)
        type: Token type - "2fa_setup"
    """

    sub: str
    secret: str
    backup_codes_hashed: list[str]
    exp: int
    iat: int
    type: str  # "2fa_setup"


class PasskeyRegistrationTokenPayload(TypedDict, total=False):
    """JWT token payload for passkey registration.

    Attributes:
        sub: Subject (user ID)
        challenge: WebAuthn challenge (base64url-encoded)
        exp: Expiration time (Unix timestamp)
        iat: Issued at (Unix timestamp)
        type: Token type - "passkey_registration"
    """

    sub: str
    challenge: str
    exp: int
    iat: int
    type: str  # "passkey_registration"
