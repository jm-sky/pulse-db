"""Authentication service layer for business logic."""

import logging
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast
from uuid import uuid4

from ...core.config import settings
from ...core.email import get_email_service
from ...core.email.i18n import SupportedLocale
from .auth_utils import (
    create_access_token,
    create_email_verification_token,
    create_refresh_token,
    verify_token,
)
from .exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from .models import User
from .schemas import LoginResponse, UserResponse
from .types.repository import UserRepositoryInterface

if TYPE_CHECKING:
    from app.core.auth.token_blacklist import TokenBlacklistService
    from app.modules.two_factor.types.repository import TwoFactorRepositoryInterface

logger = logging.getLogger(__name__)


class AuthService:
    """Service class for authentication operations."""

    user_repository: UserRepositoryInterface

    def __init__(
        self,
        user_repository: UserRepositoryInterface,
        token_blacklist_service: "TokenBlacklistService | None" = None,
        two_factor_repository: object | None = None,
    ):
        self.user_repository = user_repository
        self.token_blacklist_service = token_blacklist_service
        self.two_factor_repository = two_factor_repository

    async def _issue_login_tokens(
        self,
        user: User,
        *,
        tfa_verified: bool = False,
        tfa_method: str | None = None,
    ) -> tuple[str, str]:
        session_jti = str(uuid4())
        token_version = user.tokenVersion
        access_token = create_access_token(
            data={
                "sub": user.id,
                "email": user.email,
                "tfaVerified": tfa_verified,
                "tfaMethod": tfa_method,
                "emailVerified": user.isEmailVerified,
                "jti": session_jti,
                "tv": token_version,
            }
        )
        refresh_token = create_refresh_token(
            data={
                "sub": user.id,
                "email": user.email,
                "tfaVerified": tfa_verified,
                "tfaMethod": tfa_method,
                "emailVerified": user.isEmailVerified,
                "jti": session_jti,
                "tv": token_version,
            }
        )
        if self.token_blacklist_service:
            payload = verify_token(refresh_token)
            expires_at = payload.get("exp")
            if expires_at:
                await self.token_blacklist_service.track_user_session(
                    user_id=user.id,
                    jti=session_jti,
                    expires_at=expires_at,
                )
        return access_token, refresh_token

    async def register_user(
        self,
        email: str,
        password: str,
        name: str,
        locale: SupportedLocale | None = None,
        translations: dict | None = None,
    ) -> User:
        """
        Register a new user.

        Args:
            email: User email
            password: Plain text password
            name: User full name

        Returns:
            Created user

        Raises:
            UserAlreadyExistsError: If user with email already exists
        """
        try:
            user = await self.user_repository.create_user(email, password, name)

            # Generate verification token and send verification email
            verification_token = create_email_verification_token({"sub": user.id, "email": email})
            stored_user = await self.user_repository.store_email_verification_token(user.id, verification_token, datetime.now(UTC))
            if stored_user:
                user = stored_user

            try:
                email_service = get_email_service()
                await email_service.send_email_verification_email(
                    to=email,
                    name=name,
                    verification_token=verification_token,
                    user_id=user.id,
                    locale=locale,
                    translations=translations,
                )
            except Exception as e:
                logger.warning(f"Failed to send email verification message: {e}")

            return user
        except UserAlreadyExistsError:
            raise

    async def login_user(self, email: str, password: str) -> LoginResponse:
        """
        Authenticate user and generate tokens.

        Args:
            email: User email
            password: Plain text password

        Returns:
            Login response with tokens and user info

        Raises:
            InvalidCredentialsError: If credentials are invalid
        """
        # Get user by email
        user = await self.user_repository.get_user_by_email(email)
        if not user:
            raise InvalidCredentialsError("Invalid email or password")

        # Verify password
        if not user.verify_password(password):
            raise InvalidCredentialsError("Invalid email or password")

        # Check if user is active
        if not user.isActive:
            raise InvalidCredentialsError("User account is inactive")

        # Generate tokens
        access_token, refresh_token = await self._issue_login_tokens(user)

        return LoginResponse(
            user=UserResponse(**user.to_response()),
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="bearer",
            expiresIn=settings.security.access_token_expires_minutes * 60,
            requiresEmailVerification=not user.isEmailVerified,
        )

    async def refresh_access_token(self, refresh_token: str) -> dict[str, str | int]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            New access and refresh tokens

        Raises:
            InvalidTokenError: If refresh token is invalid
        """
        try:
            payload = verify_token(refresh_token)

            # Verify token type
            if payload.get("type") != "refresh":
                raise InvalidTokenError("Invalid token type")

            if self.token_blacklist_service:
                if await self.token_blacklist_service.is_blacklisted(refresh_token):
                    raise InvalidTokenError("Token has been revoked")
                token_jti = payload.get("jti")
                if token_jti and await self.token_blacklist_service.is_jti_blacklisted(token_jti):
                    raise InvalidTokenError("Session has been revoked")

            # Get user ID
            user_id = payload.get("sub")
            if not user_id:
                raise InvalidTokenError("Invalid token payload")

            # Verify user exists
            user = await self.user_repository.get_user_by_id(user_id)
            if not user or not user.isActive:
                raise InvalidTokenError("User not found or inactive")
            if payload.get("tv", 0) != user.tokenVersion:
                raise InvalidTokenError("Token version mismatch")

            # Preserve 2FA state from refresh token
            old_tfa_verified = payload.get("tfaVerified", False)
            old_tfa_method = payload.get("tfaMethod")

            # Generate new tokens with preserved 2FA state
            # Ensure tfaVerified is bool (not None)
            tfa_verified_bool = old_tfa_verified if old_tfa_verified is not None else False
            new_access_token, new_refresh_token = await self._issue_login_tokens(
                user,
                tfa_verified=tfa_verified_bool,
                tfa_method=old_tfa_method,
            )
            if self.token_blacklist_service:
                old_jti = payload.get("jti")
                old_exp = payload.get("exp")
                if old_jti and old_exp:
                    await self.token_blacklist_service.revoke_session(
                        user_id=user_id,
                        jti=old_jti,
                        expires_at=old_exp,
                        reason="refresh_rotated",
                    )
                if old_exp:
                    await self.token_blacklist_service.blacklist_token(
                        token=refresh_token,
                        expires_at=old_exp,
                        reason="refresh_rotated",
                    )

            return {
                "accessToken": new_access_token,
                "refreshToken": new_refresh_token,
                "tokenType": "bearer",
                "expiresIn": settings.security.access_token_expires_minutes * 60,
            }

        except InvalidTokenError:
            # Re-raise known errors
            raise
        except Exception as e:
            # Log unexpected errors for debugging
            logger.error(f"Unexpected error during token refresh: {e}", exc_info=True)
            raise InvalidTokenError("Invalid or expired refresh token") from e

    async def request_password_reset(
        self,
        email: str,
        locale: SupportedLocale | None = None,
        translations: dict | None = None,
    ) -> bool:
        """
        Generate password reset token for user.

        Args:
            email: User email

        Returns:
            True if token generated successfully, False if user not found

        Note:
            Sends email with reset link. In development mode, also logs token.
        """
        # Get user to get name for email
        user = await self.user_repository.get_user_by_email(email)
        if not user:
            # Return True to prevent email enumeration
            return True

        token = await self.user_repository.generate_reset_token(email)
        if token:
            # Send email with reset link
            try:
                email_service = get_email_service()
                await email_service.send_password_reset_email(
                    to=email,
                    name=user.name,
                    reset_token=token,
                    user_id=user.id,
                    locale=locale,
                    translations=translations,
                )
            except Exception as e:
                logger.error(f"Failed to send password reset email: {e}")

            # In development mode only, also log the token (NEVER in production!)
            environment = os.getenv("ENVIRONMENT", "production").lower()
            if environment == "development":
                logger.warning(f"DEV MODE: Password reset token for {email}: {token}\n" f"Reset link: /reset-password?token={token}")
            else:
                # In production, just log that email was sent without exposing token
                logger.info(f"Password reset email sent to {email}")
            return True
        return False

    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset password using reset token.

        Args:
            token: Password reset token
            new_password: New password

        Returns:
            True if password reset successfully

        Raises:
            InvalidTokenError: If token is invalid
        """
        success = await self.user_repository.reset_password_with_token(token, new_password)
        if not success:
            raise InvalidTokenError("Invalid or expired reset token")
        try:
            payload = verify_token(token)
            user_id = payload.get("sub")
            if user_id:
                await self.user_repository.increment_token_version(user_id)
                if self.token_blacklist_service:
                    await self.token_blacklist_service.blacklist_all_user_tokens(
                        user_id=user_id,
                        reason="password_reset",
                    )
        except Exception:
            logger.warning("Failed to revoke sessions after password reset", exc_info=True)
        return True

    async def resend_email_verification(
        self,
        email: str,
        locale: SupportedLocale | None = None,
        translations: dict | None = None,
    ) -> bool:
        """Resend email verification message."""
        user = await self.user_repository.get_user_by_email(email)
        if not user:
            return True  # Do not leak existence

        if user.isEmailVerified:
            return True

        token = create_email_verification_token({"sub": user.id, "email": user.email})
        await self.user_repository.store_email_verification_token(user.id, token, datetime.now(UTC))

        try:
            email_service = get_email_service()
            await email_service.send_email_verification_email(
                to=user.email,
                name=user.name,
                verification_token=token,
                user_id=user.id,
                locale=locale,
                translations=translations,
            )
        except Exception as e:
            logger.warning(f"Failed to send email verification email: {e}")

        return True

    async def verify_email(
        self,
        token: str,
        locale: SupportedLocale | None = None,
        translations: dict | None = None,
    ) -> User:
        """Verify email using provided token."""
        user = await self.user_repository.verify_email_by_token(token)
        if not user:
            raise InvalidTokenError("Invalid or expired verification token")

        # Send welcome email after successful verification
        try:
            email_service = get_email_service()
            await email_service.send_welcome_email(
                to=user.email,
                name=user.name,
                user_id=user.id,
                locale=locale,
                translations=translations,
            )
        except Exception as e:
            logger.warning(f"Failed to send welcome email post verification: {e}")

        return user

    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
        ip_address: str | None = None,
        locale: SupportedLocale | None = None,
        translations: dict | None = None,
    ) -> bool:
        """
        Change user password.

        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            ip_address: IP address where change occurred (optional)

        Returns:
            True if password changed successfully

        Raises:
            InvalidCredentialsError: If current password is incorrect
            UserNotFoundError: If user not found
        """
        success = await self.user_repository.change_password(user_id, current_password, new_password)
        if not success:
            user = await self.user_repository.get_user_by_id(user_id)
            if not user:
                raise UserNotFoundError("User not found")
            raise InvalidCredentialsError("Current password is incorrect")

        await self.user_repository.increment_token_version(user_id)
        if self.token_blacklist_service:
            await self.token_blacklist_service.blacklist_all_user_tokens(
                user_id=user_id,
                reason="password_changed",
            )

        user = await self.user_repository.get_user_by_id(user_id)

        # Send password changed notification email
        try:
            email_service = get_email_service()
            if user:
                await email_service.send_password_changed_email(
                    to=user.email,
                    name=user.name,
                    ip_address=ip_address,
                    user_id=user_id,
                    locale=locale,
                    translations=translations,
                )
        except Exception as e:
            # Log error but don't fail password change if email fails
            logger.warning(f"Failed to send password changed email: {e}")

        return True

    async def delete_account(
        self,
        user_id: str,
        password: str | None = None,
        confirmation: str = "",
        soft_delete: bool = True,
        locale: SupportedLocale | None = None,
        translations: dict | None = None,
    ) -> bool:
        """
        Delete user account.

        Args:
            user_id: User ID to delete
            password: Current password for verification (optional but recommended)
            confirmation: Confirmation phrase (e.g., 'DELETE' or user email)
            soft_delete: If True, performs soft delete (default). If False, hard delete.

        Returns:
            True if account deleted successfully

        Raises:
            InvalidCredentialsError: If password is provided but incorrect
            UserNotFoundError: If user not found
        """
        # Get user to verify existence and for password verification
        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError("User not found")

        # Verify password if provided
        if password:
            if not user.verify_password(password):
                raise InvalidCredentialsError("Password is incorrect")

        # Verify confirmation phrase (should be 'DELETE' or user email)
        if confirmation.upper() != "DELETE" and confirmation.lower() != user.email.lower():
            raise InvalidCredentialsError("Confirmation phrase is incorrect")

        # Store user email and name before deletion for email notification
        user_email = user.email
        user_name = user.name

        # Delete user account
        if self.two_factor_repository:
            two_factor_repository = cast("TwoFactorRepositoryInterface", self.two_factor_repository)
            try:
                await two_factor_repository.disable_totp(user_id)
                await two_factor_repository.delete_all_passkeys(user_id)
            except Exception:
                logger.warning(
                    "Failed to cleanup 2FA artifacts during account deletion",
                    exc_info=True,
                )
        await self.user_repository.delete_all_oauth_connections(user_id)
        success = await self.user_repository.delete_user(user_id, soft_delete=soft_delete)
        if not success:
            raise UserNotFoundError("Failed to delete user account")

        if self.token_blacklist_service:
            await self.token_blacklist_service.blacklist_all_user_tokens(
                user_id=user_id,
                reason="account_deleted",
            )

        # Send account deletion confirmation email (before account is deleted)
        try:
            email_service = get_email_service()
            await email_service.send_account_deleted_email(
                to=user_email,
                name=user_name,
                user_id=user_id,
                locale=locale,
                translations=translations,
            )
        except Exception as e:
            # Log error but don't fail deletion if email fails
            logger.warning(f"Failed to send account deletion email: {e}")

        # TODO: Invalidate all user sessions/tokens
        # TODO: Delete related data (2FA, passkeys, etc.)

        return True

    async def _resolve_oauth_user(self, provider: str, user_info: dict) -> User:
        """
        Look up, link, or create the user for an OAuth login, without issuing tokens.

        Args:
            provider: OAuth provider name (google, github, etc.)
            user_info: User information from OAuth provider (camelCase format from OAuthUserInfo)

        Returns:
            The resolved user

        Raises:
            ValueError: If provider or user_info is invalid
            InvalidCredentialsError: If the resolved user account is inactive
        """
        if not provider or not user_info:
            raise ValueError("Provider and user_info are required")

        email = user_info.get("email")
        if not email:
            raise ValueError("Email is required from OAuth provider")

        # Extract provider_id - support both camelCase (providerId) and snake_case (provider_id, id, sub)
        provider_id = user_info.get("providerId") or user_info.get("provider_id") or user_info.get("id") or user_info.get("sub") or ""

        # Extract avatar URL - support both camelCase (avatarUrl) and snake_case (avatar_url, picture)
        avatar_url = user_info.get("avatarUrl") or user_info.get("avatar_url") or user_info.get("picture")

        # Extract name
        name = user_info.get("name", email.split("@")[0])

        # Check if user already exists by OAuth provider
        existing_user_by_provider = await self.user_repository.get_user_by_oauth_provider(provider, provider_id)

        if existing_user_by_provider:
            # User exists with this OAuth provider - use existing user
            # IMPORTANT: We do NOT update user's name/avatar from OAuth here to preserve
            # any manual changes the user made in their profile (e.g., custom avatar, display name)
            user = existing_user_by_provider
        else:
            # Check if user exists by email
            existing_user = await self.user_repository.get_user_by_email(email)

            if existing_user:
                # User exists with this email - link OAuth to existing account
                # This allows users to add OAuth to existing password-based accounts
                # IMPORTANT: We do NOT update user's name/avatar from OAuth here to preserve
                # any manual changes the user made in their profile
                user = existing_user
            else:
                # Create new OAuth user - only for new users do we set initial data from OAuth
                user = await self.user_repository.create_oauth_user(
                    email=email,
                    name=name,
                    provider=provider,
                    provider_id=provider_id,
                    avatar_url=avatar_url,
                )

        if not user.isActive:
            raise InvalidCredentialsError("User account is inactive")

        # Create or update OAuth connection in oauth_connections table
        await self.user_repository.create_oauth_connection(
            user_id=user.id,
            provider=provider,
            provider_id=provider_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
        )

        return user

    async def login_with_oauth(self, provider: str, user_info: dict) -> LoginResponse:
        """
        Login or register user via OAuth.

        Routes through ``_issue_login_tokens`` (same as password login) so OAuth
        sessions get a tracked `jti`, `tv`, and `emailVerified` claim like every
        other login path.

        Args:
            provider: OAuth provider name (google, github, etc.)
            user_info: User information from OAuth provider (camelCase format from OAuthUserInfo)

        Returns:
            LoginResponse with tokens and user info

        Raises:
            ValueError: If provider or user_info is invalid
            InvalidCredentialsError: If the resolved user account is inactive
        """
        user = await self._resolve_oauth_user(provider, user_info)
        access_token, refresh_token = await self._issue_login_tokens(user)

        return LoginResponse(
            user=UserResponse(**user.to_response()),
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="bearer",
            expiresIn=settings.security.access_token_expires_minutes * 60,
            requiresEmailVerification=False,  # OAuth emails are pre-verified
        )
