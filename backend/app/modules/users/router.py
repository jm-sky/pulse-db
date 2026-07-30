"""FastAPI router for user management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.admin.authorization import enforce_user_mutation_permissions
from app.modules.auth.repositories import UserRepository as AuthUserRepository
from app.modules.auth.repositories import (
    get_user_repository as get_auth_user_repository,
)
from app.modules.settings.db_models import UserSettingsDB

from .dependencies import AdminUser, CurrentUser
from .exceptions import UserAlreadyExistsError
from .repositories import UserRepository, get_user_repository
from .schemas import (
    MessageResponse,
    PublicUserResponse,
    UserListResponse,
    UserProfileUpdate,
    UserResponse,
    UserUpdate,
)

router = APIRouter()

# Note: there is intentionally no POST "/" (create user) endpoint here.
# User creation requires password handling and is only done through the
# auth module's registration endpoint (POST /auth/register). A previous
# version of this endpoint called UserRepository.create_user(), which
# unconditionally raised NotImplementedError — it was dead, untested code
# that always 500'd. See docs/reviews/2026-07-20-code-quality.md.


@router.get(
    "/",
    response_model=UserListResponse,
    summary="List users",
    description="Get list of all users with pagination and search",
)
async def list_users(
    _: AdminUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max records to return"),
    include_inactive: bool = Query(default=False, description="Include inactive users"),
    search: str | None = Query(default=None, description="Search in name, email, and role"),
) -> UserListResponse:
    """Get list of users with optional search."""
    users = await repo.get_all_users(skip=skip, limit=limit, include_inactive=include_inactive, search=search)
    total = await repo.count_users(include_inactive=include_inactive, search=search)
    user_responses = [UserResponse(**u.to_response()) for u in users]
    return UserListResponse.create(items=user_responses, total=total, skip=skip, limit=limit)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get currently authenticated user information",
)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """Get current user information."""
    return UserResponse(**current_user.to_response())


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user",
    description="Update profile information for the authenticated user",
)
async def update_current_user_profile(
    user_data: UserProfileUpdate,
    current_user: CurrentUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserResponse:
    """Update current user's profile details."""
    updated_user = await repo.update_user(
        user_id=current_user.id,
        name=user_data.name,
        avatar_url=user_data.avatarUrl,
    )
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(**updated_user.to_response())


@router.get(
    "/{user_id}/public",
    response_model=PublicUserResponse,
    summary="Get public user profile",
    description="Get public profile information for a user (only if profile is public)",
)
async def get_public_user_profile(
    user_id: str,
    auth_repo: Annotated[AuthUserRepository, Depends(get_auth_user_repository)],
    db: AsyncSession = Depends(get_db),
) -> PublicUserResponse:
    """Get public user profile."""
    auth_user = await auth_repo.get_user_by_id(user_id)
    if not auth_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")

    result = await db.execute(select(UserSettingsDB).where(UserSettingsDB.user_id == user_id))
    user_settings = result.scalars().first()

    if not user_settings or not user_settings.is_public_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user profile is not public",
        )

    return PublicUserResponse(
        id=auth_user.id,
        name=auth_user.name,
        avatarUrl=auth_user.avatarUrl,
        isAdmin=auth_user.isAdmin,
        isOwner=auth_user.isOwner,
        isPremium=auth_user.isPremium,
        email=auth_user.email if user_settings.is_public_email else None,
        emailPublic=user_settings.is_public_email,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Get a specific user by their ID",
)
async def get_user(
    user_id: str,
    _: AdminUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserResponse:
    """Get user by ID."""
    user = await repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")
    return UserResponse(**user.to_response())


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Update user information (admin only)",
)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: AdminUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
    auth_repo: Annotated[AuthUserRepository, Depends(get_auth_user_repository)],
) -> UserResponse:
    """Update user information."""
    target_user = await auth_repo.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    enforce_user_mutation_permissions(
        # This module's own User model uses a single `role` string (not the
        # auth module's independent isAdmin/isOwner booleans) — "owner" is
        # treated as admin-plus, matching how AdminService's role mapping
        # already collapses isOwner=True to role="owner" regardless of isAdmin.
        actor_is_admin=current_user.role in ("admin", "owner"),
        actor_is_owner=current_user.role == "owner",
        target_email=target_user.email,
        target_is_owner=target_user.isOwner,
        target_is_admin=target_user.isAdmin,
        new_role=user_data.role,
        new_is_owner=user_data.isOwner,
    )
    try:
        user = await repo.update_user(
            user_id=user_id,
            email=user_data.email,
            name=user_data.name,
            role=user_data.role,
            is_active=user_data.isActive,
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )
        return UserResponse(**user.to_response())
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Delete user",
    description="Soft delete user (set isActive to false)",
)
async def delete_user(
    user_id: str,
    current_user: AdminUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
    auth_repo: Annotated[AuthUserRepository, Depends(get_auth_user_repository)],
) -> MessageResponse:
    """Soft delete user."""
    target_user = await auth_repo.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")
    enforce_user_mutation_permissions(
        actor_is_admin=current_user.role in ("admin", "owner"),
        actor_is_owner=current_user.role == "owner",
        target_email=target_user.email,
        target_is_owner=target_user.isOwner,
        target_is_admin=target_user.isAdmin,
        is_delete=True,
    )
    success = await repo.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")
    return MessageResponse(message=f"User {user_id} deactivated successfully")


@router.delete(
    "/{user_id}/hard",
    response_model=MessageResponse,
    summary="Permanently delete user",
    description="Permanently delete user from the system (admin only)",
)
async def hard_delete_user(
    user_id: str,
    current_user: AdminUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
    auth_repo: Annotated[AuthUserRepository, Depends(get_auth_user_repository)],
) -> MessageResponse:
    """Permanently delete user."""
    target_user = await auth_repo.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")
    enforce_user_mutation_permissions(
        actor_is_admin=current_user.role in ("admin", "owner"),
        actor_is_owner=current_user.role == "owner",
        target_email=target_user.email,
        target_is_owner=target_user.isOwner,
        target_is_admin=target_user.isAdmin,
        is_delete=True,
        is_hard_delete=True,
    )
    success = await repo.hard_delete_user(user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")
    return MessageResponse(message=f"User {user_id} permanently deleted")
