"""Pydantic schemas for settings endpoints."""

from typing import Literal

from pydantic import BaseModel, Field

SupportedLocale = Literal["en", "pl"]


class SettingsResponse(BaseModel):
    darkMode: bool = Field(default=False)
    locale: SupportedLocale = Field(default="en")
    profilePublic: bool = Field(default=False)
    emailPublic: bool = Field(default=False)
    imageProcessingMode: str | None = Field(default="balanced")


class UpdateSettingsRequest(BaseModel):
    darkMode: bool | None = Field(default=None)
    locale: SupportedLocale | None = Field(default=None)
    profilePublic: bool | None = Field(default=None)
    emailPublic: bool | None = Field(default=None)
    imageProcessingMode: str | None = Field(default=None)
