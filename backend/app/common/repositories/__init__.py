"""Common repositories shared across modules."""

from .email_audit_repository import EmailAuditRepository, get_email_audit_repository

__all__ = ["EmailAuditRepository", "get_email_audit_repository"]
