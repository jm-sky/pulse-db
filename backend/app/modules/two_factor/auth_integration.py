"""Auth integration for 2FA support.

This module provides AuthServiceWith2FA that extends AuthService to check
for 2FA after password verification. It's backward compatible - users without
2FA get normal login flow, users with 2FA get TwoFactorRequiredResponse.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.auth.token_blacklist import TokenBlacklistService
from app.core.config import settings
from app.modules.auth.models import User
from app.modules.auth.repositories import get_user_repository
from app.modules.auth.schemas import LoginResponse, UserResponse
from app.modules.auth.service import AuthService
from app.modules.auth.types.repository import UserRepositoryInterface

from .repositories import get_two_factor_repository
from .schemas import TwoFactorRequiredResponse
from .service import TwoFactorService
from .types.repository import TwoFactorRepositoryInterface


class AuthServiceWith2FA(AuthService):
    """
    Extended AuthService that checks 2FA after login.

    Usage: Replace AuthService with this in dependencies when 2FA module is installed.
    This maintains backward compatibility - users without 2FA get normal login.
    """

    def __init__(
        self,
        user_repository: UserRepositoryInterface,
        two_factor_service: TwoFactorService,
        token_blacklist_service: TokenBlacklistService | None = None,
    ):
        super().__init__(
            user_repository=user_repository,
            token_blacklist_service=token_blacklist_service,
            two_factor_repository=two_factor_service.repository,
        )
        self.two_factor_service = two_factor_service

    async def _build_two_factor_challenge(self, user: User) -> TwoFactorRequiredResponse:
        """Build the 2FA challenge response for a user with 2FA enabled."""
        from .auth_utils import create_two_factor_token

        two_factor_token = create_two_factor_token(
            data={
                "sub": user.id,
                "email": user.email,
            }
        )
        methods = await self.two_factor_service.get_available_methods(user.id)
        preferred = await self.two_factor_service.get_preferred_method(user.id)

        # Get expiration from token
        import jwt

        token_payload = jwt.decode(
            two_factor_token,
            settings.security.secret_key,
            algorithms=[settings.security.jwt_algorithm],
            options={"verify_exp": False},
        )
        from datetime import UTC, datetime

        expires_at = datetime.fromtimestamp(token_payload["exp"], tz=UTC)

        return TwoFactorRequiredResponse(
            requiresTwoFactor=True,
            twoFactorToken=two_factor_token,
            methods=methods,
            preferredMethod=preferred,
            allowBackupCodes=True,  # If TOTP enabled
            expiresAt=expires_at,
        )

    async def login_user(self, email: str, password: str) -> LoginResponse | TwoFactorRequiredResponse:  # type: ignore[override]
        """Login with 2FA check.

        If user has 2FA enabled, returns TwoFactorRequiredResponse instead of tokens.
        Otherwise, returns normal LoginResponse with tokens.
        """
        from app.modules.auth.auth_utils import verify_password
        from app.modules.auth.exceptions import InvalidCredentialsError

        # Get user by email
        user = await self.user_repository.get_user_by_email(email)
        if not user:
            raise InvalidCredentialsError("Invalid email or password")

        # Verify password (hashedPassword is guaranteed non-empty for password auth)
        if not user.hashedPassword or not verify_password(password, user.hashedPassword):
            raise InvalidCredentialsError("Invalid email or password")

        # Check if user is active
        if not user.isActive:
            raise InvalidCredentialsError("User account is inactive")

        # Check if user has 2FA enabled
        if await self.two_factor_service.has_two_factor_enabled(user.id):
            return await self._build_two_factor_challenge(user)

        # No 2FA - generate tokens via parent helper (handles JTI tracking)
        access_token, refresh_token = await self._issue_login_tokens(user)

        return LoginResponse(
            user=UserResponse(**user.to_response()),
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="bearer",
            expiresIn=settings.security.access_token_expires_minutes * 60,
            requiresEmailVerification=not user.isEmailVerified,
        )

    async def login_with_oauth(self, provider: str, user_info: dict) -> LoginResponse | TwoFactorRequiredResponse:  # type: ignore[override]
        """Login or register user via OAuth, honoring 2FA like password login.

        If the resolved user has 2FA enabled, returns TwoFactorRequiredResponse
        instead of tokens (same challenge flow as ``login_user``).
        """
        user = await self._resolve_oauth_user(provider, user_info)

        if await self.two_factor_service.has_two_factor_enabled(user.id):
            return await self._build_two_factor_challenge(user)

        access_token, refresh_token = await self._issue_login_tokens(user)

        return LoginResponse(
            user=UserResponse(**user.to_response()),
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="bearer",
            expiresIn=settings.security.access_token_expires_minutes * 60,
            requiresEmailVerification=False,  # OAuth emails are pre-verified
        )


def get_auth_service_with_2fa(
    user_repository: Annotated[UserRepositoryInterface, Depends(get_user_repository)],
    two_factor_repository: Annotated[TwoFactorRepositoryInterface, Depends(get_two_factor_repository)],
    token_blacklist_service: TokenBlacklistService | None = None,
) -> AuthServiceWith2FA:
    """
    FastAPI dependency for AuthServiceWith2FA.

    Usage in your auth router (replace get_auth_service):
        from app.modules.two_factor.auth_integration import get_auth_service_with_2fa as get_auth_service

        @router.post("/login")
        async def login(
            credentials: UserLogin,
            auth_service: AuthServiceWith2FA = Depends(get_auth_service),
        ):
            return await auth_service.login_user(credentials.email, credentials.password)

    Note: This is optional. You can continue using the regular AuthService
    if you don't want 2FA integration. This provides backward compatibility.

    The return type is LoginResponse | TwoFactorRequiredResponse (union type).
    Frontend should check for requiresTwoFactor field to determine next step.
    """
    two_factor_service = TwoFactorService(repository=two_factor_repository)
    return AuthServiceWith2FA(
        user_repository=user_repository,
        two_factor_service=two_factor_service,
        token_blacklist_service=token_blacklist_service,
    )
