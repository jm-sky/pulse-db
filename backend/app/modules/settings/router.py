"""API router for user settings."""

from datetime import UTC, datetime
from typing import Literal, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import CurrentUser

from .db_models import UserSettingsDB
from .schemas import SettingsResponse, UpdateSettingsRequest

router = APIRouter(prefix="", tags=["Settings"])


async def _get_or_create_settings(
    db: AsyncSession,
    user_id: str,
) -> UserSettingsDB:
    result = await db.execute(select(UserSettingsDB).where(UserSettingsDB.user_id == user_id))
    settings = result.scalars().first()
    if settings is None:
        settings = UserSettingsDB(user_id=user_id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


@router.get("", response_model=SettingsResponse)
async def get_my_settings(
    *,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Return preferences for the authenticated user."""
    settings = await _get_or_create_settings(db, current_user.id)
    locale = cast(Literal["en", "pl"], settings.locale)
    return SettingsResponse(
        darkMode=settings.dark_mode,
        locale=locale,
        profilePublic=settings.is_public_profile,
        emailPublic=settings.is_public_email,
        imageProcessingMode=settings.image_processing_mode,
    )


@router.patch("", response_model=SettingsResponse)
async def update_my_settings(
    *,
    payload: UpdateSettingsRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Update preferences for the authenticated user."""
    if (
        payload.darkMode is None
        and payload.locale is None
        and payload.profilePublic is None
        and payload.emailPublic is None
        and payload.imageProcessingMode is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided.",
        )

    settings = await _get_or_create_settings(db, current_user.id)

    if payload.darkMode is not None:
        settings.dark_mode = payload.darkMode
    if payload.locale is not None:
        settings.locale = payload.locale
    if payload.profilePublic is not None:
        settings.is_public_profile = payload.profilePublic
    if payload.emailPublic is not None:
        settings.is_public_email = payload.emailPublic
    if payload.imageProcessingMode is not None:
        if payload.imageProcessingMode == "high_quality" and not current_user.isAdmin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="High quality image processing mode is only available for administrators.",
            )
        settings.image_processing_mode = payload.imageProcessingMode

    settings.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(settings)
    locale = cast(Literal["en", "pl"], settings.locale)
    return SettingsResponse(
        darkMode=settings.dark_mode,
        locale=locale,
        profilePublic=settings.is_public_profile,
        emailPublic=settings.is_public_email,
        imageProcessingMode=settings.image_processing_mode,
    )
