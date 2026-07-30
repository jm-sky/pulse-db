"""SMTP email adapter with retry logic and exponential backoff.

This adapter wraps the standard SMTP adapter to add resilience
through automatic retries with exponential backoff for transient errors.
"""

import asyncio
import logging
from smtplib import (
    SMTPAuthenticationError,
    SMTPConnectError,
    SMTPDataError,
    SMTPException,
    SMTPHeloError,
    SMTPRecipientsRefused,
    SMTPSenderRefused,
    SMTPServerDisconnected,
)

from .adapter import EmailAdapter
from .smtp_adapter import SMTPEmailAdapter

logger = logging.getLogger(__name__)

# Permanent errors that should not be retried
PERMANENT_SMTP_ERRORS = (
    SMTPAuthenticationError,  # Wrong credentials
    SMTPRecipientsRefused,  # Invalid recipient email
    SMTPSenderRefused,  # Invalid sender email
)

# Transient errors that can be retried
TRANSIENT_SMTP_ERRORS = (
    SMTPServerDisconnected,  # Server connection lost
    SMTPConnectError,  # Failed to connect
    SMTPHeloError,  # HELO/EHLO error
    SMTPDataError,  # Error during data transmission
    ConnectionError,  # Network connection error
    TimeoutError,  # Network timeout
    OSError,  # OS-level network error
)


class RetrySMTPAdapter(EmailAdapter):
    """SMTP adapter with automatic retry and exponential backoff.

    This adapter wraps SMTPEmailAdapter and retries failed sends
    with exponential backoff for transient network/server errors.

    Retry delays: 1s, 2s, 4s, 8s, 16s (default max_retries=5)

    Example:
        adapter = RetrySMTPAdapter(
            host="smtp.gmail.com",
            port=587,
            user="user@gmail.com",
            password="password",
            max_retries=5,
            initial_delay=1.0
        )
        success = await adapter.send_email(...)
    """

    def __init__(
        self,
        host: str,
        port: int = 587,
        user: str = "",
        password: str = "",
        from_email: str = "noreply@example.com",
        use_tls: bool = True,
        max_retries: int = 5,
        initial_delay: float = 1.0,
    ):
        """Initialize retry SMTP adapter.

        Args:
            host: SMTP server hostname
            port: SMTP server port (default: 587 for TLS, 465 for SSL)
            user: SMTP username
            password: SMTP password
            from_email: Default sender email address
            use_tls: Use TLS encryption (default: True)
            max_retries: Maximum number of retry attempts (default: 5)
            initial_delay: Initial retry delay in seconds (default: 1.0)
        """
        self.smtp_adapter = SMTPEmailAdapter(
            host=host,
            port=port,
            user=user,
            password=password,
            from_email=from_email,
            use_tls=use_tls,
        )
        self.max_retries = max_retries
        self.initial_delay = initial_delay

    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
        from_email: str | None = None,
    ) -> bool:
        """Send email with automatic retry on transient errors.

        This method will retry up to max_retries times with exponential
        backoff (1s, 2s, 4s, 8s, 16s) for transient errors like network
        issues or server disconnections.

        Permanent errors (authentication, invalid email) are not retried.

        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional)
            from_email: Sender email address (optional)

        Returns:
            True if email sent successfully, False otherwise
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                # Try to send email
                success = await self.smtp_adapter.send_email(
                    to=to,
                    subject=subject,
                    html_body=html_body,
                    text_body=text_body,
                    from_email=from_email,
                )

                if success:
                    if attempt > 0:
                        logger.info(f"Email sent successfully to {to} " f"after {attempt} retries")
                    return True

                # If send_email returned False without exception,
                # treat as transient error and retry
                if attempt < self.max_retries:
                    delay = self.initial_delay * (2**attempt)
                    logger.warning(f"Email send to {to} failed (returned False), " f"retrying in {delay}s (attempt {attempt + 1}/" f"{self.max_retries})")
                    await asyncio.sleep(delay)
                    continue

                return False

            except PERMANENT_SMTP_ERRORS as e:
                # Don't retry permanent errors
                logger.error(f"Permanent SMTP error sending to {to}: " f"{type(e).__name__}: {e}. Not retrying.")
                return False

            except (*TRANSIENT_SMTP_ERRORS, SMTPException) as e:
                last_error = e

                if attempt < self.max_retries:
                    # Calculate exponential backoff delay
                    delay = self.initial_delay * (2**attempt)

                    logger.warning(f"Transient error sending to {to}: " f"{type(e).__name__}: {e}. " f"Retrying in {delay}s (attempt {attempt + 1}/" f"{self.max_retries})")

                    await asyncio.sleep(delay)
                else:
                    # Max retries exhausted
                    logger.error(
                        f"Failed to send email to {to} after " f"{self.max_retries} retries. " f"Last error: {type(e).__name__}: {e}",
                        exc_info=True,
                    )

        # All retries exhausted
        if last_error:
            logger.error(f"All {self.max_retries} retries exhausted for {to}. " f"Last error: {type(last_error).__name__}: {last_error}")

        return False

    def __repr__(self) -> str:
        """String representation."""
        return f"RetrySMTPAdapter(host={self.smtp_adapter.host}, " f"port={self.smtp_adapter.port}, " f"max_retries={self.max_retries})"
