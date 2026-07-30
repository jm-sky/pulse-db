"""Pydantic schemas for authentication endpoints."""

import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


def validate_password_strength(password: str) -> str:
    """
    Validate password meets strength requirements.

    Requirements:
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Args:
        password: The password to validate

    Returns:
        The validated password

    Raises:
        ValueError: If password doesn't meet requirements
    """
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError('Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)')
    return password


class UserLogin(BaseModel):
    """User login request schema with camelCase."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    recaptchaToken: str | None = Field(
        default=None,
        description="reCAPTCHA token (optional, only checked if RECAPTCHA_ENABLED=true)",
    )


class UserRegister(BaseModel):
    """User registration request schema with camelCase."""

    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password must contain uppercase, lowercase, digit, and special character",
    )
    name: str = Field(..., min_length=1, max_length=100)
    recaptchaToken: str | None = Field(
        default=None,
        description="reCAPTCHA token (optional, only checked if RECAPTCHA_ENABLED=true)",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets strength requirements."""
        return validate_password_strength(v)


class TokenResponse(BaseModel):
    """Token response schema with camelCase."""

    accessToken: str
    refreshToken: str
    tokenType: str = "bearer"
    expiresIn: int  # seconds


class UserResponse(BaseModel):
    """User response schema with camelCase."""

    id: str
    email: EmailStr
    name: str
    isActive: bool
    isAdmin: bool
    isOwner: bool = False
    isPremium: bool = False
    isEmailVerified: bool
    emailVerifiedAt: datetime | None = None
    avatarUrl: str | None = None
    createdAt: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class LoginResponse(BaseModel):
    """Login response schema combining token and user info."""

    user: UserResponse
    accessToken: str
    refreshToken: str
    tokenType: str = "bearer"
    expiresIn: int
    requiresEmailVerification: bool


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request schema."""

    email: EmailStr
    recaptchaToken: str | None = Field(
        default=None,
        description="reCAPTCHA token (optional, only checked if RECAPTCHA_ENABLED=true)",
    )


class ResetPasswordRequest(BaseModel):
    """Reset password request schema."""

    token: str = Field(..., min_length=1)
    newPassword: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password must contain uppercase, lowercase, digit, and special character",
    )

    @field_validator("newPassword")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets strength requirements."""
        return validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    """Change password request schema for authenticated users."""

    currentPassword: str = Field(..., min_length=1, max_length=100)
    newPassword: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password must contain uppercase, lowercase, digit, and special character",
    )

    @field_validator("newPassword")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets strength requirements."""
        return validate_password_strength(v)


class DeleteAccountRequest(BaseModel):
    """Delete account request schema."""

    password: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Current password for confirmation (optional but recommended)",
    )
    confirmation: str = Field(..., min_length=1, description="Confirmation phrase like 'DELETE' or user email")


class EmailVerificationRequest(BaseModel):
    """Email verification token payload."""

    token: str = Field(..., min_length=1)


class ResendEmailVerificationRequest(BaseModel):
    """Resend email verification request."""

    email: EmailStr


# OAuth Schemas


class OAuthAuthUrlRequest(BaseModel):
    """Request schema for OAuth authorization URL."""

    provider: str = Field(..., description="OAuth provider name (google, github, etc.)")


class OAuthAuthUrlResponse(BaseModel):
    """Response schema for OAuth authorization URL."""

    authUrl: str = Field(..., description="Authorization URL to redirect user to")
    state: str = Field(..., description="CSRF protection state parameter")


class OAuthCallbackRequest(BaseModel):
    """Request schema for OAuth callback."""

    code: str = Field(..., description="Authorization code from provider")
    state: str = Field(..., description="CSRF protection state parameter")
    recaptchaToken: str | None = Field(default=None, description="reCAPTCHA token (optional)")


class OAuthCallbackResponse(BaseModel):
    """Response schema for OAuth callback (same as LoginResponse)."""

    user: UserResponse
    accessToken: str
    refreshToken: str
    tokenType: str = "bearer"
    expiresIn: int
    requiresEmailVerification: bool = False  # OAuth emails are pre-verified


class OAuthConnectionResponse(BaseModel):
    """Response schema for OAuth connection."""

    id: str
    provider: str
    providerId: str
    email: str | None = None
    name: str | None = None
    avatarUrl: str | None = None
    createdAt: datetime


class OAuthConnectionsListResponse(BaseModel):
    """Response schema for list of OAuth connections."""

    connections: list[OAuthConnectionResponse]
