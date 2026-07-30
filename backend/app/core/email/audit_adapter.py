"""Email audit adapter decorator for tracking sent emails.

This decorator wraps any EmailAdapter to add audit logging functionality,
storing all sent emails in the database for compliance and troubleshooting.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.repositories import EmailAuditRepository

from .adapter import EmailAdapter

logger = logging.getLogger(__name__)


class AuditEmailAdapter(EmailAdapter):
    """Decorator that adds audit logging to any EmailAdapter.

    This adapter wraps another adapter and logs all email operations
    to the database for audit trail, compliance, and troubleshooting.

    Example:
        # Wrap SMTP adapter with audit logging
        smtp_adapter = SMTPEmailAdapter(...)
        audit_adapter = AuditEmailAdapter(smtp_adapter, db_session)

        # Now all emails sent through audit_adapter are logged
        await audit_adapter.send_email(...)
    """

    def __init__(
        self,
        wrapped_adapter: EmailAdapter,
        db: AsyncSession,
        adapter_name: str | None = None,
        store_body: bool = True,
    ):
        """Initialize audit adapter.

        Args:
            wrapped_adapter: The actual email adapter to use for sending
            db: Database session for audit logging
            adapter_name: Name to store in audit log (defaults to wrapped adapter class name)
            store_body: Whether to store email body in database (default: True)
        """
        self.wrapped_adapter = wrapped_adapter
        self.db = db
        self.adapter_name = adapter_name or wrapped_adapter.__class__.__name__
        self.store_body = store_body
        self.repository = EmailAuditRepository(db)

    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
        from_email: str | None = None,
        template_name: str | None = None,
        template_context: dict | None = None,
        user_id: str | None = None,
        related_entity_type: str | None = None,
        related_entity_id: str | None = None,
        extra_metadata: dict | None = None,
    ) -> bool:
        """Send email with audit logging.

        This method:
        1. Creates audit log entry with status='pending'
        2. Attempts to send email using wrapped adapter
        3. Updates audit log with success/failure status

        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional)
            from_email: Sender email address (optional)
            template_name: Template used (optional, for audit)
            template_context: Template variables (optional, for audit)
            user_id: Related user ID (optional, for audit)
            related_entity_type: Type of related entity (optional, for audit)
            related_entity_id: ID of related entity (optional, for audit)
            extra_metadata: Additional metadata (optional, for audit)

        Returns:
            True if email sent successfully, False otherwise
        """
        # Create audit log entry
        try:
            audit_log = await self.repository.create_log(
                recipient_email=to,
                sender_email=from_email,
                subject=subject,
                html_body=html_body if self.store_body else None,
                text_body=text_body if self.store_body else None,
                template_name=template_name,
                template_context=template_context,
                adapter=self.adapter_name,
                user_id=user_id,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id,
                extra_metadata=extra_metadata,
            )

            logger.info(f"Created email audit log {audit_log.id} for {to} " f"(subject: {subject}, template: {template_name})")

        except Exception as e:
            logger.error(f"Failed to create email audit log for {to}: {e}", exc_info=True)
            # Continue with sending even if audit log fails
            # (don't let audit logging block email sending)
            audit_log = None

        # Try to send email using wrapped adapter
        try:
            success = await self.wrapped_adapter.send_email(
                to=to,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                from_email=from_email,
            )

            # Update audit log based on result
            if audit_log:
                if success:
                    await self.repository.mark_sent(audit_log.id)
                    logger.info(f"Email audit log {audit_log.id} marked as sent")
                else:
                    await self.repository.mark_failed(
                        audit_log.id,
                        error_message="Email adapter returned False (sending failed)",
                        error_code="SEND_FAILED",
                    )
                    logger.warning(f"Email audit log {audit_log.id} marked as failed " f"(adapter returned False)")

            return success

        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}", exc_info=True)

            # Update audit log with error
            if audit_log:
                error_message = f"{type(e).__name__}: {str(e)}"
                await self.repository.mark_failed(
                    audit_log.id,
                    error_message=error_message,
                    error_code=type(e).__name__,
                )
                logger.error(f"Email audit log {audit_log.id} marked as failed " f"with error: {error_message}")

            return False

    def __repr__(self) -> str:
        """String representation."""
        return f"AuditEmailAdapter(wrapped={self.wrapped_adapter.__class__.__name__})"
