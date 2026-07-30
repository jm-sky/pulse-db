"""Business logic service for admin operations."""

import logging

from app.modules.auth.models import User
from app.modules.auth.repositories import UserRepository as AuthUserRepository
from app.modules.users.repositories import UserRepository
from app.modules.users.schemas import UserUpdate

from .authorization import enforce_user_mutation_permissions
from .repository import AdminRepository
from .schemas import AdminUserResponse

logger = logging.getLogger(__name__)


class AdminService:
    """Service for admin-level business logic."""

    def __init__(
        self,
        repository: AdminRepository,
        user_repository: UserRepository,
        auth_user_repository: AuthUserRepository,
    ):
        self.repository = repository
        self.user_repository = user_repository
        self.auth_user_repository = auth_user_repository

    def _serialize_datetime(self, dt: object) -> str | None:
        if dt is None:
            return None
        if hasattr(dt, "isoformat"):
            return str(dt.isoformat())
        return str(dt)

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> list[AdminUserResponse]:
        users_with_auth = await self.repository.get_all_users(skip=skip, limit=limit)
        result = []
        for user, _ in users_with_auth:
            result.append(
                AdminUserResponse(
                    id=user.id,
                    name=user.name,
                    email=user.email,
                    avatarUrl=user.avatar_url,
                    isActive=user.is_active,
                    isAdmin=user.is_admin,
                    isOwner=user.is_owner,
                    isPremium=user.is_premium,
                    isEmailVerified=user.is_email_verified,
                    emailVerifiedAt=self._serialize_datetime(user.email_verified_at) or "",
                    createdAt=self._serialize_datetime(user.created_at) or "",
                    updatedAt=self._serialize_datetime(user.created_at) or "",
                )
            )
        return result

    async def get_user_by_id(self, user_id: str) -> AdminUserResponse | None:
        user, _ = await self.repository.get_user_by_id(user_id)
        if not user:
            return None
        return AdminUserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            avatarUrl=user.avatar_url,
            isActive=user.is_active,
            isAdmin=user.is_admin,
            isOwner=user.is_owner,
            isPremium=user.is_premium,
            isEmailVerified=user.is_email_verified,
            emailVerifiedAt=self._serialize_datetime(user.email_verified_at) or "",
            createdAt=self._serialize_datetime(user.created_at) or "",
            updatedAt=self._serialize_datetime(user.created_at) or "",
        )

    async def update_user(self, user_id: str, user_data: UserUpdate, current_user: "User") -> AdminUserResponse | None:
        target_user, _ = await self.repository.get_user_by_id(user_id)
        if not target_user:
            return None

        enforce_user_mutation_permissions(
            actor_is_admin=current_user.isAdmin,
            actor_is_owner=current_user.isOwner,
            target_email=target_user.email,
            target_is_owner=target_user.is_owner,
            target_is_admin=target_user.is_admin,
            new_role=user_data.role,
            new_is_owner=user_data.isOwner,
        )

        is_admin = user_data.isAdmin
        is_owner = user_data.isOwner
        is_premium = user_data.isPremium

        if user_data.role:
            if user_data.role == "admin":
                is_admin = True
                is_owner = False
                is_premium = False
            elif user_data.role == "owner":
                is_owner = True
                is_admin = False
                is_premium = False
            elif user_data.role == "premium":
                is_premium = True
                is_admin = False
                is_owner = False
            elif user_data.role == "user":
                is_admin = False
                is_owner = False
                is_premium = False

        user_model = await self.user_repository.update_user(
            user_id=user_id,
            email=user_data.email,
            name=user_data.name,
            is_active=user_data.isActive,
            role=user_data.role,
            is_admin=is_admin,
            is_owner=is_owner,
            is_premium=is_premium,
        )
        if not user_model:
            return None

        updated_user, _ = await self.repository.get_user_by_id(user_id)
        if not updated_user:
            return None

        return AdminUserResponse(
            id=updated_user.id,
            name=updated_user.name,
            email=updated_user.email,
            avatarUrl=updated_user.avatar_url,
            isActive=updated_user.is_active,
            isAdmin=updated_user.is_admin,
            isEmailVerified=updated_user.is_email_verified,
            emailVerifiedAt=self._serialize_datetime(updated_user.email_verified_at) or "",
            createdAt=self._serialize_datetime(updated_user.created_at) or "",
            updatedAt=self._serialize_datetime(updated_user.created_at) or "",
        )

    async def delete_user(self, user_id: str, current_user: "User") -> bool:
        target_user, _ = await self.repository.get_user_by_id(user_id)
        if not target_user:
            return False

        enforce_user_mutation_permissions(
            actor_is_admin=current_user.isAdmin,
            actor_is_owner=current_user.isOwner,
            target_email=target_user.email,
            target_is_owner=target_user.is_owner,
            target_is_admin=target_user.is_admin,
            is_delete=True,
        )

        return await self.auth_user_repository.delete_user(user_id, soft_delete=True)
