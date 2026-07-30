"""Return types for 2FA login token issuance.

Kept as TypedDicts (not dict[str, Any]) so mypy checks the `**result`
unpacking into TwoFactorVerifyResponse at the router call site — a plain
dict[str, Any] return type lets a missing key (e.g. `verified`/`method`)
through silently, surfacing only as a runtime pydantic ValidationError.
"""

from typing import TypedDict


class LoginTokens(TypedDict):
    """JWT tokens minted for a completed login."""

    accessToken: str
    refreshToken: str
    tokenType: str
    expiresIn: int


class TwoFactorLoginResult(LoginTokens):
    """Full result of a 2FA login verification (TOTP or WebAuthn).

    Matches TwoFactorVerifyResponse's required fields.
    """

    verified: bool
    method: str
