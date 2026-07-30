"""Pagination utilities for API endpoints.

This module provides reusable pagination functionality including
request parameters, response models, and helper functions.
"""

from typing import Any, Self, TypeVar

from pydantic import BaseModel, Field
from sqlalchemy.orm import Query

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Standard pagination parameters for API endpoints.

    Usage:
        @router.get("/items")
        async def list_items(
            skip: int = Query(default=0, ge=0),
            limit: int = Query(default=100, ge=1, le=1000)
        ):
            # Use skip and limit for database queries
            pass
    """

    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=100, ge=1, le=1000, description="Max records to return")


class PaginatedResponse[T](BaseModel):
    """Generic paginated response model.

    This provides a consistent pagination structure across all endpoints.
    Matches frontend PaginatedResponse interface.

    Usage:
        class UserListResponse(PaginatedResponse[UserResponse]):
            pass

        # Calculate page from skip
        page = skip // limit if limit > 0 else 0
        return UserListResponse(
            items=users,
            total=total_count,
            page=page,
            limit=limit
        )
    """

    items: list[T] = Field(description="List of items for current page")
    total: int = Field(description="Total number of items available")
    page: int = Field(description="Current page number (0-based)")
    limit: int = Field(description="Maximum items per page")
    hasMore: bool = Field(description="Whether more items are available")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        skip: int,
        limit: int,
    ) -> Self:
        """Create a PaginatedResponse from skip/limit pagination.

        This helper method converts skip-based pagination to page-based
        and automatically calculates hasMore.

        Args:
            items: List of items for current page
            total: Total number of items available
            skip: Number of items skipped
            limit: Maximum items per page (should be >= 1, enforced by endpoint validation)

        Returns:
            PaginatedResponse instance with calculated page and hasMore

        Note:
            - limit >= 1 is enforced by endpoint validation (ge=1 in Query params)
            - If limit were 0, page would be 0 and hasMore calculation would be incorrect,
              but this is prevented by endpoint validation
        """
        page = skip // limit if limit > 0 else 0
        has_more = (skip + len(items)) < total
        return cls(items=items, total=total, page=page, limit=limit, hasMore=has_more)


def paginate_query(query: Query[Any], skip: int = 0, limit: int = 100) -> Query[Any]:
    """Apply pagination to SQLAlchemy query.

    Args:
        query: SQLAlchemy query object
        skip: Number of records to skip
        limit: Maximum records to return

    Returns:
        Query with pagination applied

    Usage:
        stmt = select(UserDB).where(UserDB.is_active == True)
        stmt = paginate_query(stmt, skip=0, limit=50)
        result = await session.execute(stmt)
    """
    return query.offset(skip).limit(limit)
