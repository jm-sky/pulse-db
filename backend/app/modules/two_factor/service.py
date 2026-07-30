"""Two-Factor Authentication service facade.

This service aggregates TOTP and WebAuthn services using composition pattern.
It provides a unified interface for all 2FA operations while delegating to
specialized services.

Uses composition over inheritance - no base classes.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select

from app.modules.settings.db_models import UserSettingsDB

from .totp_service import TotpService
from .types.repository import TwoFactorRepositoryInterface
from .types.tokens import LoginTokens, TwoFactorLoginResult
from .webauthn_service import WebAuthnService

logger = logging.getLogger(__name__)


class TwoFactorService:
    """Facade service aggregating TOTP and WebAuthn services.

    This service uses composition to delegate operations to specialized
    services while providing a unified API for 2FA operations.
    """

    def __init__(
        self,
        repository: TwoFactorRepositoryInterface,
        challenge_store: Any = None,
        user_repository: Any = None,
        token_blacklist_service: Any = None,
    ):
        """Initialize with repository and create service dependencies.

        Args:
            repository: Two-factor repository interface
            challenge_store: WebAuthn challenge store (optional)
            user_repository: User repository, required by verify_totp_login /
                complete_passkey_authentication to mint full-claim login tokens
            token_blacklist_service: Session tracking service (optional)
        """
        self.repository = repository
        # Composition: create specialized services
        self.totp = TotpService(repository)
        self.webauthn = WebAuthnService(repository, challenge_store)
        self.user_repository = user_repository
        self.token_blacklist_service = token_blacklist_service

    async def _issue_login_tokens(self, user_id: str, tfa_method: str) -> LoginTokens:
        """Mint access/refresh tokens for a completed 2FA login.

        Delegates to ``AuthService._issue_login_tokens`` (the same helper the
        password/OAuth login paths use) so these tokens carry the same `tv`
        (token version) and `jti` (session id) claims. Without them,
        `_verify_user_token` rejects every request from a user whose
        `tokenVersion` isn't 0 (e.g. anyone who ever reset their password)
        with 401 "Token has been revoked" right after a successful 2FA check.

        Note: pulse-db ``AuthService._issue_login_tokens`` returns
        ``tuple[str, str]`` (access, refresh), not ``LoginResponse``.
        """
        from app.core.config import settings
        from app.modules.auth.exceptions import UserNotFoundError
        from app.modules.auth.service import AuthService

        if self.user_repository is None:
            raise RuntimeError("TwoFactorService requires user_repository to issue login tokens")

        user = await self.user_repository.get_user_by_id(user_id)
        if user is None:
            raise UserNotFoundError("User not found")

        auth_service = AuthService(user_repository=self.user_repository, token_blacklist_service=self.token_blacklist_service)
        access_token, refresh_token = await auth_service._issue_login_tokens(user, tfa_verified=True, tfa_method=tfa_method)

        return {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "tokenType": "bearer",
            "expiresIn": settings.security.access_token_expires_minutes * 60,
        }

    async def _get_or_create_user_settings(self, user_id: str) -> UserSettingsDB:
        """Get or create user settings.

        Args:
            user_id: User ID

        Returns:
            User settings entity
        """
        db = self.repository.db
        result = await db.execute(select(UserSettingsDB).where(UserSettingsDB.user_id == user_id))
        settings = result.scalars().first()
        if settings is None:
            settings = UserSettingsDB(user_id=user_id)
            db.add(settings)
            await db.commit()
            await db.refresh(settings)
        return settings

    # ==================================================================
    # TOTP Methods - delegate to TotpService
    # ==================================================================

    async def initiate_totp_setup(self, user_id: str, email: str) -> dict[str, Any]:
        """Start TOTP setup. Delegates to TotpService."""
        return await self.totp.initiate_setup(user_id, email)

    async def verify_totp_setup(self, setup_token: str, code: str) -> dict[str, Any]:
        """Verify TOTP setup. Delegates to TotpService."""
        return await self.totp.verify_setup(setup_token, code)

    async def get_totp_status(self, user_id: str) -> dict[str, Any]:
        """Get TOTP status. Delegates to TotpService."""
        return await self.totp.get_status(user_id)

    async def regenerate_backup_codes(
        self,
        user_id: str,
        password: str | None = None,
        totp_code: str | None = None,
        user_repository: Any = None,
    ) -> dict[str, Any]:
        """Regenerate backup codes. Delegates to TotpService."""
        return await self.totp.regenerate_backup_codes(user_id, password, totp_code, user_repository)

    async def disable_totp(
        self,
        user_id: str,
        password: str | None = None,
        backup_code: str | None = None,
        user_repository: Any = None,
    ) -> dict[str, Any]:
        """Disable TOTP. Delegates to TotpService."""
        return await self.totp.disable(user_id, password, backup_code, user_repository)

    async def verify_totp_login(self, two_factor_token: str, code: str) -> TwoFactorLoginResult:
        """Verify TOTP code during login and return JWT tokens.

        This method combines TOTP verification with token generation.
        """
        from .auth_utils import verify_two_factor_token

        # Verify 2FA token
        payload = verify_two_factor_token(two_factor_token)
        user_id: str = payload["sub"]

        # Verify TOTP/backup code
        is_valid, is_backup = await self.totp.verify_code(user_id, code, mark_used=True)

        if not is_valid:
            from .exceptions import InvalidTwoFactorCodeError

            raise InvalidTwoFactorCodeError("Invalid verification code")

        tokens = await self._issue_login_tokens(user_id, tfa_method="totp")

        return {
            "verified": True,
            "method": "totp",
            **tokens,
        }

    # ==================================================================
    # WebAuthn Methods - delegate to WebAuthnService
    # ==================================================================

    async def initiate_passkey_registration(
        self,
        user_id: str,
        user_email: str,
        user_name: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Initiate passkey registration. Delegates to WebAuthnService."""
        return await self.webauthn.initiate_registration(user_id, user_email, user_name, name)

    async def complete_passkey_registration(
        self,
        registration_token: str,
        credential_json: dict[str, Any],
        name: str | None = None,
        user_agent: str | None = None,
        origin: str | None = None,
    ) -> dict[str, Any]:
        """Complete passkey registration. Delegates to WebAuthnService."""
        return await self.webauthn.complete_registration(registration_token, credential_json, name, user_agent, origin)

    async def get_webauthn_status(self, user_id: str) -> dict[str, Any]:
        """Get WebAuthn status. Delegates to WebAuthnService."""
        return await self.webauthn.get_status(user_id)

    async def delete_passkey(self, passkey_id: str, user_id: str) -> None:
        """Delete passkey. Delegates to WebAuthnService."""
        await self.webauthn.delete_passkey(passkey_id, user_id)

    async def initiate_passkey_authentication(self, user_id: str) -> dict[str, Any]:
        """Initiate passkey authentication. Delegates to WebAuthnService."""
        return await self.webauthn.initiate_authentication(user_id)

    async def complete_passkey_authentication(
        self,
        challenge_token: str,
        credential_json: dict,
        challenge_data: dict | None = None,
        expected_user_id: str | None = None,
    ) -> TwoFactorLoginResult:
        """Complete passkey authentication during login and return JWT tokens.

        Delegates credential verification to WebAuthnService, then mints
        tokens the same way verify_totp_login does — this endpoint is part
        of the login flow, so its response must match TwoFactorVerifyResponse
        (verified/method/accessToken/...), not WebAuthnService's internal
        {success, userId, passkeyId} shape.
        """
        result = await self.webauthn.complete_authentication(challenge_token, credential_json, challenge_data, expected_user_id)
        user_id = result["userId"]

        tokens = await self._issue_login_tokens(user_id, tfa_method="webauthn")

        return {
            "verified": True,
            "method": "webauthn",
            **tokens,
        }

    # ==================================================================
    # Combined 2FA Methods - use both services
    # ==================================================================

    async def has_two_factor_enabled(self, user_id: str) -> bool:
        """Check if user has any 2FA method enabled.

        Combines TOTP and WebAuthn status checks.
        """
        totp_status = await self.totp.get_status(user_id)
        has_totp = bool(totp_status.get("isEnabled", False))

        webauthn_status = await self.webauthn.get_status(user_id)
        has_passkeys = bool(webauthn_status.get("enabled", False))

        logger.info(f"2FA check for user {user_id}: " f"TOTP enabled={has_totp}, " f"Passkeys enabled={has_passkeys}, " f"Has 2FA={has_totp or has_passkeys}")

        return has_totp or has_passkeys

    async def get_available_methods(self, user_id: str) -> list[str]:
        """Get list of available 2FA methods for user.

        Combines TOTP and WebAuthn availability.
        """
        methods = []

        totp_status = await self.totp.get_status(user_id)
        if totp_status.get("isEnabled"):
            methods.append("totp")

        webauthn_status = await self.webauthn.get_status(user_id)
        if webauthn_status.get("enabled"):
            methods.append("webauthn")

        return methods

    async def get_preferred_method(self, user_id: str) -> str | None:
        """Get preferred 2FA method.

        Returns user's preferred method from user_settings, or first available method if no preference set.
        """
        # Get user's preferred method from settings
        settings = await self._get_or_create_user_settings(user_id)
        preferred_method = settings.preferred_2fa_method

        # Get available methods
        methods = await self.get_available_methods(user_id)

        # If user has a preferred method and it's available, return it
        if preferred_method and preferred_method in methods:
            return preferred_method

        # Otherwise, return first available method (TOTP priority)
        if methods:
            return methods[0]

        return None

    async def get_two_factor_status(self, user_id: str) -> dict[str, Any]:
        """Get combined 2FA status (TOTP + WebAuthn).

        Aggregates status from both services.
        """
        totp_status = await self.totp.get_status(user_id)
        webauthn_status = await self.webauthn.get_status(user_id)

        return {
            "totp": {
                "enabled": totp_status.get("isEnabled", False),
                "createdAt": totp_status.get("createdAt"),
                "lastUsedAt": totp_status.get("lastVerifiedAt"),
            },
            "webauthn": webauthn_status,
            "required": False,  # Global setting - can be added later
        }

    async def update_preferred_method(self, user_id: str, method: str | None) -> None:
        """Update user's preferred 2FA method.

        Args:
            user_id: User ID
            method: Preferred method ('totp' or 'webauthn'), or None to clear preference

        Raises:
            ValueError: If method is invalid or not enabled
        """
        # If method is None, just clear the preference
        if method is None:
            settings = await self._get_or_create_user_settings(user_id)
            settings.preferred_2fa_method = None
            await self.repository.db.commit()
            await self.repository.db.refresh(settings)
            logger.info(f"Cleared preferred 2FA method for user {user_id}")
            return

        valid_methods = ["totp", "webauthn"]
        if method not in valid_methods:
            raise ValueError(f"Invalid method. Must be one of: {valid_methods}")

        # Verify the method is enabled for the user
        if method == "totp":
            status = await self.totp.get_status(user_id)
            if not status.get("isEnabled"):
                raise ValueError("TOTP is not enabled for this user")
        elif method == "webauthn":
            status = await self.webauthn.get_status(user_id)
            if not status.get("enabled"):
                raise ValueError("WebAuthn is not enabled for this user")

        # Store preferred method in user_settings table
        settings = await self._get_or_create_user_settings(user_id)
        settings.preferred_2fa_method = method
        await self.repository.db.commit()
        await self.repository.db.refresh(settings)

        logger.info(f"Updated preferred 2FA method for user {user_id} to {method}")
