"""Helper functions for application core functionality."""

import json

# Truthy string representations accepted for boolean env vars.
_TRUE_STRINGS = frozenset({"true", "1", "yes", "on"})


def parse_bool_value(v: str | bool | None) -> bool:
    """
    Parse a boolean value from an environment string or bool.

    Accepts common truthy string representations ("true", "1", "yes", "on",
    case-insensitive). Anything else (including ``None``) is ``False``.

    This is the single source of truth for boolean parsing across all
    Pydantic settings classes (previously duplicated as ``parse_enabled`` /
    ``parse_bool_field``).

    Examples:
        >>> parse_bool_value("true")
        True
        >>> parse_bool_value("0")
        False
        >>> parse_bool_value(True)
        True
        >>> parse_bool_value(None)
        False
    """
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in _TRUE_STRINGS
    return False


def parse_list_value(v: str | list[str] | None) -> list[str]:
    """
    Parse list value from JSON array or comma-separated string.

    Supports multiple input formats:
    - JSON array string: '["localhost","127.0.0.1"]' or ["localhost","127.0.0.1"]
    - Comma-separated string: "localhost,127.0.0.1"
    - Already parsed list: ["localhost", "127.0.0.1"]
    - None: returns empty list

    Args:
        v: Input value (string, list, or None)

    Returns:
        list[str]: Parsed list of strings

    Examples:
        >>> parse_list_value('["localhost","127.0.0.1"]')
        ['localhost', '127.0.0.1']
        >>> parse_list_value("localhost,127.0.0.1")
        ['localhost', '127.0.0.1']
        >>> parse_list_value(["localhost", "127.0.0.1"])
        ['localhost', '127.0.0.1']
        >>> parse_list_value(None)
        []
    """
    if v is None:
        return []
    if isinstance(v, list):
        return [str(item) for item in v]
    if isinstance(v, str):
        # Remove surrounding quotes if present
        v = v.strip().strip('"').strip("'")
        # Try JSON first (e.g., '["localhost","127.0.0.1"]' or ["localhost","127.0.0.1"])
        try:
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        # Fall back to comma-separated string (e.g., "localhost,127.0.0.1")
        return [item.strip() for item in v.split(",") if item.strip()]
    return []
