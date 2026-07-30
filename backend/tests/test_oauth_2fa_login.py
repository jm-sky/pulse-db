"""Unit tests for OAuth login honoring 2FA (issue 036 / ops 014).

Regression tests for: `AuthService.login_with_oauth` used to mint tokens via
the low-level builders directly, bypassing session tracking, token-version
enforcement, and 2FA entirely. `AuthServiceWith2FA` (the service actually
wired up when the 2FA module is installed) additionally needs to check 2FA
for OAuth logins the same way it already does for password logins, instead
of silently letting 2FA-enabled accounts skip the challenge.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.modules.auth.auth_utils import verify_token
from app.modules.auth.models import User
from app.modules.auth.types.repository import UserRepositoryInterface
from app.modules.two_factor.auth_integration import AuthServiceWith2FA
from app.modules.two_factor.schemas import TwoFactorRequiredResponse
from app.modules.two_factor.service import TwoFactorService
from app.modules.two_factor.types.repository import TwoFactorRepositoryInterface


@pytest.fixture
def mock_user_repository() -> AsyncMock:
    return AsyncMock(spec=UserRepositoryInterface)


@pytest.fixture
def mock_two_factor_repository() -> AsyncMock:
    return AsyncMock(spec=TwoFactorRepositoryInterface)


@pytest.fixture
def sample_user() -> User:
    return User(
        id="user-123",
        email="test@example.com",
        name="Test User",
        hashedPassword=None,
        isActive=True,
        isEmailVerified=True,
        createdAt=datetime.now(UTC),
    )


@pytest.fixture
def auth_service(mock_user_repository: AsyncMock, mock_two_factor_repository: AsyncMock) -> AuthServiceWith2FA:
    two_factor_service = TwoFactorService(repository=mock_two_factor_repository, challenge_store=None)
    return AuthServiceWith2FA(
        user_repository=mock_user_repository,
        two_factor_service=two_factor_service,
    )


class TestOAuthLoginWithout2FA:
    @pytest.mark.asyncio
    async def test_oauth_login_without_2fa_issues_tokens(
        self,
        auth_service: AuthServiceWith2FA,
        mock_user_repository: AsyncMock,
        sample_user: User,
    ) -> None:
        mock_user_repository.get_user_by_oauth_provider.return_value = sample_user
        mock_user_repository.create_oauth_connection.return_value = None
        auth_service.two_factor_service.has_two_factor_enabled = AsyncMock(return_value=False)  # type: ignore[method-assign]

        response = await auth_service.login_with_oauth("github", {"email": "test@example.com", "providerId": "gh-1"})

        assert not hasattr(response, "requiresTwoFactor")
        assert response.accessToken
        payload = verify_token(response.accessToken)
        assert payload["jti"]
        assert payload["tv"] == sample_user.tokenVersion


class TestOAuthLoginWith2FA:
    @pytest.mark.asyncio
    async def test_oauth_login_with_2fa_returns_challenge_not_tokens(
        self,
        auth_service: AuthServiceWith2FA,
        mock_user_repository: AsyncMock,
        sample_user: User,
    ) -> None:
        """Before the fix, OAuth login never checked 2FA at all — a user who
        enabled 2FA would be logged in immediately via OAuth with no challenge."""
        mock_user_repository.get_user_by_oauth_provider.return_value = sample_user
        mock_user_repository.create_oauth_connection.return_value = None
        auth_service.two_factor_service.has_two_factor_enabled = AsyncMock(return_value=True)  # type: ignore[method-assign]
        auth_service.two_factor_service.get_available_methods = AsyncMock(return_value=["totp"])  # type: ignore[method-assign]
        auth_service.two_factor_service.get_preferred_method = AsyncMock(return_value="totp")  # type: ignore[method-assign]

        result = await auth_service.login_with_oauth("github", {"email": "test@example.com", "providerId": "gh-1"})

        assert isinstance(result, TwoFactorRequiredResponse)
        assert result.requiresTwoFactor is True
        assert result.twoFactorToken
