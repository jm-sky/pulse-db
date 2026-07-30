"""ID generation utilities.

Provides centralized ID generation using ULID (if available) or UUID fallback.
This eliminates duplication across all repositories.
"""

import logging

logger = logging.getLogger(__name__)

# Try to import ULID, fallback to UUID
try:
    from ulid import ULID

    USE_ULID = True
    logger.debug("Using ULID for ID generation")
except ImportError:
    import uuid

    USE_ULID = False
    logger.debug("ULID not available, using UUID for ID generation")


def generate_id() -> str:
    """Generate unique ID using ULID or UUID.

    Returns:
        str: Unique ID as string

    Note:
        - ULID is preferred (lexicographically sortable, timestamp-based)
        - Falls back to UUID v4 if ULID package is not installed
    """
    if USE_ULID:
        return str(ULID())
    return str(uuid.uuid4())


def is_using_ulid() -> bool:
    """Check if ULID is being used for ID generation.

    Returns:
        bool: True if ULID is available and being used, False if using UUID
    """
    return USE_ULID
