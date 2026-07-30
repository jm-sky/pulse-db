"""Adapter repository for user management module.

This repository wraps the auth module's UserRepository using composition.
It provides the specific method signatures needed by the users module endpoints
while delegating actual database operations to the auth repository.

This follows the composition over inheritance principle - instead of creating
a base class, we wrap and adapt the auth repository to our needs.
"""

import logging
from typing import TYPE_CHECKING

from fastapi import Depends

from app.common.repository_utils import normalize_email
from app.modules.auth.repositories import UserRepository as AuthUserRepository
from app.modules.auth.repositories import get_user_repository as get_auth_repository

from .exceptions import UserAlreadyExistsError
from .models import User

if TYPE_CHECKING:
    from app.modules.auth.models import User as AuthUser


logger = logging.getLogger(__name__)


class UserRepository:
    """Adapter repository that wraps auth module's UserRepository.

    This uses composition to delegate to the auth repository while providing
    the specific method signatures and User model needed by users module endpoints.

    The auth repository handles all actual database operations.
    """

    def __init__(self, auth_repo: AuthUserRepository):
        """Initialize with auth repository (composition).

        Args:
            auth_repo: Auth module's UserRepository instance
        """
        self._auth_repo = auth_repo

    def _auth_user_to_users_user(self, auth_user: "AuthUser") -> User:
        """Convert auth module's User to users module's User.

        Args:
            auth_user: User from auth module

        Returns:
            User model for users module
        """
        role = "admin" if auth_user.isAdmin else "user"
        # Use createdAt for both timestamps if updatedAt not available
        return User(
            id=auth_user.id,
            email=auth_user.email,
            name=auth_user.name,
            role=role,
            isActive=auth_user.isActive,
            isEmailVerified=auth_user.isEmailVerified,
            avatarUrl=auth_user.avatarUrl,
            createdAt=auth_user.createdAt,
            updatedAt=auth_user.createdAt,  # users model requires this
        )

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email from database."""
        auth_user = await self._auth_repo.get_user_by_email(email)
        if not auth_user:
            return None
        return self._auth_user_to_users_user(auth_user)

    async def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID from database."""
        auth_user = await self._auth_repo.get_user_by_id(user_id)
        if not auth_user:
            return None
        return self._auth_user_to_users_user(auth_user)

    async def get_all_users(
        self,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
        search: str | None = None,
    ) -> list[User]:
        """Get all users from database with pagination and search.

        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            include_inactive: Include inactive users
            search: Search term (searches in name, email)

        Returns:
            List of users matching criteria
        """
        auth_users = await self._auth_repo.get_all_users(
            skip=skip,
            limit=limit,
            include_inactive=include_inactive,
            search=search,
        )
        return [self._auth_user_to_users_user(u) for u in auth_users]

    async def update_user(
        self,
        user_id: str,
        email: str | None = None,
        name: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
        avatar_url: str | None = None,
        is_admin: bool | None = None,
        is_owner: bool | None = None,
        is_premium: bool | None = None,
    ) -> User | None:
        """Update user fields in database.

        Args:
            user_id: User ID to update
            email: New email (optional)
            name: New name (optional)
            role: New role - 'admin', 'user', 'owner', 'premium' (optional, deprecated - use flags instead)
            is_active: Active status (optional)
            avatar_url: Avatar URL (optional)
            is_admin: Admin flag (optional)
            is_owner: Owner flag (optional)
            is_premium: Premium flag (optional)

        Returns:
            Updated User or None if not found

        Raises:
            UserAlreadyExistsError: If email is already in use
        """
        # Get existing user from auth repository
        auth_user = await self._auth_repo.get_user_by_id(user_id)
        if not auth_user:
            return None

        # Update fields that were provided
        if email is not None:
            # Check if email is changing and already exists
            normalized_email = normalize_email(email)
            if normalized_email != auth_user.email:
                existing = await self._auth_repo.get_user_by_email(email)
                if existing:
                    raise UserAlreadyExistsError(f"Email {email} is already in use")
            auth_user.email = normalized_email

        if name is not None:
            auth_user.name = name

        # Handle role updates - support both old 'role' field and new flags
        if role is not None:
            # Legacy support: map role string to flags
            auth_user.isAdmin = role == "admin"
            auth_user.isOwner = role == "owner"
            auth_user.isPremium = role == "premium" or role == "admin" or role == "owner"
        else:
            # Use explicit flags if provided
            if is_admin is not None:
                auth_user.isAdmin = is_admin
            if is_owner is not None:
                auth_user.isOwner = is_owner
            if is_premium is not None:
                auth_user.isPremium = is_premium

        if is_active is not None:
            auth_user.isActive = is_active

        if avatar_url is not None:
            auth_user.avatarUrl = avatar_url

        # Save via auth repository
        updated_auth_user = await self._auth_repo.update_user(auth_user)
        return self._auth_user_to_users_user(updated_auth_user)

    async def delete_user(self, user_id: str) -> bool:
        """Delete user (soft delete - set is_active to False)."""
        return await self._auth_repo.delete_user(user_id, soft_delete=True)

    async def hard_delete_user(self, user_id: str) -> bool:
        """Permanently delete user from database."""
        return await self._auth_repo.delete_user(user_id, soft_delete=False)

    async def count_users(self, include_inactive: bool = False, search: str | None = None) -> int:
        """Count total users in database with optional search.

        Args:
            include_inactive: Include inactive users in count
            search: Search term (searches in name, email)

        Returns:
            Total count of users matching criteria
        """
        return await self._auth_repo.count_users(include_inactive=include_inactive, search=search)


def get_user_repository(
    auth_repo: AuthUserRepository = Depends(get_auth_repository),
) -> UserRepository:
    """FastAPI dependency to get user repository instance.

    This creates an adapter that wraps the auth repository using composition.
    All database operations are delegated to the auth module's repository.

    Args:
        auth_repo: Auth module's repository (injected by dependency)

    Returns:
        UserRepository adapter instance

    Example:
        @router.get("/users")
        async def list_users(
            repo: UserRepository = Depends(get_user_repository)
        ):
            return await repo.get_all_users()
    """
    return UserRepository(auth_repo)
