"""SQLAlchemy models for Two-Factor (TOTP) configuration."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TotpConfigDB(Base):
    """TOTP configuration per user.

    Stores encrypted TOTP secret and hashed backup codes.
    """

    __tablename__ = "totp_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    secret: Mapped[str] = mapped_column(Text, nullable=False, comment="Encrypted TOTP secret")
    backup_codes: Mapped[str] = mapped_column(Text, nullable=False, comment="JSON array of hashed backup codes")
    backup_codes_used: Mapped[str | None] = mapped_column(Text, nullable=True, comment="JSON array of used backup code hashes")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PasskeyDB(Base):
    """WebAuthn passkey configuration per user.

    Users can have multiple passkeys (different devices).
    """

    __tablename__ = "passkeys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    credential_id: Mapped[str] = mapped_column(
        String(1024),
        unique=True,
        nullable=False,
        index=True,
        comment="Base64url-encoded credential ID",
    )
    public_key: Mapped[str] = mapped_column(Text, nullable=False, comment="Encrypted public key")
    counter: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Signature counter for replay attack prevention",
    )
    aaguid: Mapped[str | None] = mapped_column(String(36), nullable=True, comment="Authenticator AAGUID")
    transports: Mapped[str | None] = mapped_column(Text, nullable=True, comment="JSON array of transport types")
    backup_eligible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="WebAuthn backup eligible flag")
    backup_state: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="WebAuthn backup state flag")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
