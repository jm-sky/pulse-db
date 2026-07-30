"""WebAuthn utilities for passkey registration and authentication."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import (
    base64url_to_bytes,
    bytes_to_base64url,
    parse_authentication_credential_json,
    parse_registration_credential_json,
)
from webauthn.helpers.structs import (
    AuthenticatorTransport,
    PublicKeyCredentialDescriptor,
    UserVerificationRequirement,
)

from app.core.config import settings


def _frontend_hostname() -> str:
    """Hostname derived from FRONTEND_URL."""
    return urlparse(settings.frontend_url).hostname or "localhost"


def _get_rp_id() -> str:
    """Get WebAuthn Relying Party ID from settings.

    When WEBAUTHN_RP_ID is still ``localhost`` but the app is served on a real
    domain (FRONTEND_URL), use that domain so browser ceremonies succeed.
    """
    configured = settings.webauthn.rp_id
    frontend_host = _frontend_hostname()
    if configured in ("localhost", "127.0.0.1") and frontend_host not in (
        "localhost",
        "127.0.0.1",
    ):
        return frontend_host
    return configured or frontend_host


def _get_rp_name() -> str:
    """Get WebAuthn Relying Party name from settings."""
    return settings.webauthn.rp_name


def _get_origin() -> str:
    """Expected WebAuthn origin (frontend URL).

    When WEBAUTHN_ORIGIN is still a localhost URL but FRONTEND_URL is a real
    domain, use FRONTEND_URL so verification matches the browser origin.
    """
    configured = settings.webauthn.origin
    frontend = settings.frontend_url
    if not configured:
        return frontend
    configured_host = urlparse(configured).hostname or ""
    frontend_host = _frontend_hostname()
    if configured_host in ("localhost", "127.0.0.1") and frontend_host not in (
        "localhost",
        "127.0.0.1",
    ):
        return frontend
    return configured


def _get_timeout() -> int:
    """Get WebAuthn timeout in milliseconds."""
    return 60000


def create_registration_options(user_id: str, user_email: str, user_name: str) -> tuple[str, str]:
    """
    Create WebAuthn registration options.

    Args:
        user_id: User ID (will be encoded as bytes)
        user_email: User email (used as user name)
        user_name: User display name

    Returns:
        (options_json, challenge) - options for frontend (JSON string), challenge to store (base64url)
    """
    options = generate_registration_options(
        rp_id=_get_rp_id(),
        rp_name=_get_rp_name(),
        user_id=user_id.encode(),
        user_name=user_email,
        user_display_name=user_name,
        timeout=_get_timeout(),
    )

    return options_to_json(options), bytes_to_base64url(options.challenge)


def verify_registration(
    credential_json: dict[str, Any],
    expected_challenge: str,
    expected_origin: str,
    expected_rp_id: str | None = None,
) -> dict[str, Any]:
    """
    Verify WebAuthn registration response.

    Args:
        credential_json: Credential JSON from frontend (navigator.credentials.create result)
        expected_challenge: Challenge that was sent to frontend
        expected_origin: Expected origin (e.g., "https://example.com")
        expected_rp_id: Expected Relying Party ID (uses settings if None)

    Returns:
        Verified credential data:
        - credential_id: Base64url-encoded credential ID
        - public_key: Base64url-encoded public key
        - counter: Initial signature counter
        - aaguid: Authenticator AAGUID
        - transports: List of transport types
        - backup_eligible: Backup eligible flag
        - backup_state: Backup state flag

    Raises:
        Exception: If verification fails
    """
    credential = parse_registration_credential_json(credential_json)

    rp_id = expected_rp_id or _get_rp_id()

    verification = verify_registration_response(
        credential=credential,
        expected_challenge=base64url_to_bytes(expected_challenge),
        expected_origin=expected_origin,
        expected_rp_id=rp_id,
    )

    # Extract transports if available
    transports = []
    if hasattr(credential.response, "transports") and credential.response.transports:
        transports = [t.value for t in credential.response.transports]

    # backup_eligible is not directly available in VerifiedRegistration
    # Use credential_device_type to determine if backup eligible
    # Single-device credentials are typically not backup eligible
    backup_eligible = getattr(verification, "credential_device_type", None) is not None
    if hasattr(verification, "credential_device_type"):
        # Check if it's a multi-device credential (which can be backed up)
        # For now, we'll use a conservative default
        backup_eligible = False

    return {
        "credential_id": bytes_to_base64url(verification.credential_id),
        "public_key": bytes_to_base64url(verification.credential_public_key),
        "counter": verification.sign_count,
        "aaguid": str(verification.aaguid),
        "transports": transports,
        "backup_eligible": backup_eligible,
        "backup_state": verification.credential_backed_up,
    }


def create_authentication_options(
    allow_credentials: list[tuple[bytes, list[str]]],
) -> tuple[str, bytes]:
    """
    Create WebAuthn authentication (passkey login) options.

    Args:
        allow_credentials: List of (credential_id_bytes, transports) for the
            user's enabled passkeys

    Returns:
        (options_json, challenge) - options for frontend (JSON string, already
        base64url-encoded internally by options_to_json), raw challenge bytes
        to store server-side for later verification
    """
    descriptors = [
        PublicKeyCredentialDescriptor(
            id=credential_id,
            transports=[AuthenticatorTransport(t) for t in transports] or None,
        )
        for credential_id, transports in allow_credentials
    ]

    options = generate_authentication_options(
        rp_id=_get_rp_id(),
        allow_credentials=descriptors,
        user_verification=UserVerificationRequirement.REQUIRED,
        timeout=_get_timeout(),
    )

    return options_to_json(options), options.challenge


def verify_authentication(
    credential_json: dict[str, Any],
    expected_challenge: bytes,
    expected_origin: str,
    credential_public_key: bytes,
    credential_current_sign_count: int,
    expected_rp_id: str | None = None,
) -> dict[str, Any]:
    """
    Verify a WebAuthn authentication (passkey login) response.

    Args:
        credential_json: Credential JSON from frontend (navigator.credentials.get result)
        expected_challenge: Raw challenge bytes that were sent to frontend as
            `options.challenge` (the exact bytes `generate_authentication_options`
            produced — not re-encoded, just round-tripped through storage)
        expected_origin: Expected origin (e.g., "https://example.com")
        credential_public_key: Decrypted, raw public key bytes for the stored passkey
        credential_current_sign_count: Last known signature counter for the stored passkey
        expected_rp_id: Expected Relying Party ID (uses settings if None)

    Returns:
        Dict with new_sign_count (verified, monotonically-increasing counter)

    Raises:
        Exception: If verification fails (bad signature, replayed/cloned
            counter, origin/rp_id mismatch, challenge mismatch, etc.)
    """
    credential = parse_authentication_credential_json(credential_json)

    rp_id = expected_rp_id or _get_rp_id()

    verification = verify_authentication_response(
        credential=credential,
        expected_challenge=expected_challenge,
        expected_rp_id=rp_id,
        expected_origin=expected_origin,
        credential_public_key=credential_public_key,
        credential_current_sign_count=credential_current_sign_count,
        require_user_verification=True,
    )

    return {
        "new_sign_count": verification.new_sign_count,
    }
