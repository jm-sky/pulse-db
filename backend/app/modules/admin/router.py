"""FastAPI router for admin endpoints.

This module provides admin-only endpoints for managing users.
All endpoints require admin authentication.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import AdminOrOwnerUser
from app.modules.auth.repositories import (
    UserRepository as AuthUserRepository,
)
from app.modules.auth.repositories import (
    get_user_repository as get_auth_user_repository,
)
from app.modules.users.repositories import UserRepository, get_user_repository
from app.modules.users.schemas import UserUpdate

from .repository import AdminRepository
from .schemas import AdminUserResponse
from .service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


def get_admin_repository(db: AsyncSession = Depends(get_db)) -> AdminRepository:
    """Dependency to get admin repository instance."""
    return AdminRepository(db)


def get_admin_service(
    repository: AdminRepository = Depends(get_admin_repository),
    user_repository: UserRepository = Depends(get_user_repository),
    auth_user_repository: AuthUserRepository = Depends(get_auth_user_repository),
) -> AdminService:
    """Dependency to get admin service instance."""
    return AdminService(repository, user_repository, auth_user_repository)


# Users endpoints
@router.get(
    "/users",
    response_model=list[AdminUserResponse],
    summary="Get all users (admin only)",
    description="Get list of all users with pagination",
)
async def get_all_users(
    _: AdminOrOwnerUser,
    service: Annotated[AdminService, Depends(get_admin_service)],
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max records to return"),
) -> list[AdminUserResponse]:
    """Get all users (admin only)."""
    return await service.get_all_users(skip=skip, limit=limit)


@router.get(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Get user by ID (admin only)",
    description="Get a specific user by their ID",
)
async def get_user_by_id(
    user_id: str,
    _: AdminOrOwnerUser,
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> AdminUserResponse:
    """Get user by ID (admin only)."""
    user = await service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")
    return user


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Update user (admin only)",
    description="Update user information",
)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: AdminOrOwnerUser,
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> AdminUserResponse:
    """Update user (admin or owner only)."""
    user = await service.update_user(user_id, user_data, current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")
    return user


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user (admin only)",
    description="Delete a user (soft delete - sets isActive to false)",
)
async def delete_user(
    user_id: str,
    current_user: AdminOrOwnerUser,
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> None:
    """Delete user (admin or owner only)."""
    success = await service.delete_user(user_id, current_user)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")
