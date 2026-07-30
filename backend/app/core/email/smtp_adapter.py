"""SMTP email adapter for production email sending."""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP, SMTP_SSL

from app.core.email.adapter import EmailAdapter

logger = logging.getLogger(__name__)


class SMTPEmailAdapter(EmailAdapter):
    """SMTP email adapter for sending emails via SMTP server."""

    host: str
    port: int
    user: str
    password: str
    from_email: str
    use_tls: bool

    def __init__(
        self,
        host: str,
        port: int = 587,
        user: str = "",
        password: str = "",
        from_email: str = "noreply@example.com",
        use_tls: bool = True,
    ):
        """Initialize SMTP email adapter.

        Args:
            host: SMTP server hostname
            port: SMTP server port (default: 587 for TLS, 465 for SSL)
            user: SMTP username (optional for some servers)
            password: SMTP password (optional for some servers)
            from_email: Default sender email address
            use_tls: Use TLS encryption (default: True)
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_email = from_email
        self.use_tls = use_tls

    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
        from_email: str | None = None,
    ) -> bool:
        """Send email via SMTP.

        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional, fallback for HTML)
            from_email: Sender email address (uses default if not provided)

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            sender = from_email or self.from_email

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = to

            # Add text and HTML parts
            if text_body:
                text_part = MIMEText(text_body, "plain", "utf-8")
                msg.attach(text_part)

            html_part = MIMEText(html_body, "html", "utf-8")
            msg.attach(html_part)

            server: SMTP_SSL | SMTP

            # Send email
            if self.port == 465:
                # Use SSL for port 465
                server = SMTP_SSL(self.host, self.port)
            else:
                # Use TLS for port 587
                server = SMTP(self.host, self.port)
                if self.use_tls:
                    server.starttls()

            # Authenticate if credentials provided
            if self.user and self.password:
                server.login(self.user, self.password)

            server.send_message(msg)
            server.quit()

            logger.info(f"Email sent successfully to {to}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}", exc_info=True)
            return False
