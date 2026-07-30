"""TOTP utilities for generating, verifying and provisioning URIs."""

from __future__ import annotations

from urllib.parse import unquote

import pyotp

from app.core.config import settings


def _get_period() -> int:
    # Fallback to 30s if two_factor settings are not yet present
    return getattr(getattr(settings, "two_factor", object()), "totp_period", 30)


def _get_digits() -> int:
    return getattr(getattr(settings, "two_factor", object()), "totp_digits", 6)


def _get_issuer() -> str:
    return getattr(getattr(settings, "two_factor", object()), "totp_issuer", "FastAPI App")


def _get_time_window() -> int:
    return getattr(getattr(settings, "two_factor", object()), "totp_time_window", 1)


def generate_totp_secret() -> str:
    """Generate a new base32 TOTP secret."""

    return pyotp.random_base32()


def verify_totp_with_window(secret: str, code: str, window: int | None = None) -> bool:
    """Verify a TOTP code with time-window tolerance.

    If window is None, uses configured tolerance.
    """

    period = _get_period()
    digits = _get_digits()
    valid_window = _get_time_window() if window is None else window
    totp = pyotp.TOTP(secret, interval=period, digits=digits)
    return bool(totp.verify(code, valid_window=valid_window))


def get_totp_provisioning_uri(secret: str, user_email: str, issuer: str | None = None) -> str:
    """Build otpauth provisioning URI to be rendered as QR on frontend."""

    issuer_name = issuer or _get_issuer()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=user_email, issuer_name=issuer_name)
    # Ensure the label part of the URI is human-readable (issuer:user_email)
    if "?" in uri:
        label, query = uri.split("?", 1)
        return f"{unquote(label)}?{query}"
    return unquote(uri)
