"""Email service with adapter pattern for sending emails.

This module provides email functionality with adapters:
- FileEmailAdapter: Saves emails to files (development/testing)
- SMTPEmailAdapter: Sends emails via SMTP (production)
- RetrySMTPAdapter: SMTP with retry and exponential backoff
- AuditEmailAdapter: Wraps any adapter with audit logging

Usage:
    from app.core.email import get_email_service

    email_service = get_email_service()
    await email_service.send_welcome_email("user@example.com", "John Doe")
"""

from .adapter import EmailAdapter
from .audit_adapter import AuditEmailAdapter
from .retry_smtp_adapter import RetrySMTPAdapter
from .service import EmailService, get_email_service, get_email_service_with_audit

__all__ = [
    "EmailService",
    "EmailAdapter",
    "AuditEmailAdapter",
    "RetrySMTPAdapter",
    "get_email_service",
    "get_email_service_with_audit",
]
