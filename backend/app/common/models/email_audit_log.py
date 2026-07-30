"""Email audit log model for tracking sent emails."""

import logging
from datetime import UTC, datetime

from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, DateTime

from app.core.database import Base

logger = logging.getLogger(__name__)

# Try to use ULID, fallback to UUID
try:
    from ulid import ULID

    USE_ULID = True
    logger.info("Using ULID for email audit log IDs")
except ImportError:
    import uuid

    USE_ULID = False
    logger.info("ULID not available, using UUID for email audit log IDs")


def generate_id() -> str:
    """Generate unique ID (ULID or UUID)."""
    if USE_ULID:
        return str(ULID())
    return str(uuid.uuid4())


class EmailAuditLog(Base):
    """
    Email audit log for tracking all sent emails.

    Stores metadata about every email sent by the system for:
    - Compliance (GDPR, SOC2)
    - Debugging and troubleshooting
    - Analytics and reporting
    - Retry failed sends
    """

    __tablename__ = "email_audit_log"

    # Primary key
    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=generate_id)

    # Recipients
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sender_email: Mapped[str | None] = mapped_column(String(255))

    # Content
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    html_body: Mapped[str | None] = mapped_column(Text)
    text_body: Mapped[str | None] = mapped_column(Text)

    # Template info
    template_name: Mapped[str | None] = mapped_column(String(100), index=True)
    template_context: Mapped[dict | None] = mapped_column(JSON)

    # Status & Tracking
    # Status: pending, sent, failed, bounced
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True, default="pending")
    adapter: Mapped[str] = mapped_column(String(50), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(50))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    # Extra metadata (JSON for flexibility)
    extra_metadata: Mapped[dict | None] = mapped_column(JSON)

    # Related entities (optional foreign keys)
    user_id: Mapped[str | None] = mapped_column(String(26), index=True)
    related_entity_type: Mapped[str | None] = mapped_column(String(50))
    related_entity_id: Mapped[str | None] = mapped_column(String(26))

    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_email_audit_status_created", "status", "created_at"),
        Index("idx_email_audit_user_created", "user_id", "created_at"),
        Index("idx_email_audit_template_created", "template_name", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<EmailAuditLog(id={self.id}, to={self.recipient_email}, status={self.status})>"

    def to_dict(self) -> dict:
        """Convert to dictionary (useful for API responses)."""
        return {
            "id": self.id,
            "recipient_email": self.recipient_email,
            "sender_email": self.sender_email,
            "subject": self.subject,
            "template_name": self.template_name,
            "status": self.status,
            "adapter": self.adapter,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "failed_at": self.failed_at.isoformat() if self.failed_at else None,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "retry_count": self.retry_count,
            "user_id": self.user_id,
        }
