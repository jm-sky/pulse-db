"""Repository interface for user storage implementations.

This module defines the abstract interface that both in-memory and database
repositories must implement. This allows easy switching between implementations.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from ..models import User


class UserRepositoryInterface(ABC):
    """Abstract interface for user repository implementations.

    Implementations:
    - UserStore (memory_stores.py): In-memory storage for dev/testing
    - UserRepository (repositories.py): Database storage for production
    """

    @abstractmethod
    async def create_user(self, email: str, password: str, full_name: str) -> User:
        """Create a new user.

        Args:
            email: User email address
            password: Plain text password (will be hashed)
            full_name: User's full name

        Returns:
            Created user object

        Raises:
            UserAlreadyExistsError: If user with email already exists
        """
        ...

    @abstractmethod
    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email address.

        Args:
            email: User email to search for

        Returns:
            User object if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by unique ID.

        Args:
            user_id: User ID (ULID format)

        Returns:
            User object if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_all_users(self) -> list[User]:
        """Get all users.

        Returns:
            List of all user objects
        """
        ...

    @abstractmethod
    async def update_user(self, user: User) -> User:
        """Update user in storage.

        Args:
            user: User object with updated fields

        Returns:
            Updated user object
        """
        ...

    @abstractmethod
    async def generate_reset_token(self, email: str) -> str | None:
        """Generate and store JWT password reset token for user.

        Args:
            email: User email address

        Returns:
            Reset token (JWT) if user found and active, None otherwise
        """
        ...

    @abstractmethod
    async def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """Reset password using token.

        Args:
            token: Password reset token (JWT)
            new_password: New plain text password

        Returns:
            True if password reset successful, False otherwise
        """
        ...

    @abstractmethod
    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change user password after verifying current password.

        Args:
            user_id: User ID
            current_password: Current plain text password
            new_password: New plain text password

        Returns:
            True if password changed successfully, False otherwise
        """
        ...

    @abstractmethod
    async def delete_user(self, user_id: str, soft_delete: bool = True) -> bool:
        """Delete user account (soft delete by default).

        Args:
            user_id: User ID to delete
            soft_delete: If True, marks user as deleted (soft delete). If False, physically removes user.

        Returns:
            True if user deleted successfully, False otherwise
        """
        ...

    @abstractmethod
    async def store_email_verification_token(self, user_id: str, token: str, sent_at: datetime) -> User | None:
        """Persist email verification token for a user.

        Args:
            user_id: User ID
            token: Email verification token
            sent_at: Timestamp when token was sent

        Returns:
            Updated user object if successful, None otherwise
        """
        ...

    @abstractmethod
    async def verify_email_by_token(self, token: str) -> User | None:
        """Verify user email using token.

        Args:
            token: Email verification token

        Returns:
            Verified user object if token is valid, None otherwise
        """
        ...

    @abstractmethod
    async def create_oauth_user(
        self,
        email: str,
        name: str,
        provider: str,
        provider_id: str,
        avatar_url: str | None = None,
    ) -> User:
        """Create a new user via OAuth (no password).

        Args:
            email: User email address
            name: User's full name
            provider: OAuth provider name (google, github, etc.)
            provider_id: Provider's unique user ID
            avatar_url: User's profile picture URL (optional)

        Returns:
            Created user object

        Raises:
            UserAlreadyExistsError: If user with email already exists
        """
        ...

    @abstractmethod
    async def get_user_by_oauth_provider(self, provider: str, provider_id: str) -> User | None:
        """Get user by OAuth provider and provider ID.

        Args:
            provider: OAuth provider name (google, github, etc.)
            provider_id: Provider's unique user ID

        Returns:
            User object if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_oauth_connections(self, user_id: str) -> list[dict]:
        """Get all OAuth connections for a user.

        Args:
            user_id: User ID

        Returns:
            List of OAuth connection dictionaries
        """
        ...

    @abstractmethod
    async def create_oauth_connection(
        self,
        user_id: str,
        provider: str,
        provider_id: str,
        email: str | None = None,
        name: str | None = None,
        avatar_url: str | None = None,
    ) -> dict:
        """Create a new OAuth connection for a user.

        Args:
            user_id: User ID
            provider: OAuth provider name (google, github, etc.)
            provider_id: Provider's unique user ID
            email: Email from OAuth provider (optional)
            name: Name from OAuth provider (optional)
            avatar_url: Profile picture URL from OAuth provider (optional)

        Returns:
            Created or existing OAuth connection dictionary
        """
        ...

    @abstractmethod
    async def delete_oauth_connection(self, user_id: str, provider: str) -> bool:
        """Delete an OAuth connection for a user.

        Args:
            user_id: User ID
            provider: OAuth provider name (google, github, etc.)

        Returns:
            True if connection deleted, False if not found
        """
        ...

    @abstractmethod
    async def delete_all_oauth_connections(self, user_id: str) -> int:
        """Delete all OAuth connections for a user."""
        ...

    @abstractmethod
    async def increment_token_version(self, user_id: str) -> int | None:
        """Increment token version and return the new value."""
        ...
