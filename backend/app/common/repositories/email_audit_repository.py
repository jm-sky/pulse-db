"""Database repository implementation for email audit log.

This module provides async PostgreSQL/SQLite repository using SQLAlchemy 2.0+
for tracking and auditing all emails sent by the system.
"""

import logging
from datetime import UTC, datetime

from fastapi import Depends
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.models import EmailAuditLog
from app.common.search import SearchMixin
from app.core.database import get_db

logger = logging.getLogger(__name__)


class EmailAuditRepository(SearchMixin):
    """Email audit repository for async database operations.

    This implementation uses SQLAlchemy 2.0+ with async sessions
    for PostgreSQL or SQLite database access.

    Supports search across: recipient_email, subject, template_name
    """

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session.

        Args:
            db: Async SQLAlchemy session
        """
        self.db = db
        # Define searchable columns for SearchMixin
        self._search_columns = [
            EmailAuditLog.recipient_email,
            EmailAuditLog.subject,
            EmailAuditLog.template_name,
        ]
        self._case_sensitive = False

    async def create_log(
        self,
        recipient_email: str,
        subject: str,
        adapter: str,
        sender_email: str | None = None,
        html_body: str | None = None,
        text_body: str | None = None,
        template_name: str | None = None,
        template_context: dict | None = None,
        user_id: str | None = None,
        related_entity_type: str | None = None,
        related_entity_id: str | None = None,
        extra_metadata: dict | None = None,
        max_retries: int = 3,
    ) -> EmailAuditLog:
        """Create a new email audit log entry.

        Args:
            recipient_email: Email recipient
            subject: Email subject
            adapter: Email adapter used (smtp, file, ses, etc.)
            sender_email: Email sender (optional)
            html_body: HTML body content (optional)
            text_body: Plain text body (optional)
            template_name: Template used (optional)
            template_context: Template variables (optional)
            user_id: Related user ID (optional)
            related_entity_type: Type of related entity (optional)
            related_entity_id: ID of related entity (optional)
            extra_metadata: Additional metadata (optional)
            max_retries: Maximum retry attempts (default: 3)

        Returns:
            Created EmailAuditLog instance
        """
        log = EmailAuditLog(
            recipient_email=recipient_email,
            sender_email=sender_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            template_name=template_name,
            template_context=template_context,
            status="pending",
            adapter=adapter,
            user_id=user_id,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            extra_metadata=extra_metadata,
            max_retries=max_retries,
        )

        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)

        return log

    async def mark_sent(self, log_id: str) -> None:
        """Mark email as successfully sent.

        Args:
            log_id: Email audit log ID
        """
        stmt = select(EmailAuditLog).where(EmailAuditLog.id == log_id)
        result = await self.db.execute(stmt)
        log = result.scalar_one_or_none()

        if log:
            log.status = "sent"
            log.sent_at = datetime.now(UTC)
            await self.db.commit()

    async def mark_failed(
        self,
        log_id: str,
        error_message: str,
        error_code: str | None = None,
    ) -> None:
        """Mark email as failed.

        Args:
            log_id: Email audit log ID
            error_message: Error message
            error_code: Error code (optional)
        """
        stmt = select(EmailAuditLog).where(EmailAuditLog.id == log_id)
        result = await self.db.execute(stmt)
        log = result.scalar_one_or_none()

        if log:
            log.status = "failed"
            log.failed_at = datetime.now(UTC)
            log.error_message = error_message
            log.error_code = error_code
            log.retry_count += 1
            await self.db.commit()

    async def get_by_id(self, log_id: str) -> EmailAuditLog | None:
        """Get email audit log by ID.

        Args:
            log_id: Email audit log ID

        Returns:
            EmailAuditLog instance or None if not found
        """
        stmt = select(EmailAuditLog).where(EmailAuditLog.id == log_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_emails(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
        template_name: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        search: str | None = None,
    ) -> tuple[list[EmailAuditLog], int]:
        """Get emails sent to a specific user with pagination.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum records to return
            status: Filter by status (optional)
            template_name: Filter by template (optional)
            start_date: Filter emails after this date (optional)
            end_date: Filter emails before this date (optional)
            search: Search term (optional)

        Returns:
            Tuple of (list of emails, total count)
        """
        # Base query
        stmt = select(EmailAuditLog).where(EmailAuditLog.user_id == user_id)

        # Apply filters
        filters = []
        if status:
            filters.append(EmailAuditLog.status == status)
        if template_name:
            filters.append(EmailAuditLog.template_name == template_name)
        if start_date:
            filters.append(EmailAuditLog.created_at >= start_date)
        if end_date:
            filters.append(EmailAuditLog.created_at <= end_date)

        if filters:
            stmt = stmt.where(and_(*filters))

        # Apply search
        if search:
            stmt = self.apply_search(stmt, search)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Order by newest first and paginate
        stmt = stmt.order_by(EmailAuditLog.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        emails = result.scalars().all()

        return list(emails), total

    async def get_failed_emails(
        self,
        limit: int = 100,
        exclude_max_retries: bool = True,
    ) -> list[EmailAuditLog]:
        """Get failed emails that can be retried.

        Args:
            limit: Maximum number of emails to return
            exclude_max_retries: Exclude emails that have reached max retries

        Returns:
            List of failed email audit logs
        """
        stmt = select(EmailAuditLog).where(EmailAuditLog.status == "failed")

        if exclude_max_retries:
            stmt = stmt.where(EmailAuditLog.retry_count < EmailAuditLog.max_retries)

        stmt = stmt.order_by(EmailAuditLog.failed_at.desc()).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_retries(self, limit: int = 100) -> list[EmailAuditLog]:
        """Get pending emails waiting for retry.

        Args:
            limit: Maximum number of emails to return

        Returns:
            List of pending email audit logs
        """
        stmt = (
            select(EmailAuditLog)
            .where(
                and_(
                    EmailAuditLog.status == "pending",
                    EmailAuditLog.retry_count > 0,
                )
            )
            .order_by(EmailAuditLog.created_at.asc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_emails(
        self,
        status: str | None = None,
        user_id: str | None = None,
        template_name: str | None = None,
        adapter: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        search: str | None = None,
    ) -> int:
        """Count email audit logs with filters.

        Args:
            status: Filter by status (optional)
            user_id: Filter by user ID (optional)
            template_name: Filter by template (optional)
            adapter: Filter by adapter (optional)
            start_date: Filter emails after this date (optional)
            end_date: Filter emails before this date (optional)
            search: Search term (optional)

        Returns:
            Total count of emails matching criteria
        """
        stmt = select(func.count(EmailAuditLog.id))

        filters = []
        if status:
            filters.append(EmailAuditLog.status == status)
        if user_id:
            filters.append(EmailAuditLog.user_id == user_id)
        if template_name:
            filters.append(EmailAuditLog.template_name == template_name)
        if adapter:
            filters.append(EmailAuditLog.adapter == adapter)
        if start_date:
            filters.append(EmailAuditLog.created_at >= start_date)
        if end_date:
            filters.append(EmailAuditLog.created_at <= end_date)

        if filters:
            stmt = stmt.where(and_(*filters))

        # Apply search
        if search:
            stmt = self.apply_search(stmt, search)

        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_emails_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> tuple[list[EmailAuditLog], int]:
        """Get emails by status with pagination.

        Args:
            status: Email status (pending, sent, failed, bounced)
            skip: Number of records to skip
            limit: Maximum records to return
            search: Search term (optional)

        Returns:
            Tuple of (list of emails, total count)
        """
        stmt = select(EmailAuditLog).where(EmailAuditLog.status == status)

        if search:
            stmt = self.apply_search(stmt, search)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Order and paginate
        stmt = stmt.order_by(EmailAuditLog.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        emails = result.scalars().all()

        return list(emails), total


def get_email_audit_repository(
    db: AsyncSession = Depends(get_db),
) -> EmailAuditRepository:
    """FastAPI dependency to get email audit repository instance.

    Args:
        db: Async database session from dependency

    Returns:
        EmailAuditRepository instance configured with the session

    Example:
        @router.get("/email-audit")
        async def list_emails(
            repo: EmailAuditRepository = Depends(get_email_audit_repository)
        ):
            return await repo.get_user_emails(user_id="...")
    """
    return EmailAuditRepository(db)
