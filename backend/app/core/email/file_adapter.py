"""File-based email adapter for development and testing.

This adapter saves emails to files instead of sending them.
Useful for development, testing, and debugging.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from .adapter import EmailAdapter

logger = logging.getLogger(__name__)


class FileEmailAdapter(EmailAdapter):
    """File-based email adapter that saves emails to files."""

    file_path: Path

    def __init__(self, file_path: str = "./emails"):
        """Initialize file email adapter.

        Args:
            file_path: Directory path where emails will be saved
        """
        self.file_path = Path(file_path)
        self.file_path.mkdir(parents=True, exist_ok=True)

    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
        from_email: str | None = None,
    ) -> bool:
        """Save email to file instead of sending.

        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional)
            from_email: Sender email address (optional)

        Returns:
            True if email saved successfully
        """
        try:
            # Create date-based subdirectory
            date_str = datetime.now().strftime("%Y-%m-%d")
            date_dir = self.file_path / date_str
            date_dir.mkdir(parents=True, exist_ok=True)

            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            # Sanitize email for filename
            safe_email = to.replace("@", "_at_").replace(".", "_")
            filename = f"{timestamp}_{safe_email}.html"

            # Save HTML file
            email_file = date_dir / filename
            email_file.write_text(html_body, encoding="utf-8")

            # Save metadata as JSON
            metadata_file = date_dir / f"{timestamp}_{safe_email}.json"
            metadata = {
                "to": to,
                "from": from_email,
                "subject": subject,
                "timestamp": datetime.now().isoformat(),
                "html_file": str(email_file.relative_to(self.file_path)),
                "text_body": text_body,
            }
            metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

            logger.info(f"Email saved to {email_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save email to file: {e}", exc_info=True)
            return False
