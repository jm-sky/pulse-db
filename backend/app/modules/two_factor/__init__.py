"""Two-Factor Authentication (2FA) module.

Provides TOTP (authenticator apps) and WebAuthn/Passkeys support.
Phase 1 initializes TOTP MVP: utilities, models, repository, service, router.
"""

from .types.jwt import (
    PasskeyRegistrationTokenPayload,
    TotpSetupTokenPayload,
    TwoFactorTokenPayload,
)

__all__ = [
    "TwoFactorTokenPayload",
    "TotpSetupTokenPayload",
    "PasskeyRegistrationTokenPayload",
]
