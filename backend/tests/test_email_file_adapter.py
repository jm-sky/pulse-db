"""Unit tests for FileEmailAdapter."""

import json
import tempfile
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from app.core.email.file_adapter import FileEmailAdapter


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test emails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def file_adapter(temp_dir: Path) -> FileEmailAdapter:
    """Create a FileEmailAdapter instance with temporary directory."""
    return FileEmailAdapter(file_path=str(temp_dir))


@pytest.mark.asyncio
async def test_send_email_creates_files(file_adapter: FileEmailAdapter, temp_dir: Path) -> None:
    """Test that send_email creates HTML and JSON metadata files."""
    result = await file_adapter.send_email(
        to="test@example.com",
        subject="Test Subject",
        html_body="<html><body>Test content</body></html>",
        text_body="Test content",
        from_email="sender@example.com",
    )

    assert result is True

    # Check that date directory was created
    date_str = datetime.now().strftime("%Y-%m-%d")
    date_dir = temp_dir / date_str
    assert date_dir.exists()

    # Find created files
    html_files = list(date_dir.glob("*.html"))
    json_files = list(date_dir.glob("*.json"))

    assert len(html_files) == 1
    assert len(json_files) == 1

    # Verify HTML content
    html_content = html_files[0].read_text(encoding="utf-8")
    assert "Test content" in html_content

    # Verify JSON metadata
    json_content = json.loads(json_files[0].read_text(encoding="utf-8"))
    assert json_content["to"] == "test@example.com"
    assert json_content["from"] == "sender@example.com"
    assert json_content["subject"] == "Test Subject"
    assert json_content["text_body"] == "Test content"
    assert "timestamp" in json_content
    assert "html_file" in json_content


@pytest.mark.asyncio
async def test_send_email_without_text_body(file_adapter: FileEmailAdapter, temp_dir: Path) -> None:
    """Test send_email works without text_body."""
    result = await file_adapter.send_email(
        to="test@example.com",
        subject="Test Subject",
        html_body="<html><body>Test</body></html>",
    )

    assert result is True

    date_str = datetime.now().strftime("%Y-%m-%d")
    date_dir = temp_dir / date_str
    json_files = list(date_dir.glob("*.json"))

    assert len(json_files) == 1
    json_content = json.loads(json_files[0].read_text(encoding="utf-8"))
    assert json_content["text_body"] is None


@pytest.mark.asyncio
async def test_send_email_without_from_email(file_adapter: FileEmailAdapter, temp_dir: Path) -> None:
    """Test send_email works without from_email."""
    result = await file_adapter.send_email(
        to="test@example.com",
        subject="Test Subject",
        html_body="<html><body>Test</body></html>",
    )

    assert result is True

    date_str = datetime.now().strftime("%Y-%m-%d")
    date_dir = temp_dir / date_str
    json_files = list(date_dir.glob("*.json"))

    assert len(json_files) == 1
    json_content = json.loads(json_files[0].read_text(encoding="utf-8"))
    assert json_content["from"] is None


@pytest.mark.asyncio
async def test_send_email_creates_date_directories(file_adapter: FileEmailAdapter, temp_dir: Path) -> None:
    """Test that emails are organized by date."""
    await file_adapter.send_email(
        to="test1@example.com",
        subject="Test 1",
        html_body="<html><body>Test 1</body></html>",
    )

    await file_adapter.send_email(
        to="test2@example.com",
        subject="Test 2",
        html_body="<html><body>Test 2</body></html>",
    )

    date_str = datetime.now().strftime("%Y-%m-%d")
    date_dir = temp_dir / date_str

    assert date_dir.exists()
    html_files = list(date_dir.glob("*.html"))
    assert len(html_files) == 2


@pytest.mark.asyncio
async def test_send_email_sanitizes_email_in_filename(file_adapter: FileEmailAdapter, temp_dir: Path) -> None:
    """Test that email addresses are sanitized in filenames."""
    await file_adapter.send_email(
        to="test.user@example.com",
        subject="Test",
        html_body="<html><body>Test</body></html>",
    )

    date_str = datetime.now().strftime("%Y-%m-%d")
    date_dir = temp_dir / date_str
    html_files = list(date_dir.glob("*.html"))

    assert len(html_files) == 1
    # Check that @ and . are replaced in filename
    filename = html_files[0].name
    assert "@" not in filename
    assert "test_user_at_example_com" in filename or "_at_" in filename


@pytest.mark.asyncio
async def test_send_email_handles_exception(file_adapter: FileEmailAdapter, temp_dir: Path, mocker: Any) -> None:
    """Test that send_email handles exceptions gracefully."""
    # Mock Path.write_text to raise an exception
    mocker.patch.object(Path, "write_text", side_effect=PermissionError("Permission denied"))

    result = await file_adapter.send_email(
        to="test@example.com",
        subject="Test",
        html_body="<html><body>Test</body></html>",
    )

    assert result is False


@pytest.mark.asyncio
async def test_send_email_creates_directory_if_not_exists() -> None:
    """Test that adapter creates directory if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        non_existent_dir = Path(tmpdir) / "emails" / "subdir"
        adapter = FileEmailAdapter(file_path=str(non_existent_dir))

        result = await adapter.send_email(
            to="test@example.com",
            subject="Test",
            html_body="<html><body>Test</body></html>",
        )

        assert result is True
        assert non_existent_dir.exists()
