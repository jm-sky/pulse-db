"""Pydantic schemas for admin endpoints."""

from pydantic import BaseModel


class AdminUserResponse(BaseModel):
    """Response schema for admin user data."""

    id: str
    name: str
    email: str
    avatarUrl: str | None = None
    isActive: bool
    isAdmin: bool
    isOwner: bool = False
    isPremium: bool = False
    isEmailVerified: bool
    emailVerifiedAt: str | None = None
    createdAt: str
    updatedAt: str
