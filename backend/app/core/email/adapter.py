"""Email adapter interface for different email sending implementations."""

from abc import ABC, abstractmethod


class EmailAdapter(ABC):
    """Abstract interface for email adapters.

    Implementations:
    - FileEmailAdapter: Saves emails to files (development/testing)
    - SMTPEmailAdapter: Sends emails via SMTP (production)
    """

    @abstractmethod
    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
        from_email: str | None = None,
    ) -> bool:
        """Send an email.

        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional, fallback for HTML)
            from_email: Sender email address (optional, uses default if not provided)

        Returns:
            True if email sent successfully, False otherwise
        """
        ...
