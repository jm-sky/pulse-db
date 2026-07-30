"""Unit tests for authentication service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.auth.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.modules.auth.models import User
from app.modules.auth.service import AuthService
from app.modules.auth.types.repository import UserRepositoryInterface


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Create a mock user repository."""
    return AsyncMock(spec=UserRepositoryInterface)


@pytest.fixture
def sample_user() -> User:
    """Create a sample user for testing."""
    from app.modules.auth.auth_utils import get_password_hash

    user = User(
        id="user123",
        email="test@example.com",
        name="Test User",
        hashedPassword=get_password_hash("password123"),  # Real hash for testing
        isActive=True,
        isEmailVerified=False,
        createdAt=datetime.now(UTC),
    )
    return user


@pytest.fixture
def auth_service(mock_repository: AsyncMock) -> AuthService:
    """Create AuthService instance with mocked repository."""
    return AuthService(user_repository=mock_repository)


@pytest.fixture
def mock_blacklist_service() -> AsyncMock:
    """Create a mock blacklist service."""
    service = AsyncMock()
    service.is_blacklisted.return_value = False
    service.is_jti_blacklisted.return_value = False
    service.blacklist_all_user_tokens.return_value = 0
    return service


@pytest.fixture
def auth_service_with_blacklist(
    mock_repository: AsyncMock,
    mock_blacklist_service: AsyncMock,
) -> AuthService:
    """Create AuthService with blacklist service enabled."""
    return AuthService(
        user_repository=mock_repository,
        token_blacklist_service=mock_blacklist_service,
    )


class TestRegisterUser:
    """Tests for user registration."""

    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service: AuthService, mock_repository: AsyncMock, sample_user: User) -> None:
        """Test successful user registration."""
        mock_repository.create_user.return_value = sample_user
        mock_repository.store_email_verification_token.return_value = sample_user

        with patch("app.modules.auth.service.get_email_service") as mock_email_service:
            mock_email_service.return_value.send_email_verification_email = AsyncMock()

            user = await auth_service.register_user(
                email="test@example.com",
                password="password123",
                name="Test User",
            )

            assert user.id == "user123"
            assert user.email == "test@example.com"
            mock_repository.create_user.assert_called_once()
            mock_repository.store_email_verification_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_already_exists(self, auth_service: AuthService, mock_repository: AsyncMock) -> None:
        """Test registration with existing email."""
        mock_repository.create_user.side_effect = UserAlreadyExistsError()

        with pytest.raises(UserAlreadyExistsError):
            await auth_service.register_user(
                email="existing@example.com",
                password="password123",
                name="Test User",
            )


class TestLoginUser:
    """Tests for user login."""

    @pytest.mark.asyncio
    async def test_login_user_success(self, auth_service: AuthService, mock_repository: AsyncMock, sample_user: User) -> None:
        """Test successful user login."""
        mock_repository.get_user_by_email.return_value = sample_user

        response = await auth_service.login_user(
            email="test@example.com",
            password="password123",
        )

        assert response.user.email == "test@example.com"
        assert response.accessToken is not None
        assert response.refreshToken is not None
        assert response.tokenType == "bearer"
        mock_repository.get_user_by_email.assert_called_once_with("test@example.com")

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, auth_service: AuthService, mock_repository: AsyncMock) -> None:
        """Test login with non-existent user."""
        mock_repository.get_user_by_email.return_value = None

        with pytest.raises(InvalidCredentialsError, match="Invalid email or password"):
            await auth_service.login_user(
                email="nonexistent@example.com",
                password="password123",
            )

    @pytest.mark.asyncio
    async def test_login_user_wrong_password(self, auth_service: AuthService, mock_repository: AsyncMock, sample_user: User) -> None:
        """Test login with wrong password."""
        mock_repository.get_user_by_email.return_value = sample_user
        # sample_user has password "password123", so "wrong_password" will fail

        with pytest.raises(InvalidCredentialsError, match="Invalid email or password"):
            await auth_service.login_user(
                email="test@example.com",
                password="wrong_password",
            )

    @pytest.mark.asyncio
    async def test_login_user_inactive(self, auth_service: AuthService, mock_repository: AsyncMock, sample_user: User) -> None:
        """Test login with inactive user."""
        sample_user.isActive = False
        mock_repository.get_user_by_email.return_value = sample_user

        with pytest.raises(InvalidCredentialsError, match="User account is inactive"):
            await auth_service.login_user(
                email="test@example.com",
                password="password123",
            )


class TestRefreshAccessToken:
    """Tests for token refresh."""

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, auth_service: AuthService, mock_repository: AsyncMock, sample_user: User) -> None:
        """Test successful token refresh."""
        from app.modules.auth.auth_utils import create_refresh_token

        refresh_token = create_refresh_token(data={"sub": "user123", "email": "test@example.com"})
        mock_repository.get_user_by_id.return_value = sample_user

        result = await auth_service.refresh_access_token(refresh_token)

        assert "accessToken" in result
        assert "refreshToken" in result
        assert result["tokenType"] == "bearer"
        mock_repository.get_user_by_id.assert_called_once_with("user123")

    @pytest.mark.asyncio
    async def test_refresh_access_token_preserves_tv_and_jti(self, auth_service: AuthService, mock_repository: AsyncMock, sample_user: User) -> None:
        """Refreshed tokens must carry `tv`/`jti` like a fresh login.

        Regression test: refresh_access_token used to mint the new
        access/refresh tokens via the low-level create_access_token/
        create_refresh_token builders directly, omitting `tv` and `jti`
        entirely. For any user whose tokenVersion isn't 0 (e.g. after a
        password reset), the very first refresh cycle would silently
        produce tokens that _verify_user_token rejects with 401 "Token has
        been revoked" — logging the user out shortly after a successful
        login.

        pulse-db already routes refresh through _issue_login_tokens;
        this test locks that behavior in.
        """
        from app.modules.auth.auth_utils import create_refresh_token, verify_token

        sample_user.tokenVersion = 5
        refresh_token = create_refresh_token(data={"sub": "user123", "email": "test@example.com", "tv": 5})
        mock_repository.get_user_by_id.return_value = sample_user

        result = await auth_service.refresh_access_token(refresh_token)

        access_payload = verify_token(str(result["accessToken"]))
        assert access_payload["tv"] == 5
        assert access_payload["jti"]

        refresh_payload = verify_token(str(result["refreshToken"]))
        assert refresh_payload["tv"] == 5
        assert refresh_payload["jti"]

    @pytest.mark.asyncio
    async def test_refresh_access_token_invalid_token(self, auth_service: AuthService) -> None:
        """Test refresh with invalid token."""
        with pytest.raises(InvalidTokenError):
            await auth_service.refresh_access_token("invalid_token")

    @pytest.mark.asyncio
    async def test_refresh_access_token_wrong_type(self, auth_service: AuthService) -> None:
        """Test refresh with access token instead of refresh token."""
        from app.modules.auth.auth_utils import create_access_token

        access_token = create_access_token(data={"sub": "user123"})

        with pytest.raises(InvalidTokenError, match="Invalid token type"):
            await auth_service.refresh_access_token(access_token)

    @pytest.mark.asyncio
    async def test_refresh_access_token_user_not_found(self, auth_service: AuthService, mock_repository: AsyncMock) -> None:
        """Test refresh when user doesn't exist."""
        from app.modules.auth.auth_utils import create_refresh_token

        refresh_token = create_refresh_token(data={"sub": "user123"})
        mock_repository.get_user_by_id.return_value = None

        with pytest.raises(InvalidTokenError):
            await auth_service.refresh_access_token(refresh_token)

    @pytest.mark.asyncio
    async def test_refresh_access_token_rejects_token_version_mismatch(
        self,
        auth_service_with_blacklist: AuthService,
        mock_repository: AsyncMock,
        sample_user: User,
    ) -> None:
        """Test refresh rejects tokens from previous token version."""
        from app.modules.auth.auth_utils import create_refresh_token

        sample_user.tokenVersion = 2
        refresh_token = create_refresh_token(data={"sub": "user123", "tv": 1})
        mock_repository.get_user_by_id.return_value = sample_user

        with pytest.raises(InvalidTokenError, match="Token version mismatch"):
            await auth_service_with_blacklist.refresh_access_token(refresh_token)

    @pytest.mark.asyncio
    async def test_refresh_access_token_rejects_revoked_session(self, mock_repository: AsyncMock, sample_user: User) -> None:
        """A refresh token whose session jti was revoked (e.g. via logout)
        must not be usable to mint a new token pair.

        Regression test: refresh_access_token must consult the JTI
        blacklist, so revoking a session on logout actually stops the
        refresh token (which shares the same jti) from minting new tokens.
        """
        from app.modules.auth.auth_utils import create_refresh_token

        mock_blacklist = AsyncMock()
        mock_blacklist.is_blacklisted.return_value = False
        mock_blacklist.is_jti_blacklisted.return_value = True
        service = AuthService(user_repository=mock_repository, token_blacklist_service=mock_blacklist)

        refresh_token = create_refresh_token(data={"sub": "user123", "email": "test@example.com", "jti": "revoked-jti"})
        mock_repository.get_user_by_id.return_value = sample_user

        with pytest.raises(InvalidTokenError, match="revoked"):
            await service.refresh_access_token(refresh_token)

        mock_blacklist.is_jti_blacklisted.assert_awaited_once_with("revoked-jti")

    @pytest.mark.asyncio
    async def test_refresh_access_token_allows_non_revoked_session(self, mock_repository: AsyncMock, sample_user: User) -> None:
        """A refresh token whose jti is not blacklisted still refreshes normally."""
        from app.modules.auth.auth_utils import create_refresh_token

        mock_blacklist = AsyncMock()
        mock_blacklist.is_blacklisted.return_value = False
        mock_blacklist.is_jti_blacklisted.return_value = False
        service = AuthService(user_repository=mock_repository, token_blacklist_service=mock_blacklist)

        refresh_token = create_refresh_token(data={"sub": "user123", "email": "test@example.com", "jti": "active-jti"})
        mock_repository.get_user_by_id.return_value = sample_user

        result = await service.refresh_access_token(refresh_token)

        assert "accessToken" in result


class TestPasswordReset:
    """Tests for password reset functionality."""

    @pytest.mark.asyncio
    async def test_request_password_reset_success(self, auth_service: AuthService, mock_repository: AsyncMock, sample_user: User) -> None:
        """Test successful password reset request."""
        mock_repository.get_user_by_email.return_value = sample_user
        mock_repository.generate_reset_token.return_value = "reset_token_123"

        with patch("app.modules.auth.service.get_email_service") as mock_email_service:
            mock_email_service.return_value.send_password_reset_email = AsyncMock()

            result = await auth_service.request_password_reset("test@example.com")

            assert result is True
            mock_repository.get_user_by_email.assert_called_once()
            mock_repository.generate_reset_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_password_reset_user_not_found(self, auth_service: AuthService, mock_repository: AsyncMock) -> None:
        """Test password reset request for non-existent user."""
        mock_repository.get_user_by_email.return_value = None

        # Should return True to prevent email enumeration
        result = await auth_service.request_password_reset("nonexistent@example.com")
        assert result is True

    @pytest.mark.asyncio
    async def test_reset_password_success(self, auth_service: AuthService, mock_repository: AsyncMock) -> None:
        """Test successful password reset."""
        mock_repository.reset_password_with_token.return_value = True

        result = await auth_service.reset_password("reset_token_123", "new_password")

        assert result is True
        mock_repository.reset_password_with_token.assert_called_once_with("reset_token_123", "new_password")

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, auth_service: AuthService, mock_repository: AsyncMock) -> None:
        """Test password reset with invalid token."""
        mock_repository.reset_password_with_token.return_value = False

        with pytest.raises(InvalidTokenError, match="Invalid or expired reset token"):
            await auth_service.reset_password("invalid_token", "new_password")


class TestChangePassword:
    """Tests for password change functionality."""

    @pytest.mark.asyncio
    async def test_change_password_success(self, auth_service: AuthService, mock_repository: AsyncMock, sample_user: User) -> None:
        """Test successful password change."""
        mock_repository.change_password.return_value = True
        mock_repository.get_user_by_id.return_value = sample_user

        with patch("app.modules.auth.service.get_email_service") as mock_email_service:
            mock_email_service.return_value.send_password_changed_email = AsyncMock()

            result = await auth_service.change_password(
                user_id="user123",
                current_password="old_password",
                new_password="new_password",
            )

            assert result is True
            mock_repository.change_password.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_wrong_current_password(self, auth_service: AuthService, mock_repository: AsyncMock, sample_user: User) -> None:
        """Test password change with wrong current password."""
        mock_repository.change_password.return_value = False
        mock_repository.get_user_by_id.return_value = sample_user

        with pytest.raises(InvalidCredentialsError, match="Current password is incorrect"):
            await auth_service.change_password(
                user_id="user123",
                current_password="wrong_password",
                new_password="new_password",
            )

    @pytest.mark.asyncio
    async def test_change_password_user_not_found(self, auth_service: AuthService, mock_repository: AsyncMock) -> None:
        """Test password change for non-existent user."""
        mock_repository.change_password.return_value = False
        mock_repository.get_user_by_id.return_value = None

        with pytest.raises(UserNotFoundError, match="User not found"):
            await auth_service.change_password(
                user_id="nonexistent",
                current_password="old_password",
                new_password="new_password",
            )


class TestEmailVerification:
    """Tests for email verification functionality."""

    @pytest.mark.asyncio
    async def test_verify_email_success(self, auth_service: AuthService, mock_repository: AsyncMock, sample_user: User) -> None:
        """Test successful email verification."""
        mock_repository.verify_email_by_token.return_value = sample_user

        with patch("app.modules.auth.service.get_email_service") as mock_email_service:
            mock_email_service.return_value.send_welcome_email = AsyncMock()

            user = await auth_service.verify_email("verification_token_123")

            assert user.id == "user123"
            mock_repository.verify_email_by_token.assert_called_once_with("verification_token_123")

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, auth_service: AuthService, mock_repository: AsyncMock) -> None:
        """Test email verification with invalid token."""
        mock_repository.verify_email_by_token.return_value = None

        with pytest.raises(InvalidTokenError, match="Invalid or expired verification token"):
            await auth_service.verify_email("invalid_token")

    @pytest.mark.asyncio
    async def test_resend_email_verification_success(self, auth_service: AuthService, mock_repository: AsyncMock, sample_user: User) -> None:
        """Test successful resend of email verification."""
        mock_repository.get_user_by_email.return_value = sample_user
        mock_repository.store_email_verification_token.return_value = sample_user

        with patch("app.modules.auth.service.get_email_service") as mock_email_service:
            mock_email_service.return_value.send_email_verification_email = AsyncMock()

            result = await auth_service.resend_email_verification("test@example.com")

            assert result is True
            mock_repository.get_user_by_email.assert_called_once()


class TestLoginWithOAuth:
    """Tests for OAuth login (issue 036 / ops 014: must reuse the same
    token-issuing machinery as password login — jti, tv, session tracking)."""

    @pytest.mark.asyncio
    async def test_login_with_oauth_new_user_issues_full_tokens(self, auth_service: AuthService, mock_repository: AsyncMock, sample_user: User) -> None:
        from app.modules.auth.auth_utils import verify_token

        mock_repository.get_user_by_oauth_provider.return_value = None
        mock_repository.get_user_by_email.return_value = None
        mock_repository.create_oauth_user.return_value = sample_user
        mock_repository.create_oauth_connection.return_value = None

        response = await auth_service.login_with_oauth(
            "google",
            {
                "email": "test@example.com",
                "providerId": "provider-123",
                "name": "Test User",
            },
        )

        assert response.accessToken is not None
        assert response.refreshToken is not None
        assert response.requiresEmailVerification is False

        payload = verify_token(response.accessToken)
        assert payload["jti"]
        assert payload["tv"] == sample_user.tokenVersion
        assert payload["emailVerified"] == sample_user.isEmailVerified
        mock_repository.create_oauth_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_with_oauth_survives_token_version_bump(self, auth_service: AuthService, mock_repository: AsyncMock, sample_user: User) -> None:
        """A user whose tokenVersion was bumped (e.g. password change) must
        still get a token carrying the *current* tv, not a stale default of 0
        that the tv-enforcement dependency would immediately reject."""
        from app.modules.auth.auth_utils import verify_token

        sample_user.tokenVersion = 5
        mock_repository.get_user_by_oauth_provider.return_value = sample_user
        mock_repository.create_oauth_connection.return_value = None

        response = await auth_service.login_with_oauth("google", {"email": "test@example.com", "providerId": "provider-123"})

        payload = verify_token(response.accessToken)
        assert payload["tv"] == 5

    @pytest.mark.asyncio
    async def test_login_with_oauth_missing_email_raises(self, auth_service: AuthService) -> None:
        with pytest.raises(ValueError, match="Email is required"):
            await auth_service.login_with_oauth("google", {"providerId": "abc"})

    @pytest.mark.asyncio
    async def test_login_with_oauth_missing_provider_raises(self, auth_service: AuthService) -> None:
        with pytest.raises(ValueError, match="Provider and user_info are required"):
            await auth_service.login_with_oauth("", {"email": "test@example.com"})


class TestDeleteAndOAuthHardening:
    """Tests for account deletion and OAuth hardening flows."""

    @pytest.mark.asyncio
    async def test_delete_account_cleans_up_auth_artifacts(
        self,
        auth_service_with_blacklist: AuthService,
        mock_repository: AsyncMock,
        sample_user: User,
        mock_blacklist_service: AsyncMock,
    ) -> None:
        """Test deletion triggers cleanup/revoke methods."""
        mock_repository.get_user_by_id.return_value = sample_user
        mock_repository.delete_user.return_value = True
        mock_repository.delete_all_oauth_connections.return_value = 1

        with patch("app.modules.auth.service.get_email_service") as mock_email_service:
            mock_email_service.return_value.send_account_deleted_email = AsyncMock()

            result = await auth_service_with_blacklist.delete_account(
                user_id=sample_user.id,
                confirmation="DELETE",
            )

        assert result is True
        mock_repository.delete_all_oauth_connections.assert_called_once_with(sample_user.id)
        mock_blacklist_service.blacklist_all_user_tokens.assert_called_once_with(
            user_id=sample_user.id,
            reason="account_deleted",
        )

    @pytest.mark.asyncio
    async def test_login_with_oauth_rejects_inactive_user(self, auth_service: AuthService, mock_repository: AsyncMock, sample_user: User) -> None:
        """Test OAuth login does not issue tokens for inactive users."""
        sample_user.isActive = False
        mock_repository.get_user_by_oauth_provider.return_value = sample_user

        with pytest.raises(InvalidCredentialsError, match="User account is inactive"):
            await auth_service.login_with_oauth(
                "google",
                {
                    "email": "test@example.com",
                    "providerId": "provider-user-1",
                },
            )
