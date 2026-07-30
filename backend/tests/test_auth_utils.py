"""Unit tests for authentication utilities."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import settings
from app.modules.auth.auth_utils import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.modules.auth.exceptions import ExpiredTokenError, InvalidTokenError


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_get_password_hash_returns_string(self) -> None:
        """Test that password hash is returned as string."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_get_password_hash_different_for_same_password(self) -> None:
        """Test that same password produces different hashes (salt)."""
        password = "test_password_123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        # Hashes should be different due to salt
        assert hash1 != hash2

    def test_verify_password_correct(self) -> None:
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self) -> None:
        """Test password verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self) -> None:
        """Test password verification with empty password."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        assert verify_password("", hashed) is False


class TestTokenCreation:
    """Tests for JWT token creation functions."""

    def test_create_access_token_returns_string(self) -> None:
        """Test that access token is returned as string."""
        token = create_access_token(data={"sub": "user123"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_contains_user_id(self) -> None:
        """Test that access token contains user ID."""
        user_id = "user123"
        token = create_access_token(data={"sub": user_id})
        payload = verify_token(token)
        assert payload["sub"] == user_id
        assert payload["type"] == "access"

    def test_create_access_token_with_email(self) -> None:
        """Test access token creation with email."""
        token = create_access_token(data={"sub": "user123", "email": "test@example.com"})
        payload = verify_token(token)
        assert payload["email"] == "test@example.com"

    def test_create_access_token_with_custom_expiry(self) -> None:
        """Test access token with custom expiration time."""
        custom_delta = timedelta(minutes=5)
        token = create_access_token(data={"sub": "user123"}, expires_delta=custom_delta)
        payload = verify_token(token)
        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
        now = datetime.now(UTC)
        # Should expire in approximately 5 minutes
        assert 4.9 * 60 <= (exp_time - now).total_seconds() <= 5.1 * 60

    def test_create_refresh_token_returns_string(self) -> None:
        """Test that refresh token is returned as string."""
        token = create_refresh_token(data={"sub": "user123"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token_has_refresh_type(self) -> None:
        """Test that refresh token has correct type."""
        token = create_refresh_token(data={"sub": "user123"})
        payload = verify_token(token)
        assert payload["type"] == "refresh"

    def test_create_tokens_include_jti_and_token_version(self) -> None:
        """Test access/refresh tokens include jti and tv claims."""
        jti = "session-jti-123"
        access = create_access_token(data={"sub": "user123", "jti": jti, "tv": 3})
        refresh = create_refresh_token(data={"sub": "user123", "jti": jti, "tv": 3})

        access_payload = verify_token(access)
        refresh_payload = verify_token(refresh)

        assert access_payload.get("jti") == jti
        assert refresh_payload.get("jti") == jti
        assert access_payload.get("tv") == 3
        assert refresh_payload.get("tv") == 3

    def test_create_password_reset_token_returns_string(self) -> None:
        """Test that password reset token is returned as string."""
        token = create_password_reset_token({"sub": "user123", "email": "test@example.com"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_password_reset_token_has_correct_type(self) -> None:
        """Test that password reset token has correct type."""
        token = create_password_reset_token({"sub": "user123", "email": "test@example.com"})
        payload = verify_token(token)
        assert payload["type"] == "password_reset"

    def test_create_email_verification_token_returns_string(self) -> None:
        """Test that email verification token is returned as string."""
        token = create_email_verification_token({"sub": "user123", "email": "test@example.com"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_email_verification_token_has_correct_type(self) -> None:
        """Test that email verification token has correct type."""
        token = create_email_verification_token({"sub": "user123", "email": "test@example.com"})
        payload = verify_token(token)
        assert payload["type"] == "email_verification"


class TestTokenVerification:
    """Tests for JWT token verification."""

    def test_verify_token_valid(self) -> None:
        """Test verification of valid token."""
        user_id = "user123"
        token = create_access_token(data={"sub": user_id})
        payload = verify_token(token)
        assert payload["sub"] == user_id

    def test_verify_token_invalid_signature(self) -> None:
        """Test verification of token with invalid signature."""
        # Create a token with wrong secret
        wrong_secret = "wrong_secret_key"
        payload = {
            "sub": "user123",
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        }
        invalid_token = jwt.encode(payload, wrong_secret, algorithm=settings.security.jwt_algorithm)

        with pytest.raises(InvalidTokenError):
            verify_token(invalid_token)

    def test_verify_token_expired(self) -> None:
        """Test verification of expired token."""
        # Create token with past expiration
        expired_delta = timedelta(minutes=-1)
        token = create_access_token(data={"sub": "user123"}, expires_delta=expired_delta)

        with pytest.raises(ExpiredTokenError):
            verify_token(token)

    def test_verify_token_malformed(self) -> None:
        """Test verification of malformed token."""
        malformed_token = "not.a.valid.token"

        with pytest.raises(InvalidTokenError):
            verify_token(malformed_token)

    def test_verify_token_empty_string(self) -> None:
        """Test verification of empty token."""
        with pytest.raises(InvalidTokenError):
            verify_token("")

    def test_verify_token_contains_iat(self) -> None:
        """Test that verified token contains issued at timestamp."""
        token = create_access_token(data={"sub": "user123"})
        payload = verify_token(token)
        assert "iat" in payload
        assert isinstance(payload["iat"], int)

    def test_verify_token_contains_exp(self) -> None:
        """Test that verified token contains expiration timestamp."""
        token = create_access_token(data={"sub": "user123"})
        payload = verify_token(token)
        assert "exp" in payload
        assert isinstance(payload["exp"], int)
        assert payload["exp"] > payload["iat"]


class TestTokenOptions:
    """Tests for token creation with various options."""

    def test_access_token_with_2fa_verified(self) -> None:
        """Test access token with 2FA verified flag."""
        token = create_access_token(data={"sub": "user123", "tfaVerified": True, "tfaMethod": "totp"})
        payload = verify_token(token)
        assert payload.get("tfaVerified") is True
        assert payload.get("tfaMethod") == "totp"

    def test_access_token_with_tenant_info(self) -> None:
        """Test access token with tenant information."""
        token = create_access_token(data={"sub": "user123", "tid": "tenant1", "trol": "admin"})
        payload = verify_token(token)
        assert payload.get("tid") == "tenant1"
        assert payload.get("trol") == "admin"

    def test_refresh_token_does_not_contain_tenant_info(self) -> None:
        """Test that refresh token does not preserve tenant info (security)."""
        token = create_refresh_token(data={"sub": "user123", "tid": "tenant1", "trol": "admin"})  # type: ignore[typeddict-unknown-key]
        payload = verify_token(token)
        # Tenant info should NOT be in refresh token
        assert "tid" not in payload or payload.get("tid") is None
        assert "trol" not in payload or payload.get("trol") is None
