"""Unit tests for utility functions.

These tests cover pure functions that don't require database or complex mocking.
"""


class TestGenerateId:
    """Tests for ID generation utility."""

    def test_generate_id_returns_string(self) -> None:
        """Test that generate_id returns a string."""
        from app.common.id_utils import generate_id

        result = generate_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_id_unique(self) -> None:
        """Test that generate_id returns unique IDs."""
        from app.common.id_utils import generate_id

        ids = [generate_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All IDs should be unique

    def test_is_using_ulid_returns_bool(self) -> None:
        """Test that is_using_ulid returns a boolean."""
        from app.common.id_utils import is_using_ulid

        result = is_using_ulid()
        assert isinstance(result, bool)


class TestNormalizeEmail:
    """Tests for email normalization utility."""

    def test_normalize_email_lowercase(self) -> None:
        """Test that normalize_email converts to lowercase."""
        from app.common.repository_utils import normalize_email

        assert normalize_email("TEST@EXAMPLE.COM") == "test@example.com"
        assert normalize_email("Test@Example.Com") == "test@example.com"

    def test_normalize_email_strips_whitespace(self) -> None:
        """Test that normalize_email strips whitespace."""
        from app.common.repository_utils import normalize_email

        assert normalize_email("  test@example.com  ") == "test@example.com"
        assert normalize_email("\ttest@example.com\n") == "test@example.com"

    def test_normalize_email_combined(self) -> None:
        """Test normalize_email with both uppercase and whitespace."""
        from app.common.repository_utils import normalize_email

        assert normalize_email("  TEST@EXAMPLE.COM  ") == "test@example.com"

    def test_normalize_email_already_normalized(self) -> None:
        """Test normalize_email with already normalized email."""
        from app.common.repository_utils import normalize_email

        assert normalize_email("test@example.com") == "test@example.com"


class TestParseListValue:
    """Tests for parse_list_value helper function."""

    def test_parse_list_value_json_array(self) -> None:
        """Test parsing JSON array string."""
        from app.core.helpers import parse_list_value

        result = parse_list_value('["localhost","127.0.0.1"]')
        assert result == ["localhost", "127.0.0.1"]

    def test_parse_list_value_comma_separated(self) -> None:
        """Test parsing comma-separated string."""
        from app.core.helpers import parse_list_value

        result = parse_list_value("localhost,127.0.0.1")
        assert result == ["localhost", "127.0.0.1"]

    def test_parse_list_value_already_list(self) -> None:
        """Test with already parsed list."""
        from app.core.helpers import parse_list_value

        result = parse_list_value(["localhost", "127.0.0.1"])
        assert result == ["localhost", "127.0.0.1"]

    def test_parse_list_value_none(self) -> None:
        """Test with None value."""
        from app.core.helpers import parse_list_value

        result = parse_list_value(None)
        assert result == []

    def test_parse_list_value_empty_string(self) -> None:
        """Test with empty string."""
        from app.core.helpers import parse_list_value

        result = parse_list_value("")
        assert result == []

    def test_parse_list_value_single_value(self) -> None:
        """Test with single value."""
        from app.core.helpers import parse_list_value

        result = parse_list_value("localhost")
        assert result == ["localhost"]

    def test_parse_list_value_strips_whitespace(self) -> None:
        """Test that whitespace is stripped from values."""
        from app.core.helpers import parse_list_value

        result = parse_list_value("  localhost , 127.0.0.1  ")
        assert result == ["localhost", "127.0.0.1"]

    def test_parse_list_value_with_quotes(self) -> None:
        """Test JSON array with surrounding quotes."""
        from app.core.helpers import parse_list_value

        result = parse_list_value('"["localhost","127.0.0.1"]"')
        assert result == ["localhost", "127.0.0.1"]


class TestDetectLocaleFromAcceptLanguage:
    """Tests for Accept-Language header parsing."""

    def test_detect_locale_polish(self) -> None:
        """Test detection of Polish locale."""
        from app.core.email.i18n import detect_locale_from_accept_language

        result = detect_locale_from_accept_language("pl-PL,pl;q=0.9,en;q=0.8")
        assert result == "pl"

    def test_detect_locale_english(self) -> None:
        """Test detection of English locale."""
        from app.core.email.i18n import detect_locale_from_accept_language

        result = detect_locale_from_accept_language("en-US,en;q=0.9")
        assert result == "en"

    def test_detect_locale_with_quality_values(self) -> None:
        """Test that quality values are respected."""
        from app.core.email.i18n import detect_locale_from_accept_language

        # English has higher quality
        result = detect_locale_from_accept_language("pl;q=0.5,en;q=0.9")
        assert result == "en"

    def test_detect_locale_none_returns_default(self) -> None:
        """Test that None returns default locale."""
        from app.core.email.i18n import (
            DEFAULT_LOCALE,
            detect_locale_from_accept_language,
        )

        result = detect_locale_from_accept_language(None)
        assert result == DEFAULT_LOCALE

    def test_detect_locale_empty_string_returns_default(self) -> None:
        """Test that empty string returns default locale."""
        from app.core.email.i18n import (
            DEFAULT_LOCALE,
            detect_locale_from_accept_language,
        )

        result = detect_locale_from_accept_language("")
        assert result == DEFAULT_LOCALE

    def test_detect_locale_unsupported_returns_default(self) -> None:
        """Test that unsupported locale returns default."""
        from app.core.email.i18n import (
            DEFAULT_LOCALE,
            detect_locale_from_accept_language,
        )

        result = detect_locale_from_accept_language("de-DE,de;q=0.9,fr;q=0.8")
        assert result == DEFAULT_LOCALE

    def test_detect_locale_mixed_supported_unsupported(self) -> None:
        """Test with mix of supported and unsupported locales."""
        from app.core.email.i18n import detect_locale_from_accept_language

        # German first, but English is also present
        result = detect_locale_from_accept_language("de-DE,de;q=0.9,en;q=0.7")
        assert result == "en"

    def test_detect_locale_country_code_stripped(self) -> None:
        """Test that country codes are properly stripped."""
        from app.core.email.i18n import detect_locale_from_accept_language

        result = detect_locale_from_accept_language("en-GB,en-US;q=0.9")
        assert result == "en"

        result = detect_locale_from_accept_language("pl-PL")
        assert result == "pl"


class TestDefaultLocale:
    """Tests for default locale constant."""

    def test_default_locale_is_polish(self) -> None:
        """Test that default locale is Polish."""
        from app.core.email.i18n import DEFAULT_LOCALE

        assert DEFAULT_LOCALE == "pl"

    def test_supported_locale_type(self) -> None:
        """Test that SupportedLocale is properly defined."""
        from app.core.email.i18n import DEFAULT_LOCALE, SupportedLocale

        # DEFAULT_LOCALE should be a valid SupportedLocale
        locale: SupportedLocale = DEFAULT_LOCALE
        assert locale in ("pl", "en")
