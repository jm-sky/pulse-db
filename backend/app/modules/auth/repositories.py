"""Database repository implementation for user management.

This module provides async PostgreSQL/SQLite repository using
SQLAlchemy 2.0+. For quick development, use SQLite with
DATABASE_URL="sqlite+aiosqlite:///./dev.db" or in-memory with
DATABASE_URL="sqlite+aiosqlite:///:memory:"

Note:
    This is the primary UserRepository used by both auth and users
    modules. Uses composition (helper functions) instead of
    inheritance for better flexibility.
"""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import Depends
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.id_utils import generate_id
from app.common.repository_utils import normalize_email
from app.common.search import SearchMixin
from app.core.database import get_db

from .auth_utils import (
    create_password_reset_token,
    get_password_hash,
    verify_password,
)
from .db_models import OAuthConnectionDB, UserDB
from .exceptions import UserAlreadyExistsError
from .models import User
from .types.repository import UserRepositoryInterface

logger = logging.getLogger(__name__)


class UserRepository(SearchMixin, UserRepositoryInterface):
    """User repository for async database operations.

    This implementation uses SQLAlchemy 2.0+ with async sessions
    for PostgreSQL or SQLite database access.

    Combines auth and admin operations in a single repository.
    Supports search across: name, email
    """

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session.

        Args:
            db: Async SQLAlchemy session
        """
        self.db = db
        # Configure SearchMixin for user search
        self._search_columns = [UserDB.name, UserDB.email]
        self._case_sensitive = False

    def _map_user(self, user_db: UserDB) -> User:
        return User(
            id=user_db.id,
            email=user_db.email,
            name=user_db.name,
            hashedPassword=user_db.hashed_password or "",  # OAuth users may not have password
            isActive=user_db.is_active,
            isAdmin=user_db.is_admin,
            isOwner=user_db.is_owner,
            isPremium=user_db.is_premium,
            isEmailVerified=user_db.is_email_verified,
            createdAt=user_db.created_at,
            resetToken=user_db.reset_token,
            resetTokenExpiry=user_db.reset_token_expiry,
            emailVerificationToken=user_db.email_verification_token,
            emailVerificationSentAt=user_db.email_verification_sent_at,
            emailVerifiedAt=user_db.email_verified_at,
            tokenVersion=user_db.token_version,
            oauthProvider=user_db.oauth_provider,
            oauthProviderId=user_db.oauth_provider_id,
            avatarUrl=user_db.avatar_url,
        )

    async def create_user(
        self,
        email: str,
        password: str,
        full_name: str,
        is_admin: bool = False,
    ) -> User:
        """Create a new user in database."""
        # Normalize email using helper function
        normalized_email = normalize_email(email)

        # Check if user already exists
        stmt = select(UserDB).where(UserDB.email == normalized_email)
        result = await self.db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise UserAlreadyExistsError()

        # Generate new ID using centralized helper
        user_id = generate_id()

        # Create UserDB instance
        user_db = UserDB(
            id=user_id,
            email=normalized_email,
            name=full_name,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_admin=is_admin,
            created_at=datetime.now(UTC),
            is_email_verified=False,
        )

        self.db.add(user_db)
        await self.db.commit()
        await self.db.refresh(user_db)

        # Convert to Pydantic User model for response
        return self._map_user(user_db)

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email from database."""
        normalized_email = normalize_email(email)

        stmt = select(UserDB).where(UserDB.email == normalized_email)
        result = await self.db.execute(stmt)
        user_db = result.scalar_one_or_none()

        if not user_db:
            return None

        # Convert to Pydantic User model
        return self._map_user(user_db)

    async def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID from database."""
        stmt = select(UserDB).where(UserDB.id == user_id)
        result = await self.db.execute(stmt)
        user_db = result.scalar_one_or_none()

        if not user_db:
            return None

        # Convert to Pydantic User model
        return self._map_user(user_db)

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
        stmt = select(UserDB)

        if not include_inactive:
            stmt = stmt.where(UserDB.is_active == True)  # noqa: E712

        # Apply search filter using SearchMixin
        if search:
            stmt = self.apply_search(stmt, search)

        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        users_db = result.scalars().all()

        # Convert to Pydantic User models
        return [self._map_user(user_db) for user_db in users_db]

    async def count_users(self, include_inactive: bool = False, search: str | None = None) -> int:
        """Count total users in database with optional search.

        Args:
            include_inactive: Include inactive users in count
            search: Search term (searches in name, email)

        Returns:
            Total count of users matching criteria
        """
        stmt = select(func.count(UserDB.id))

        if not include_inactive:
            stmt = stmt.where(UserDB.is_active == True)  # noqa: E712

        # Apply search filter using SearchMixin
        if search:
            stmt = self.apply_search(stmt, search)

        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def update_user(self, user: User) -> User:
        """Update user in database."""
        # Get existing user from database
        stmt = select(UserDB).where(UserDB.id == user.id)
        result = await self.db.execute(stmt)
        user_db = result.scalar_one_or_none()

        if not user_db:
            raise ValueError(f"User with id {user.id} not found")

        # Update fields
        user_db.email = user.email
        user_db.name = user.name
        user_db.hashed_password = user.hashedPassword  # type: ignore[assignment]
        user_db.is_active = user.isActive
        user_db.is_admin = user.isAdmin
        user_db.is_owner = user.isOwner
        user_db.is_premium = user.isPremium
        user_db.reset_token = user.resetToken
        user_db.reset_token_expiry = user.resetTokenExpiry
        user_db.is_email_verified = user.isEmailVerified
        user_db.email_verification_token = user.emailVerificationToken
        user_db.email_verification_sent_at = user.emailVerificationSentAt
        user_db.email_verified_at = user.emailVerifiedAt
        user_db.token_version = user.tokenVersion
        user_db.avatar_url = user.avatarUrl

        await self.db.commit()
        await self.db.refresh(user_db)

        # Return updated user as Pydantic model
        return self._map_user(user_db)

    async def generate_reset_token(self, email: str) -> str | None:
        """Generate and store JWT password reset token for user."""
        user = await self.get_user_by_email(email)
        if not user or not user.isActive:
            return None

        # Generate JWT reset token
        token = create_password_reset_token(data={"sub": user.id})

        # Store token
        user.set_reset_token(token, datetime.now(UTC) + timedelta(hours=1))
        await self.update_user(user)

        return token

    async def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """Reset password using token."""
        # Find user with this token
        stmt = select(UserDB).where(UserDB.reset_token == token)
        result = await self.db.execute(stmt)
        user_db = result.scalar_one_or_none()

        if not user_db:
            return False

        # Convert to Pydantic model to use validation methods
        user = self._map_user(user_db)

        if user.is_reset_token_valid(token):
            user.set_password(new_password)
            user.clear_reset_token()
            await self.update_user(user)
            return True

        return False

    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change user password after verifying current password."""
        user = await self.get_user_by_id(user_id)
        if not user or not user.isActive:
            return False

        # Verify current password (hashedPassword is guaranteed non-empty for active users)
        if not user.hashedPassword or not verify_password(current_password, user.hashedPassword):
            return False

        # Update password
        user.hashedPassword = get_password_hash(new_password)
        await self.update_user(user)
        return True

    async def store_email_verification_token(self, user_id: str, token: str, sent_at: datetime) -> User | None:
        """Persist email verification token for a user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        user.set_email_verification_token(token, sent_at)
        return await self.update_user(user)

    async def verify_email_by_token(self, token: str) -> User | None:
        """Verify user email using token."""
        stmt = select(UserDB).where(UserDB.email_verification_token == token)
        result = await self.db.execute(stmt)
        user_db = result.scalar_one_or_none()

        if not user_db:
            return None

        user = self._map_user(user_db)
        if not user.is_email_verification_token_valid(token):
            return None

        user.mark_email_verified(datetime.now(UTC))
        return await self.update_user(user)

    async def delete_user(self, user_id: str, soft_delete: bool = True) -> bool:
        """Delete user account (soft delete by default)."""
        stmt = select(UserDB).where(UserDB.id == user_id)
        result = await self.db.execute(stmt)
        user_db = result.scalar_one_or_none()

        if not user_db:
            return False

        # Always remove OAuth connections tied to this user.
        await self.db.execute(delete(OAuthConnectionDB).where(OAuthConnectionDB.user_id == user_id))
        # Best-effort cleanup for 2FA artifacts (module may be disabled in some deployments).
        try:
            from app.modules.two_factor.db_models import PasskeyDB, TotpConfigDB

            await self.db.execute(delete(TotpConfigDB).where(TotpConfigDB.user_id == user_id))
            await self.db.execute(delete(PasskeyDB).where(PasskeyDB.user_id == user_id))
        except ImportError:
            pass

        if soft_delete:
            # Soft delete: mark as deleted and anonymize data
            user_db.deleted_at = datetime.now(UTC)
            user_db.is_active = False
            user_db.token_version += 1
            # Anonymize email and name for GDPR compliance
            user_db.email = f"deleted_{user_db.id}@deleted.local"
            user_db.name = "Deleted User"
            # Clear sensitive data
            user_db.hashed_password = None  # type: ignore[assignment]
            user_db.reset_token = None
            user_db.reset_token_expiry = None
            user_db.email_verification_token = None
            user_db.email_verification_sent_at = None
            user_db.email_verified_at = None
            user_db.oauth_provider = None
            user_db.oauth_provider_id = None
            user_db.avatar_url = None
            user_db.openrouter_api_token = None
        else:
            # Hard delete: physically remove from database
            await self.db.delete(user_db)

        await self.db.commit()
        return True

    async def create_oauth_user(
        self,
        email: str,
        name: str,
        provider: str,
        provider_id: str,
        avatar_url: str | None = None,
    ) -> User:
        """Create a new user via OAuth (no password)."""
        # Normalize email using helper function
        normalized_email = normalize_email(email)

        # Check if user already exists
        stmt = select(UserDB).where(UserDB.email == normalized_email)
        result = await self.db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise UserAlreadyExistsError()

        # Generate new ID
        user_id = generate_id()

        # Create UserDB instance (no password for OAuth users)
        user_db = UserDB(
            id=user_id,
            email=normalized_email,
            name=name,
            hashed_password=None,  # OAuth users don't have passwords
            is_active=True,
            is_admin=False,
            created_at=datetime.now(UTC),
            is_email_verified=True,  # OAuth emails are pre-verified
            email_verified_at=datetime.now(UTC),
            oauth_provider=provider,
            oauth_provider_id=provider_id,
            avatar_url=avatar_url,
        )

        self.db.add(user_db)
        await self.db.commit()
        await self.db.refresh(user_db)

        return self._map_user(user_db)

    async def get_user_by_oauth_provider(self, provider: str, provider_id: str) -> User | None:
        """Get user by OAuth provider and provider ID."""
        stmt = select(UserDB).where(
            UserDB.oauth_provider == provider,
            UserDB.oauth_provider_id == provider_id,
        )
        result = await self.db.execute(stmt)
        user_db = result.scalar_one_or_none()

        if not user_db:
            return None

        return self._map_user(user_db)

    async def get_oauth_connections(self, user_id: str) -> list[dict]:
        """Get all OAuth connections for a user."""
        stmt = select(OAuthConnectionDB).where(OAuthConnectionDB.user_id == user_id)
        result = await self.db.execute(stmt)
        connections = result.scalars().all()

        return [
            {
                "id": conn.id,
                "provider": conn.provider,
                "providerId": conn.provider_id,
                "email": conn.email,
                "name": conn.name,
                "avatarUrl": conn.avatar_url,
                "createdAt": conn.created_at,
            }
            for conn in connections
        ]

    async def create_oauth_connection(
        self,
        user_id: str,
        provider: str,
        provider_id: str,
        email: str | None = None,
        name: str | None = None,
        avatar_url: str | None = None,
    ) -> dict:
        """Create or update OAuth connection for a user."""
        # Check if connection already exists for this user and provider
        stmt = select(OAuthConnectionDB).where(
            OAuthConnectionDB.user_id == user_id,
            OAuthConnectionDB.provider == provider,
            OAuthConnectionDB.provider_id == provider_id,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Connection already exists for this user - update it with latest data
            existing.email = email
            existing.name = name
            existing.avatar_url = avatar_url
            await self.db.commit()
            await self.db.refresh(existing)

            return {
                "id": existing.id,
                "provider": existing.provider,
                "providerId": existing.provider_id,
                "email": existing.email,
                "name": existing.name,
                "avatarUrl": existing.avatar_url,
                "createdAt": existing.created_at,
            }

        # Check if connection exists for this provider+provider_id but different user
        # (shouldn't happen due to unique constraint, but check for safety)
        stmt_check = select(OAuthConnectionDB).where(
            OAuthConnectionDB.provider == provider,
            OAuthConnectionDB.provider_id == provider_id,
        )
        result_check = await self.db.execute(stmt_check)
        existing_check = result_check.scalar_one_or_none()

        if existing_check:
            # Connection exists but for different user - this shouldn't happen
            # but if it does, update it to point to current user
            existing_check.user_id = user_id
            existing_check.email = email
            existing_check.name = name
            existing_check.avatar_url = avatar_url
            await self.db.commit()
            await self.db.refresh(existing_check)

            return {
                "id": existing_check.id,
                "provider": existing_check.provider,
                "providerId": existing_check.provider_id,
                "email": existing_check.email,
                "name": existing_check.name,
                "avatarUrl": existing_check.avatar_url,
                "createdAt": existing_check.created_at,
            }

        # Create new connection
        connection_id = generate_id()
        connection_db = OAuthConnectionDB(
            id=connection_id,
            user_id=user_id,
            provider=provider,
            provider_id=provider_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
            created_at=datetime.now(UTC),
        )

        self.db.add(connection_db)
        await self.db.commit()
        await self.db.refresh(connection_db)

        return {
            "id": connection_db.id,
            "provider": connection_db.provider,
            "providerId": connection_db.provider_id,
            "email": connection_db.email,
            "name": connection_db.name,
            "avatarUrl": connection_db.avatar_url,
            "createdAt": connection_db.created_at,
        }

    async def delete_oauth_connection(self, user_id: str, provider: str) -> bool:
        """Delete an OAuth connection for a user."""
        stmt = select(OAuthConnectionDB).where(
            OAuthConnectionDB.user_id == user_id,
            OAuthConnectionDB.provider == provider,
        )
        result = await self.db.execute(stmt)
        connection = result.scalar_one_or_none()

        if not connection:
            return False

        await self.db.delete(connection)
        await self.db.commit()
        return True

    async def delete_all_oauth_connections(self, user_id: str) -> int:
        """Delete all OAuth connections for a user."""
        count_stmt = select(func.count(OAuthConnectionDB.id)).where(OAuthConnectionDB.user_id == user_id)
        count_result = await self.db.execute(count_stmt)
        deleted_count = int(count_result.scalar_one() or 0)
        await self.db.execute(delete(OAuthConnectionDB).where(OAuthConnectionDB.user_id == user_id))
        await self.db.commit()
        return deleted_count

    async def increment_token_version(self, user_id: str) -> int | None:
        """Increment token version and return the new value."""
        stmt = select(UserDB).where(UserDB.id == user_id)
        result = await self.db.execute(stmt)
        user_db = result.scalar_one_or_none()
        if not user_db:
            return None
        user_db.token_version += 1
        await self.db.commit()
        return user_db.token_version


def get_user_repository(
    db: AsyncSession = Depends(get_db),
) -> UserRepositoryInterface:
    """FastAPI dependency to get user repository instance.

    Args:
        db: Async database session from dependency

    Returns:
        UserRepository instance configured with the session

    Example:
        @router.get("/users")
        async def list_users(
            repo: UserRepository = Depends(get_user_repository)
        ):
            return await repo.get_all_users()

    Configuration:
        For development, use SQLite in your .env:
            DATABASE_URL=sqlite+aiosqlite:///./dev.db

        For in-memory database (data lost on restart):
            DATABASE_URL=sqlite+aiosqlite:///:memory:

        For production, use PostgreSQL:
            DATABASE_URL=postgresql+asyncpg://user:pass@host/db
    """
    return UserRepository(db)
