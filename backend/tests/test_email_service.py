"""Unit tests for EmailService."""

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.email.file_adapter import FileEmailAdapter
from app.core.email.service import EmailService


@pytest.fixture
def mock_adapter() -> Any:
    """Create a mock email adapter."""
    adapter = AsyncMock()
    adapter.send_email = AsyncMock(return_value=True)
    return adapter


@pytest.fixture
def email_service(mock_adapter: Any) -> EmailService:
    """Create an EmailService instance with mock adapter."""
    return EmailService(adapter=mock_adapter)


@pytest.mark.asyncio
async def test_send_email_renders_template(email_service: EmailService, mock_adapter: Any) -> None:
    """Test that send_email renders template and calls adapter."""
    result = await email_service.send_email(
        to="test@example.com",
        subject="Test Subject",
        template_name="welcome",
        context={
            "name": "John",
            "email": "test@example.com",
            "frontend_url": "http://localhost:3000",
        },
    )

    assert result is True
    mock_adapter.send_email.assert_called_once()

    # Verify adapter was called with rendered HTML
    call_args = mock_adapter.send_email.call_args
    assert call_args.kwargs["to"] == "test@example.com"
    assert call_args.kwargs["subject"] == "Test Subject"
    assert "html_body" in call_args.kwargs
    assert "text_body" in call_args.kwargs
    assert call_args.kwargs["html_body"] is not None
    assert call_args.kwargs["text_body"] is not None


@pytest.mark.asyncio
async def test_send_email_with_from_email(email_service: EmailService, mock_adapter: Any) -> None:
    """Test send_email with custom from_email."""
    await email_service.send_email(
        to="test@example.com",
        subject="Test",
        template_name="welcome",
        context={
            "name": "John",
            "email": "test@example.com",
            "frontend_url": "http://localhost:3000",
        },
        from_email="custom@example.com",
    )

    call_args = mock_adapter.send_email.call_args
    assert call_args.kwargs["from_email"] == "custom@example.com"


@pytest.mark.asyncio
async def test_send_email_handles_template_error(email_service: EmailService, mock_adapter: Any) -> None:
    """Test that send_email handles template errors gracefully."""
    # Use non-existent template
    result = await email_service.send_email(
        to="test@example.com",
        subject="Test",
        template_name="nonexistent",
        context={},
    )

    assert result is False
    mock_adapter.send_email.assert_not_called()


@pytest.mark.asyncio
async def test_send_email_handles_adapter_error(email_service: EmailService, mock_adapter: Any) -> None:
    """Test that send_email handles adapter errors gracefully."""
    mock_adapter.send_email.return_value = False

    result = await email_service.send_email(
        to="test@example.com",
        subject="Test",
        template_name="welcome",
        context={
            "name": "John",
            "email": "test@example.com",
            "frontend_url": "http://localhost:3000",
        },
    )

    assert result is False


@pytest.mark.asyncio
async def test_html_to_text_converts_html_to_plain_text(
    email_service: EmailService,
) -> None:
    """Test _html_to_text converts HTML to plain text."""
    html = "<html><body><h1>Title</h1><p>Paragraph with <strong>bold</strong> text.</p></body></html>"
    text = email_service._html_to_text(html)

    assert "Title" in text
    assert "Paragraph" in text
    assert "bold" in text
    assert "<" not in text
    assert ">" not in text
    assert "html" not in text.lower()
    assert "body" not in text.lower()


@pytest.mark.asyncio
async def test_send_welcome_email(email_service: EmailService, mock_adapter: Any) -> None:
    """Test send_welcome_email method."""
    result = await email_service.send_welcome_email(to="user@example.com", name="John Doe")

    assert result is True
    mock_adapter.send_email.assert_called_once()

    call_args = mock_adapter.send_email.call_args
    assert call_args.kwargs["to"] == "user@example.com"
    # Subject should contain "Welcome" and app name
    assert "Welcome" in call_args.kwargs["subject"]
    assert "welcome" in call_args.kwargs["html_body"].lower() or "John Doe" in call_args.kwargs["html_body"]


@pytest.mark.asyncio
async def test_send_password_reset_email(email_service: EmailService, mock_adapter: Any) -> None:
    """Test send_password_reset_email method."""
    reset_token = "test-reset-token-123"
    result = await email_service.send_password_reset_email(to="user@example.com", name="John", reset_token=reset_token)

    assert result is True
    mock_adapter.send_email.assert_called_once()

    call_args = mock_adapter.send_email.call_args
    assert call_args.kwargs["to"] == "user@example.com"
    # Subject should contain password reset indication
    assert "Password Reset" in call_args.kwargs["subject"]
    assert reset_token in call_args.kwargs["html_body"]


@pytest.mark.asyncio
async def test_send_password_changed_email(email_service: EmailService, mock_adapter: Any) -> None:
    """Test send_password_changed_email method."""
    result = await email_service.send_password_changed_email(to="user@example.com", name="John", ip_address="192.168.1.1")

    assert result is True
    mock_adapter.send_email.assert_called_once()

    call_args = mock_adapter.send_email.call_args
    assert call_args.kwargs["to"] == "user@example.com"
    # Subject should contain password changed indication
    assert "Password Changed" in call_args.kwargs["subject"]
    assert "192.168.1.1" in call_args.kwargs["html_body"]


@pytest.mark.asyncio
async def test_send_password_changed_email_without_ip(email_service: EmailService, mock_adapter: Any) -> None:
    """Test send_password_changed_email without IP address."""
    result = await email_service.send_password_changed_email(to="user@example.com", name="John")

    assert result is True
    call_args = mock_adapter.send_email.call_args
    assert "Unknown" in call_args.kwargs["html_body"]


@pytest.mark.asyncio
async def test_send_account_deleted_email(email_service: EmailService, mock_adapter: Any) -> None:
    """Test send_account_deleted_email method."""
    result = await email_service.send_account_deleted_email(to="user@example.com", name="John")

    assert result is True
    mock_adapter.send_email.assert_called_once()

    call_args = mock_adapter.send_email.call_args
    assert call_args.kwargs["to"] == "user@example.com"
    # Subject should contain account deleted indication
    assert "Account Deleted" in call_args.kwargs["subject"]


@pytest.mark.asyncio
async def test_email_service_initialization() -> None:
    """Test EmailService initialization with real adapter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        adapter = FileEmailAdapter(file_path=tmpdir)
        service = EmailService(adapter=adapter)

        assert service.adapter == adapter
        assert service.templates_dir.exists()
        assert service.jinja_env is not None


@pytest.mark.asyncio
async def test_send_email_with_real_template() -> None:
    """Test send_email with real template file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        adapter = FileEmailAdapter(file_path=tmpdir)
        service = EmailService(adapter=adapter)

        result = await service.send_email(
            to="test@example.com",
            subject="Test",
            template_name="welcome",
            context={
                "name": "Test User",
                "email": "test@example.com",
                "frontend_url": "http://localhost:3000",
            },
        )

        assert result is True

        # Verify email was saved
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_dir = Path(tmpdir) / date_str
        html_files = list(date_dir.glob("*.html"))
        assert len(html_files) > 0

        # Verify template was rendered
        html_content = html_files[0].read_text(encoding="utf-8")
        assert "Test User" in html_content


@pytest.mark.asyncio
async def test_get_email_service_with_file_adapter(monkeypatch: Any) -> None:
    """Test get_email_service returns service with file adapter when email disabled."""
    from app.core.email.service import get_email_service

    # Mock settings to have email disabled
    mock_settings = MagicMock()
    mock_settings.email = None
    monkeypatch.setattr("app.core.email.service.settings", mock_settings)

    service = get_email_service()

    assert service is not None
    assert isinstance(service.adapter, FileEmailAdapter)


@pytest.mark.asyncio
async def test_get_email_service_with_smtp_adapter(monkeypatch: Any) -> None:
    """Test get_email_service returns service with SMTP adapter when configured."""
    from app.core.email.service import get_email_service

    # Mock settings to have SMTP enabled (with retry disabled)
    mock_email_settings = MagicMock()
    mock_email_settings.enabled = True
    mock_email_settings.adapter = "smtp"
    mock_email_settings.smtp_host = "smtp.example.com"
    mock_email_settings.smtp_port = 587
    mock_email_settings.smtp_user = "user"
    mock_email_settings.smtp_password = "password"
    mock_email_settings.smtp_from = "noreply@example.com"
    mock_email_settings.smtp_use_tls = True
    mock_email_settings.enable_retry = False  # Disable retry to get plain SMTP adapter

    mock_settings = MagicMock()
    mock_settings.email = mock_email_settings
    monkeypatch.setattr("app.core.email.service.settings", mock_settings)

    service = get_email_service()

    assert service is not None
    from app.core.email.smtp_adapter import SMTPEmailAdapter

    assert isinstance(service.adapter, SMTPEmailAdapter)
