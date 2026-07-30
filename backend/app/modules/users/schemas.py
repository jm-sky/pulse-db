"""Pydantic schemas for user management endpoints."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.common.pagination import PaginatedResponse

from .validators import validate_avatar_url


class UserUpdate(BaseModel):
    """User update request schema with camelCase."""

    email: EmailStr | None = None
    name: str | None = Field(None, min_length=1, max_length=100)
    role: str | None = Field(None, pattern="^(user|admin|moderator|owner|premium)$")
    isActive: bool | None = None
    isAdmin: bool | None = None
    isOwner: bool | None = None
    isPremium: bool | None = None


class UserProfileUpdate(BaseModel):
    """Current user profile update schema.

    Note: Email cannot be updated through this endpoint for security reasons.
    """

    name: str | None = Field(None, min_length=1, max_length=100)
    avatarUrl: str | None = Field(None, description="Avatar URL (only allowed providers like Gravatar)")

    @field_validator("avatarUrl")
    @classmethod
    def validate_avatar_url(cls, v: str | None) -> str | None:
        """Validate avatar URL against allowed providers."""
        if v is not None and not validate_avatar_url(v):
            raise ValueError("Avatar URL must be from an allowed provider (e.g., Gravatar)")
        return v


class UserResponse(BaseModel):
    """User response schema with camelCase."""

    id: str
    email: EmailStr
    name: str
    role: str
    isActive: bool
    avatarUrl: str | None = None
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class UserListResponse(PaginatedResponse[UserResponse]):
    """User list response with pagination metadata.

    Uses generic PaginatedResponse with consistent pagination fields:
    - data: list of users
    - total: total count
    - page: current page (0-based)
    - limit: items per page
    - hasMore: whether more pages exist
    """

    pass


class PublicUserResponse(BaseModel):
    """Public user profile response schema with camelCase.

    Only includes public information:
    - id, name, avatarUrl, isAdmin, isOwner, isPremium (always public)
    - email (only if user has emailPublic setting enabled)
    """

    id: str
    name: str
    avatarUrl: str | None = None
    isAdmin: bool = False
    isOwner: bool = False
    isPremium: bool = False
    email: EmailStr | None = None  # Only included if emailPublic is True
    emailPublic: bool = False  # Indicates if email is included

    model_config = {"from_attributes": True, "populate_by_name": True}


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
