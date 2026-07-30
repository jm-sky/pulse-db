"""Validators for user module."""

from urllib.parse import urlparse

# Allowed avatar URL providers
ALLOWED_AVATAR_PROVIDERS = [
    "gravatar.com",
    "www.gravatar.com",
    "secure.gravatar.com",
    "i0.wp.com",  # WordPress CDN (often used for Gravatar)
    "i1.wp.com",
    "i2.wp.com",
]


def validate_avatar_url(url: str | None) -> bool:
    """Validate avatar URL against allowed providers.

    Only allows URLs from trusted avatar providers like Gravatar.
    This prevents users from using arbitrary URLs that could be used
    for tracking or malicious purposes.

    Args:
        url: Avatar URL to validate (can be None)

    Returns:
        True if URL is valid or None, False otherwise

    Examples:
        >>> validate_avatar_url("https://www.gravatar.com/avatar/abc123")
        True
        >>> validate_avatar_url("https://example.com/avatar.jpg")
        False
        >>> validate_avatar_url(None)
        True
    """
    if url is None:
        return True

    if not url.strip():
        return False

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    # Must be HTTPS
    if parsed.scheme != "https":
        return False

    # Check if hostname matches allowed providers
    hostname = parsed.netloc.lower()
    if not any(hostname == provider or hostname.endswith(f".{provider}") for provider in ALLOWED_AVATAR_PROVIDERS):
        return False

    # Basic URL format validation
    if not parsed.path:
        return False

    return True
