"""TOTP service layer for setup, verification, and backup codes management.

This service handles all TOTP-related operations including:
- TOTP setup and verification
- Backup codes generation and management
- TOTP status and configuration
- Disabling TOTP

Uses composition pattern - no inheritance.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import jwt

from app.core.config import settings

from .crypto_utils import (
    decrypt_secret,
    encrypt_secret,
    generate_backup_codes,
    mark_backup_code_used,
    verify_backup_code,
)
from .exceptions import InvalidTwoFactorCodeError, SetupTokenError
from .totp_utils import (
    generate_totp_secret,
    get_totp_provisioning_uri,
    verify_totp_with_window,
)
from .types.jwt import TotpSetupTokenPayload
from .types.repository import TwoFactorRepositoryInterface

logger = logging.getLogger(__name__)


def _create_totp_setup_token(user_id: str, secret: str, backup_codes_hashed: list[str]) -> str:
    """Create a short-lived JWT used during TOTP setup verification.

    Args:
        user_id: User ID
        secret: TOTP secret
        backup_codes_hashed: Hashed backup codes

    Returns:
        JWT token string
    """
    expires = datetime.now(UTC) + timedelta(minutes=10)
    payload: dict[str, Any] = {
        "sub": user_id,
        "secret": secret,
        "backup_codes_hashed": backup_codes_hashed,
        "type": "2fa_setup",
        "exp": int(expires.timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
    }
    return jwt.encode(
        payload,
        settings.security.secret_key,
        algorithm=settings.security.jwt_algorithm,
    )


def _verify_totp_setup_token(token: str) -> TotpSetupTokenPayload:
    """Verify and decode TOTP setup token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload

    Raises:
        SetupTokenError: If token is invalid or expired
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.security.secret_key,
            algorithms=[settings.security.jwt_algorithm],
        )
        if payload.get("type") != "2fa_setup":
            raise SetupTokenError("Invalid token type for TOTP setup")
        if "secret" not in payload:
            raise SetupTokenError("Invalid token - missing secret")
        return cast(TotpSetupTokenPayload, payload)
    except jwt.ExpiredSignatureError as exc:
        raise SetupTokenError("Setup token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise SetupTokenError("Invalid setup token") from exc


class TotpService:
    """Service for TOTP operations using composition pattern."""

    def __init__(self, repository: TwoFactorRepositoryInterface):
        """Initialize with repository dependency.

        Args:
            repository: Two-factor repository interface
        """
        self.repository = repository

    async def initiate_setup(self, user_id: str, email: str) -> dict[str, Any]:
        """Start TOTP setup by generating secret, URI and backup codes.

        Args:
            user_id: User ID
            email: User email for QR code

        Returns:
            Dict with qrCodeUri, secret, backupCodes, setupToken, expiresAt
        """
        secret = generate_totp_secret()
        qr_uri = get_totp_provisioning_uri(secret, user_email=email)
        plain_codes, hashed_codes = generate_backup_codes()

        setup_token = _create_totp_setup_token(user_id, secret, hashed_codes)

        return {
            "qrCodeUri": qr_uri,
            "secret": secret,
            "backupCodes": plain_codes,
            "setupToken": setup_token,
            "expiresAt": datetime.now(UTC) + timedelta(minutes=10),
        }

    async def verify_setup(self, setup_token: str, code: str) -> dict[str, Any]:
        """Verify initial TOTP code and persist configuration.

        Args:
            setup_token: JWT setup token
            code: TOTP code from user

        Returns:
            Dict with verified: True

        Raises:
            InvalidTwoFactorCodeError: If code is invalid
        """
        payload = _verify_totp_setup_token(setup_token)
        user_id: str = payload["sub"]
        secret: str = payload["secret"]
        hashed_codes: list[str] = payload["backup_codes_hashed"]

        if not verify_totp_with_window(secret, code):
            raise InvalidTwoFactorCodeError("Invalid verification code")

        encrypted_secret = encrypt_secret(secret)
        await self.repository.create_totp_config(
            user_id=user_id,
            encrypted_secret=encrypted_secret,
            backup_codes_hashed_json=json.dumps(hashed_codes),
        )
        await self.repository.mark_totp_verified(user_id)

        return {"verified": True}

    async def get_status(self, user_id: str) -> dict[str, Any]:
        """Get TOTP status and configuration.

        Args:
            user_id: User ID

        Returns:
            Dict with isEnabled, isVerified, createdAt, verifiedAt,
            lastVerifiedAt, backupCodesRemaining
        """
        config = await self.repository.get_totp_config(user_id)
        if not config:
            return {
                "isEnabled": False,
                "isVerified": False,
                "createdAt": None,
                "verifiedAt": None,
                "lastVerifiedAt": None,
                "backupCodesRemaining": 0,
            }

        try:
            backup_codes = json.loads(config.backup_codes) if config.backup_codes else []
            used_codes = json.loads(config.backup_codes_used) if config.backup_codes_used else []
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to decode backup codes JSON for user {user_id}: {e}")
            backup_codes = []
            used_codes = []

        return {
            "isEnabled": bool(config.is_enabled),
            "isVerified": bool(config.verified_at is not None or config.is_enabled),
            "createdAt": config.created_at,
            "verifiedAt": config.verified_at,
            "lastVerifiedAt": config.last_verified_at,
            "backupCodesRemaining": max(0, len(backup_codes) - len(used_codes)),
        }

    async def regenerate_backup_codes(
        self,
        user_id: str,
        password: str | None = None,
        totp_code: str | None = None,
        user_repository: Any = None,
    ) -> dict[str, Any]:
        """Regenerate backup codes.

        Args:
            user_id: User ID
            password: User password (for verification)
            totp_code: Current TOTP code (alternative verification)
            user_repository: User repository for password verification

        Returns:
            Dict with codes, count, generatedAt

        Raises:
            ValueError: If verification fails or TOTP not enabled
            InvalidTwoFactorCodeError: If password or TOTP code invalid
        """
        from app.modules.auth.auth_utils import verify_password

        config = await self.repository.get_totp_config(user_id)
        if not config or not config.is_enabled:
            raise ValueError("TOTP is not enabled for this user")

        # Verify password or TOTP code
        if password:
            if not user_repository:
                raise ValueError("User repository required for password verification")
            user = await user_repository.get_user_by_id(user_id)
            if not user or not verify_password(password, user.hashedPassword):
                raise InvalidTwoFactorCodeError("Invalid password")
        elif totp_code:
            secret = decrypt_secret(config.secret)
            if not verify_totp_with_window(secret, totp_code):
                raise InvalidTwoFactorCodeError("Invalid TOTP code")
        else:
            raise ValueError("Either password or TOTP code must be provided")

        # Generate new backup codes
        plain_codes, hashed_codes = generate_backup_codes()
        await self.repository.update_backup_codes(user_id, json.dumps(hashed_codes))

        return {
            "codes": plain_codes,
            "count": len(plain_codes),
            "generatedAt": datetime.now(UTC),
        }

    async def disable(
        self,
        user_id: str,
        password: str | None = None,
        backup_code: str | None = None,
        user_repository: Any = None,
    ) -> dict[str, Any]:
        """Disable TOTP.

        Args:
            user_id: User ID
            password: User password (for verification)
            backup_code: Backup code (alternative verification)
            user_repository: User repository for password verification

        Returns:
            Dict with success: True, message

        Raises:
            ValueError: If TOTP not enabled or verification method missing
            InvalidTwoFactorCodeError: If password or backup code invalid
        """
        from app.modules.auth.auth_utils import verify_password

        config = await self.repository.get_totp_config(user_id)
        if not config:
            raise ValueError("TOTP is not enabled for this user")

        # Verify password or backup code
        if password:
            if not user_repository:
                raise ValueError("User repository required for password verification")
            user = await user_repository.get_user_by_id(user_id)
            if not user or not verify_password(password, user.hashedPassword):
                raise InvalidTwoFactorCodeError("Invalid password")
        elif backup_code:
            backup_codes = json.loads(config.backup_codes) if config.backup_codes else []
            used_codes = json.loads(config.backup_codes_used) if config.backup_codes_used else []
            if not verify_backup_code(backup_code, backup_codes, used_codes):
                raise InvalidTwoFactorCodeError("Invalid backup code")
        else:
            raise ValueError("Either password or backup code must be provided")

        # Disable TOTP
        await self.repository.disable_totp(user_id)

        return {"success": True, "message": "TOTP disabled"}

    async def verify_code(self, user_id: str, code: str, mark_used: bool = False) -> tuple[bool, bool]:
        """Verify TOTP code or backup code.

        Args:
            user_id: User ID
            code: TOTP code or backup code
            mark_used: Whether to mark backup code as used if valid

        Returns:
            Tuple of (is_valid, is_backup_code)

        Raises:
            InvalidTwoFactorCodeError: If TOTP not enabled
        """
        config = await self.repository.get_totp_config(user_id)
        if not config or not config.is_enabled:
            raise InvalidTwoFactorCodeError("TOTP is not enabled for this user")

        # Try TOTP code first
        secret = decrypt_secret(config.secret)
        if verify_totp_with_window(secret, code):
            await self.repository.update_totp_last_verified(user_id)
            return (True, False)

        # Try backup codes
        backup_codes = json.loads(config.backup_codes) if config.backup_codes else []
        used_codes = json.loads(config.backup_codes_used) if config.backup_codes_used else []

        if verify_backup_code(code, backup_codes, used_codes):
            if mark_used:
                used_codes = mark_backup_code_used(code, used_codes)
                await self.repository.mark_backup_code_used(user_id, json.dumps(used_codes))
            return (True, True)

        return (False, False)
