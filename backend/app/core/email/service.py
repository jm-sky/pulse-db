"""Email service for sending various types of emails."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import EmailSettings, settings

from .i18n import DEFAULT_LOCALE, SupportedLocale, get_translations

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from .adapter import EmailAdapter

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending templated emails."""

    adapter: "EmailAdapter"
    templates_dir: Path
    jinja_env: Environment

    def __init__(self, adapter: "EmailAdapter"):
        """Initialize email service with adapter.

        Args:
            adapter: Email adapter (FileEmailAdapter or SMTPEmailAdapter)
        """
        self.adapter = adapter
        self.templates_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        # Primary color from frontend: oklch(0.606 0.25 292) converted to hex for email compatibility
        self.primary_color = "#7c3aed"

    def _render_translation(self, translations: dict[str, object], key: str, context: dict[str, object]) -> str:
        """Render a translation string with context variables.

        Args:
            translations: Translations dictionary
            key: Translation key (e.g., "welcome.subject")
            context: Context variables for template rendering

        Returns:
            Rendered translation string
        """
        # Navigate through nested keys (e.g., "welcome.subject")
        keys = key.split(".")
        value: object = translations
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return key  # Key not found, return key itself

        if not isinstance(value, str):
            return key  # Value is not a string, return key

        # Render with Jinja2 to support variables in translations
        from jinja2 import Template

        template = Template(value)
        return str(template.render(**context))

    async def send_email(
        self,
        to: str,
        subject: str,
        template_name: str,
        context: dict,
        from_email: str | None = None,
        user_id: str | None = None,
        related_entity_type: str | None = None,
        related_entity_id: str | None = None,
        locale: SupportedLocale | None = None,
        translations: dict | None = None,
    ) -> bool:
        """Send email using template.

        Args:
            to: Recipient email address
            subject: Email subject (can be a translation key if translations provided)
            template_name: Name of template file (without .html)
            context: Template context variables
            from_email: Sender email address (optional)
            user_id: Related user ID for audit logging (optional)
            related_entity_type: Type of related entity (optional)
            related_entity_id: ID of related entity (optional)
            locale: Locale for translations (optional)
            translations: Translations dictionary (optional, loaded automatically if locale provided)

        Returns:
            True if email sent successfully
        """
        try:
            # Load translations if locale provided
            if translations is None and locale:
                translations = get_translations(locale)

            # Render subject if it's a translation key
            if translations and subject.startswith("translation:"):
                translation_key = subject.replace("translation:", "")
                subject = self._render_translation(translations, translation_key, context)

            # Add common context variables (app_name, primary_color, frontend_url)
            context_with_defaults = {
                "app_name": settings.app.display_name,
                "primary_color": self.primary_color,
                "frontend_url": settings.frontend_url,
                **context,  # User-provided context overrides defaults
            }

            # Add translations to context if available
            if translations:
                context_with_defaults["t"] = translations
                context_with_defaults["locale"] = locale or DEFAULT_LOCALE

                # Add helper function for translations in templates
                # Note: translations is guaranteed to be a dict here
                def translate(key: str, **kwargs: object) -> str:
                    """Helper function for translations in templates."""
                    assert translations is not None
                    return self._render_translation(translations, key, {**context_with_defaults, **kwargs})

                context_with_defaults["translate"] = translate
            else:
                context_with_defaults["locale"] = DEFAULT_LOCALE

            # Load and render template
            template = self.jinja_env.get_template(f"{template_name}.html")
            html_body = template.render(**context_with_defaults)

            # Generate text version (simple strip of HTML tags)
            text_body = self._html_to_text(html_body)

            # Send via adapter
            # Add audit parameters if adapter supports them (AuditEmailAdapter)
            if hasattr(self.adapter, "repository"):
                # This is an AuditEmailAdapter - call with all params
                # Use type: ignore since AuditEmailAdapter extends base signature
                return await self.adapter.send_email(  # type: ignore[call-arg]
                    to=to,
                    subject=subject,
                    html_body=html_body,
                    text_body=text_body,
                    from_email=from_email,
                    template_name=template_name,
                    template_context=context,
                    user_id=user_id,
                    related_entity_type=related_entity_type,
                    related_entity_id=related_entity_id,
                )
            else:
                # Standard adapter
                return await self.adapter.send_email(
                    to=to,
                    subject=subject,
                    html_body=html_body,
                    text_body=text_body,
                    from_email=from_email,
                )

        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return False

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text (simple implementation).

        Args:
            html: HTML string

        Returns:
            Plain text version
        """
        # Simple HTML to text conversion
        import re

        text = re.sub(r"<[^>]+>", "", html)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    async def send_welcome_email(
        self,
        to: str,
        name: str,
        user_id: str | None = None,
        locale: SupportedLocale | None = None,
        translations: dict | None = None,
    ) -> bool:
        """Send welcome email to new user.

        Args:
            to: Recipient email address
            name: User name
            user_id: User ID for audit logging (optional)
            locale: Locale for translations (optional)
            translations: Translations dictionary (optional, loaded automatically if locale provided)

        Returns:
            True if email sent successfully
        """
        context = {"name": name, "email": to}
        subject = f"Welcome to {settings.app.display_name}!"
        if translations:
            subject = "translation:welcome.subject"

        return await self.send_email(
            to=to,
            subject=subject,
            template_name="welcome",
            context=context,
            user_id=user_id,
            related_entity_type="user" if user_id else None,
            related_entity_id=user_id,
            locale=locale,
            translations=translations,
        )

    async def send_email_verification_email(
        self,
        to: str,
        name: str,
        verification_token: str,
        user_id: str | None = None,
        locale: SupportedLocale | None = None,
        translations: dict | None = None,
    ) -> bool:
        """Send email verification message.

        Args:
            to: Recipient email address
            name: User name
            verification_token: Email verification token
            user_id: User ID for audit logging (optional)
            locale: Locale for translations (optional)
            translations: Translations dictionary (optional, loaded automatically if locale provided)

        Returns:
            True if email sent successfully
        """
        verification_link = f"{settings.frontend_url}/auth/verify-email?token={verification_token}"
        context = {
            "name": name,
            "email": to,
            "verification_link": verification_link,
            "token": verification_token,
            "expires_hours": settings.security.email_verification_token_expires_hours,
        }
        subject = f"Verify your email address - {settings.app.display_name}"
        if translations:
            subject = "translation:email_verification.subject"

        return await self.send_email(
            to=to,
            subject=subject,
            template_name="email_verification",
            context=context,
            user_id=user_id,
            related_entity_type="user" if user_id else None,
            related_entity_id=user_id,
            locale=locale,
            translations=translations,
        )

    async def send_password_reset_email(
        self,
        to: str,
        name: str,
        reset_token: str,
        user_id: str | None = None,
        locale: SupportedLocale | None = None,
        translations: dict | None = None,
    ) -> bool:
        """Send password reset email.

        Args:
            to: Recipient email address
            name: User name
            reset_token: Password reset token
            user_id: User ID for audit logging (optional)
            locale: Locale for translations (optional)
            translations: Translations dictionary (optional, loaded automatically if locale provided)

        Returns:
            True if email sent successfully
        """
        reset_link = f"{settings.frontend_url}/reset-password?token={reset_token}"
        context = {
            "name": name,
            "email": to,
            "reset_link": reset_link,
            "token": reset_token,
            "expires_hours": settings.security.password_reset_token_expires_hours,
        }
        subject = f"Password Reset Request - {settings.app.display_name}"
        if translations:
            subject = "translation:password_reset.subject"

        return await self.send_email(
            to=to,
            subject=subject,
            template_name="password_reset",
            context=context,
            user_id=user_id,
            related_entity_type="user" if user_id else None,
            related_entity_id=user_id,
            locale=locale,
            translations=translations,
        )

    async def send_password_changed_email(
        self,
        to: str,
        name: str,
        ip_address: str | None = None,
        user_id: str | None = None,
        locale: SupportedLocale | None = None,
        translations: dict | None = None,
    ) -> bool:
        """Send password changed notification email.

        Args:
            to: Recipient email address
            name: User name
            ip_address: IP address where change occurred (optional)
            user_id: User ID for audit logging (optional)
            locale: Locale for translations (optional)
            translations: Translations dictionary (optional, loaded automatically if locale provided)

        Returns:
            True if email sent successfully
        """
        context = {
            "name": name,
            "email": to,
            "ip_address": ip_address or "Unknown",
        }
        subject = f"Password Changed - {settings.app.display_name}"
        if translations:
            subject = "translation:password_changed.subject"

        return await self.send_email(
            to=to,
            subject=subject,
            template_name="password_changed",
            context=context,
            user_id=user_id,
            related_entity_type="user" if user_id else None,
            related_entity_id=user_id,
            locale=locale,
            translations=translations,
        )

    async def send_account_deleted_email(
        self,
        to: str,
        name: str,
        user_id: str | None = None,
        locale: SupportedLocale | None = None,
        translations: dict | None = None,
    ) -> bool:
        """Send account deletion confirmation email.

        Args:
            to: Recipient email address
            name: User name
            user_id: User ID for audit logging (optional)
            locale: Locale for translations (optional)
            translations: Translations dictionary (optional, loaded automatically if locale provided)

        Returns:
            True if email sent successfully
        """
        context = {"name": name, "email": to}
        subject = f"Account Deleted - {settings.app.display_name}"
        if translations:
            subject = "translation:account_deleted.subject"

        return await self.send_email(
            to=to,
            subject=subject,
            template_name="account_deleted",
            context=context,
            user_id=user_id,
            related_entity_type="user" if user_id else None,
            related_entity_id=user_id,
            locale=locale,
            translations=translations,
        )


def get_email_service() -> EmailService:
    """Get email service instance with configured adapter.

    Automatically wraps adapters with:
    - RetrySMTPAdapter: If enable_retry=True (for SMTP only)
    - AuditEmailAdapter: If enable_audit=True

    Returns:
        EmailService instance
    """
    from .adapter import EmailAdapter
    from .file_adapter import FileEmailAdapter
    from .retry_smtp_adapter import RetrySMTPAdapter
    from .smtp_adapter import SMTPEmailAdapter

    # Get email settings from config
    email_settings: EmailSettings | None = getattr(settings, "email", None)

    adapter: EmailAdapter
    if not email_settings or not email_settings.enabled:
        # Email disabled, use file adapter as fallback
        logger.warning("Email service is disabled, using file adapter")
        adapter = FileEmailAdapter(file_path="./emails")
        return EmailService(adapter)

    # Choose base adapter based on configuration
    if email_settings.adapter == "smtp":
        # Use retry SMTP if enabled
        if email_settings.enable_retry:
            adapter = RetrySMTPAdapter(
                host=email_settings.smtp_host,
                port=email_settings.smtp_port,
                user=email_settings.smtp_user,
                password=email_settings.smtp_password,
                from_email=email_settings.smtp_from,
                use_tls=email_settings.smtp_use_tls,
                max_retries=email_settings.max_retries,
            )
            logger.info(f"Using RetrySMTPAdapter with {email_settings.max_retries} " f"max retries")
        else:
            adapter = SMTPEmailAdapter(
                host=email_settings.smtp_host,
                port=email_settings.smtp_port,
                user=email_settings.smtp_user,
                password=email_settings.smtp_password,
                from_email=email_settings.smtp_from,
                use_tls=email_settings.smtp_use_tls,
            )
    else:
        # Default to file adapter
        adapter = FileEmailAdapter(file_path=email_settings.file_path)

    return EmailService(adapter)


def get_email_service_with_audit(
    db: "AsyncSession",
) -> EmailService:
    """Get email service with audit logging enabled.

    This is a request-scoped dependency that wraps the email adapter
    with AuditEmailAdapter when audit logging is enabled in settings.

    Use this as a FastAPI dependency:
        @router.post("/send-email")
        async def send_email(
            email_service: EmailService = Depends(get_email_service_with_audit)
        ):
            await email_service.send_welcome_email(...)

    Args:
        db: Database session (FastAPI dependency)

    Returns:
        EmailService instance with audit support if enabled
    """
    from .adapter import EmailAdapter
    from .audit_adapter import AuditEmailAdapter
    from .file_adapter import FileEmailAdapter
    from .retry_smtp_adapter import RetrySMTPAdapter
    from .smtp_adapter import SMTPEmailAdapter

    # Get email settings from config
    email_settings: EmailSettings | None = getattr(settings, "email", None)

    adapter: EmailAdapter
    if not email_settings or not email_settings.enabled:
        # Email disabled, use file adapter as fallback
        adapter = FileEmailAdapter(file_path="./emails")
        return EmailService(adapter)

    # Choose base adapter based on configuration
    if email_settings.adapter == "smtp":
        # Use retry SMTP if enabled
        if email_settings.enable_retry:
            adapter = RetrySMTPAdapter(
                host=email_settings.smtp_host,
                port=email_settings.smtp_port,
                user=email_settings.smtp_user,
                password=email_settings.smtp_password,
                from_email=email_settings.smtp_from,
                use_tls=email_settings.smtp_use_tls,
                max_retries=email_settings.max_retries,
            )
        else:
            adapter = SMTPEmailAdapter(
                host=email_settings.smtp_host,
                port=email_settings.smtp_port,
                user=email_settings.smtp_user,
                password=email_settings.smtp_password,
                from_email=email_settings.smtp_from,
                use_tls=email_settings.smtp_use_tls,
            )
    else:
        # Default to file adapter
        adapter = FileEmailAdapter(file_path=email_settings.file_path)

    # Wrap with audit adapter if enabled
    if email_settings.enable_audit:
        adapter = AuditEmailAdapter(
            wrapped_adapter=adapter,
            db=db,
            store_body=True,  # Store full email body for audit trail
        )
        logger.debug("Email service created with audit logging enabled")

    return EmailService(adapter)
