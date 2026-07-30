"""Pydantic models for Two-Factor (TOTP) API (camelCase)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TOTPConfig(BaseModel):
    """API model representing user's TOTP configuration."""

    id: str
    userId: str
    isEnabled: bool
    createdAt: datetime
    verifiedAt: datetime | None = None
    lastVerifiedAt: datetime | None = None
    backupCodesRemaining: int = Field(default=0)


class Passkey(BaseModel):
    """API model representing a WebAuthn passkey."""

    id: str
    userId: str
    name: str
    createdAt: datetime
    lastUsedAt: datetime | None = None
    isEnabled: bool
    userAgent: str | None = None
    aaguid: str | None = None
    transports: list[str] | None = None
    backupEligible: bool
    backupState: bool
