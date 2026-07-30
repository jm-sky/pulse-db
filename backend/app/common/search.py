"""Search utilities for API endpoints.

This module provides reusable search functionality including
full-text search across multiple columns with SQL LIKE/ILIKE.
"""

from typing import Any

from sqlalchemy import Column, or_
from sqlalchemy.sql import ColumnElement


def build_search_filter(search_term: str | None, *columns: Column[Any], case_sensitive: bool = False) -> ColumnElement[bool] | None:
    """Build SQLAlchemy filter for searching across multiple columns.

    Args:
        search_term: Search term (can be None)
        *columns: SQLAlchemy column objects to search in
        case_sensitive: Whether search should be case-sensitive (default: False)

    Returns:
        SQLAlchemy filter condition or None if no search term

    Usage:
        # Search in single column
        search_filter = build_search_filter(
            search_term="john",
            UserDB.name
        )

        # Search across multiple columns
        search_filter = build_search_filter(
            search_term="admin",
            UserDB.name,
            UserDB.email,
            UserDB.role
        )

        # Apply to query
        stmt = select(UserDB)
        if search_filter is not None:
            stmt = stmt.where(search_filter)

    Examples:
        >>> # Case-insensitive search (default)
        >>> filter = build_search_filter("john", UserDB.name)
        >>> # Generates: LOWER(name) LIKE LOWER('%john%')

        >>> # Case-sensitive search
        >>> filter = build_search_filter("John", UserDB.name, case_sensitive=True)
        >>> # Generates: name LIKE '%John%'

        >>> # Multiple columns
        >>> filter = build_search_filter("test", UserDB.name, UserDB.email)
        >>> # Generates: LOWER(name) LIKE '%test%' OR LOWER(email) LIKE '%test%'
    """
    if not search_term or not columns:
        return None

    search_pattern = f"%{search_term}%"

    if case_sensitive:
        # Case-sensitive search using LIKE
        conditions = [col.like(search_pattern) for col in columns]
    else:
        # Case-insensitive search using ILIKE or lower()
        conditions = [col.ilike(search_pattern) for col in columns]

    # Combine all conditions with OR
    return or_(*conditions)


class SearchMixin:
    """Mixin class for adding search functionality to repositories.

    This mixin provides a standardized way to add search capabilities
    to repository classes.

    Usage:
        class UserRepository(SearchMixin):
            def __init__(self, db: AsyncSession):
                self.db = db
                # Define searchable columns
                self._search_columns = [UserDB.name, UserDB.email, UserDB.role]

            async def get_users(
                self,
                search: str | None = None,
                skip: int = 0,
                limit: int = 100
            ):
                stmt = select(UserDB)

                # Apply search filter
                if search:
                    stmt = self.apply_search(stmt, search)

                stmt = stmt.offset(skip).limit(limit)
                result = await self.db.execute(stmt)
                return result.scalars().all()
    """

    _search_columns: list[Any] = []
    _case_sensitive: bool = False

    def apply_search(self, query: Any, search_term: str | None) -> Any:
        """Apply search filter to query.

        Args:
            query: SQLAlchemy query/statement
            search_term: Search term

        Returns:
            Query with search filter applied
        """
        if not search_term or not self._search_columns:
            return query

        search_filter = build_search_filter(search_term, *self._search_columns, case_sensitive=self._case_sensitive)

        if search_filter is not None:
            return query.where(search_filter)

        return query


def highlight_search_term(text: str, search_term: str, case_sensitive: bool = False) -> str:
    """Highlight search term in text (useful for UI).

    This is a helper function for highlighting search results.
    In a real application, this would typically be done on the frontend,
    but it's included here for completeness.

    Args:
        text: Original text
        search_term: Term to highlight
        case_sensitive: Whether matching should be case-sensitive

    Returns:
        Text with search term wrapped in <mark> tags

    Example:
        >>> highlight_search_term("Hello World", "world")
        'Hello <mark>World</mark>'
    """
    if not search_term or not text:
        return text

    if case_sensitive:
        return text.replace(search_term, f"<mark>{search_term}</mark>")
    else:
        # Case-insensitive replace
        import re

        pattern = re.compile(re.escape(search_term), re.IGNORECASE)
        return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", text)
