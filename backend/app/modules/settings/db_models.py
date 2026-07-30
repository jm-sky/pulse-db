"""Database models for user settings."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserSettingsDB(Base):
    """Stores per-user preferences such as dark mode and locale."""

    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    dark_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locale: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    default_containers_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_public_profile: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_public_email: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    image_processing_mode: Mapped[str | None] = mapped_column(String(20), nullable=True, default="balanced")
    preferred_2fa_method: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
