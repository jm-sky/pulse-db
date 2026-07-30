"""Internationalization support for email templates."""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

SupportedLocale = Literal["pl", "en"]
DEFAULT_LOCALE: SupportedLocale = "pl"

# Cache for translations
_translations_cache: dict[str, dict] = {}


def _load_translations(locale: SupportedLocale) -> dict[str, Any]:
    """Load translations for a given locale.

    Args:
        locale: Locale code (pl or en)

    Returns:
        Dictionary with translations
    """
    if locale in _translations_cache:
        return _translations_cache[locale]

    translations_dir = Path(__file__).parent / "translations"
    translations_file = translations_dir / f"{locale}.json"

    try:
        with open(translations_file, encoding="utf-8") as f:
            translations: dict[str, Any] = json.load(f)
            _translations_cache[locale] = translations
            return translations
    except FileNotFoundError:
        logger.warning(f"Translations file not found for locale {locale}, using default")
        if locale != DEFAULT_LOCALE:
            return _load_translations(DEFAULT_LOCALE)
        return {}
    except Exception as e:
        logger.error(f"Failed to load translations for locale {locale}: {e}")
        if locale != DEFAULT_LOCALE:
            return _load_translations(DEFAULT_LOCALE)
        return {}


def get_translations(locale: SupportedLocale) -> dict[str, Any]:
    """Get translations for a given locale.

    Args:
        locale: Locale code (pl or en)

    Returns:
        Dictionary with translations
    """
    return _load_translations(locale)


def detect_locale_from_accept_language(accept_language: str | None) -> SupportedLocale:
    """Detect locale from Accept-Language header.

    Args:
        accept_language: Accept-Language header value (e.g., "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7")

    Returns:
        Detected locale (pl or en), defaults to DEFAULT_LOCALE
    """
    if not accept_language:
        return DEFAULT_LOCALE

    # Parse Accept-Language header
    # Format: "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7"
    languages = []
    for part in accept_language.split(","):
        part = part.strip()
        if ";" in part:
            lang, q = part.split(";", 1)
            try:
                quality = float(q.split("=")[1])
            except (ValueError, IndexError):
                quality = 1.0
        else:
            lang = part
            quality = 1.0

        # Extract language code (e.g., "pl-PL" -> "pl")
        lang_code = lang.split("-")[0].lower()
        languages.append((lang_code, quality))

    # Sort by quality (descending)
    languages.sort(key=lambda x: x[1], reverse=True)

    # Check for supported languages
    for lang_code, _ in languages:
        if lang_code == "pl":
            return "pl"
        if lang_code == "en":
            return "en"

    return DEFAULT_LOCALE


async def get_user_locale(
    db: "AsyncSession",
    user_id: str | None,
) -> SupportedLocale:
    """Get user locale from settings, or return default.

    Args:
        db: Database session
        user_id: User ID (optional)

    Returns:
        User locale (pl or en), defaults to DEFAULT_LOCALE
    """
    if not user_id:
        return DEFAULT_LOCALE

    try:
        from sqlalchemy import select

        from app.modules.settings.db_models import UserSettingsDB

        result = await db.execute(select(UserSettingsDB).where(UserSettingsDB.user_id == user_id))
        settings = result.scalars().first()

        if settings and settings.locale:
            # Map locale from database (en/pl) to SupportedLocale
            locale_str = settings.locale.lower()
            if locale_str == "pl":
                return "pl"
            elif locale_str == "en":
                return "en"
    except Exception as e:
        logger.warning(f"Failed to get user locale for user {user_id}: {e}")

    return DEFAULT_LOCALE


async def determine_email_locale(
    db: "AsyncSession",
    user_id: str | None,
    accept_language: str | None = None,
) -> SupportedLocale:
    """Determine email locale based on user settings, browser language, or default.

    Priority:
    1. User settings (if user_id provided)
    2. Accept-Language header (if provided)
    3. Default locale (pl)

    Args:
        db: Database session
        user_id: User ID (optional)
        accept_language: Accept-Language header value (optional)

    Returns:
        Determined locale (pl or en)
    """
    # Try user settings first
    if user_id:
        locale = await get_user_locale(db, user_id)
        if locale != DEFAULT_LOCALE or not accept_language:
            return locale

    # Try browser language
    if accept_language:
        locale = detect_locale_from_accept_language(accept_language)
        return locale

    # Default
    return DEFAULT_LOCALE
