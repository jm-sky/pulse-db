"""Test commands for development and debugging.

This module provides test commands for various purposes like testing Sentry integration,
storage adapters (local and S3), and email functionality.
"""

import asyncio
from datetime import datetime

import typer
from rich.console import Console

from app.core.config import settings
from app.core.email import get_email_service
from app.core.storage.factory import get_storage_adapter

from ..main import COMMAND_GROUPS, show_group_interactive_menu

# Create test subcommand app
test_app = typer.Typer(
    name="test",
    help="Test commands for development and debugging",
    no_args_is_help=False,  # We handle no-args case ourselves for interactive mode
)

console = Console()


@test_app.callback(invoke_without_command=True)
def test_callback(ctx: typer.Context) -> None:
    """Callback for test command group - shows interactive menu if no subcommand provided."""
    if ctx.invoked_subcommand is None:
        # No subcommand provided, show interactive menu
        show_group_interactive_menu("test", COMMAND_GROUPS["test"])


@test_app.command("sentry")
def test_sentry() -> None:
    """Throw an unhandled exception to test Sentry error reporting.

    This command intentionally raises an unhandled exception that should
    be caught and reported by Sentry if it's properly configured.

    Examples:
        python -m cli test sentry
    """
    console.print("[yellow]Throwing unhandled exception to test Sentry...[/yellow]")
    console.print("[red]This exception should be caught by Sentry if configured correctly.[/red]\n")

    try:
        import sentry_sdk

        # Capture exception with Sentry
        sentry_sdk.capture_exception(RuntimeError("Test exception for Sentry integration - this is intentional!"))

        # Flush events to ensure they are sent before CLI exits
        console.print("[blue]Flushing Sentry events...[/blue]")
        sentry_sdk.flush(timeout=5.0)

        console.print("[green]✓ Test exception sent to Sentry successfully![/green]")
        console.print("[dim]Check your Sentry dashboard at: https://sentry.io/[/dim]")
    except ImportError:
        console.print("[red]✗ Sentry SDK not installed![/red]")
        console.print("[dim]Install with: pip install sentry-sdk[fastapi][/dim]")
    except Exception as e:
        console.print(f"[red]✗ Failed to send test exception to Sentry: {e}[/red]")


@test_app.command("storage")
def test_storage(
    skip_cleanup: bool = typer.Option(False, "--skip-cleanup", help="Skip cleanup after test"),
) -> None:
    """Test storage adapter connectivity and operations.

    Performs a full test of the configured storage adapter:
    1. Uploads a test file
    2. Verifies file exists
    3. Downloads and verifies content
    4. Cleans up test file (unless --skip-cleanup)

    Examples:
        python -m cli test storage
        python -m cli test storage --skip-cleanup
    """
    asyncio.run(_test_storage_async(skip_cleanup))


async def _test_storage_async(skip_cleanup: bool) -> None:
    """Async implementation of storage test."""
    console.print("\n[bold cyan]Testing Storage Adapter[/bold cyan]")
    console.print("=" * 50)

    # Show config
    console.print(f"[dim]Storage Type:[/dim] {settings.storage.type}")
    if settings.storage.type == "s3":
        console.print(f"[dim]S3 Bucket:[/dim] {settings.storage.s3_bucket}")
        console.print(f"[dim]S3 Region:[/dim] {settings.storage.s3_region}")
        console.print(f"[dim]S3 Endpoint:[/dim] {settings.storage.s3_endpoint_url or 'Default (AWS)'}")
    console.print()

    try:
        # Initialize storage adapter
        console.print("[1/5] [cyan]Initializing storage adapter...[/cyan]")
        adapter = get_storage_adapter()
        console.print("    [green]✓ Storage adapter initialized[/green]")

        # Prepare test data
        test_file_name = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        test_path = f"cli-test/{test_file_name}"
        test_content = f"Storage test from CLI at {datetime.now().isoformat()}".encode()

        # Upload test file
        console.print(f"[2/5] [cyan]Uploading test file: {test_path}...[/cyan]")
        uploaded_path = await adapter.upload(
            file_content=test_content,
            destination_path=test_path,
            content_type="text/plain",
            metadata={"test": "true", "source": "cli"},
        )
        console.print(f"    [green]✓ File uploaded: {uploaded_path}[/green]")

        # Check if file exists
        console.print("[3/5] [cyan]Checking if file exists...[/cyan]")
        exists = await adapter.exists(test_path)
        if exists:
            console.print("    [green]✓ File exists[/green]")
        else:
            console.print("    [red]✗ File not found![/red]")
            raise Exception("Uploaded file not found")

        # Download and verify
        console.print("[4/5] [cyan]Downloading and verifying content...[/cyan]")
        downloaded_content = await adapter.download(test_path)
        if downloaded_content == test_content:
            console.print("    [green]✓ Content verified successfully[/green]")
        else:
            console.print("    [red]✗ Content mismatch![/red]")
            raise Exception("Downloaded content doesn't match uploaded content")

        # Get URL (if supported)
        try:
            url = await adapter.get_url(test_path)
            console.print(f"    [dim]File URL: {url[:80]}...[/dim]")
        except NotImplementedError:
            console.print("    [dim]URL generation not supported for this adapter[/dim]")

        # Cleanup
        if not skip_cleanup:
            console.print("[5/5] [cyan]Cleaning up test file...[/cyan]")
            deleted = await adapter.delete(test_path)
            if deleted:
                console.print("    [green]✓ Test file deleted[/green]")
            else:
                console.print("    [yellow]⚠ Failed to delete test file[/yellow]")
        else:
            console.print(f"[5/5] [yellow]Skipping cleanup (file kept): {test_path}[/yellow]")

        # Success summary
        console.print()
        console.print("[bold green]✓ All storage tests passed successfully![/bold green]")
        console.print()

    except ImportError as e:
        console.print()
        console.print("[bold red]✗ Storage adapter dependencies missing![/bold red]")
        console.print(f"[dim]Error: {e}[/dim]")
        if settings.storage.type == "s3":
            console.print()
            console.print("[yellow]To use S3 storage, install required dependencies:[/yellow]")
            console.print("[cyan]  pip install aioboto3[/cyan]")
        console.print()
        raise typer.Exit(1) from None

    except Exception as e:
        console.print()
        console.print("[bold red]✗ Storage test failed![/bold red]")
        console.print(f"[dim]Error: {e}[/dim]")
        console.print()

        # Provide helpful troubleshooting tips
        if settings.storage.type == "s3":
            console.print("[yellow]Troubleshooting tips:[/yellow]")
            console.print("  • Verify S3 credentials are correct")
            console.print("  • Check bucket exists and is accessible")
            console.print("  • Verify network connectivity to S3 endpoint")
            console.print("  • Check IAM permissions for the access key")

        console.print()
        raise typer.Exit(1) from None


@test_app.command("email")
def test_email(
    to: str = typer.Argument(..., help="Recipient email address"),
    template: str = typer.Option(
        "welcome",
        "--template",
        "-t",
        help="Email template to use (welcome, password_reset, etc.)",
    ),
) -> None:
    """Test email sending via configured SMTP adapter.

    Sends a test email to verify SMTP configuration is working correctly.
    You can specify different email templates to test various email types.

    Examples:
        python -m cli test email jan.madeyski@gmail.com
        python -m cli test email user@example.com --template password_reset
    """
    asyncio.run(_test_email_async(to, template))


async def _test_email_async(to: str, template: str) -> None:
    """Async implementation of email test."""
    console.print("\n[bold cyan]Testing Email Service[/bold cyan]")
    console.print("=" * 50)

    # Show config
    console.print(f"[dim]Email Enabled:[/dim] {settings.email.enabled}")
    console.print(f"[dim]Email Adapter:[/dim] {settings.email.adapter}")
    if settings.email.adapter == "smtp":
        console.print(f"[dim]SMTP Host:[/dim] {settings.email.smtp_host}")
        console.print(f"[dim]SMTP Port:[/dim] {settings.email.smtp_port}")
        console.print(f"[dim]SMTP User:[/dim] {settings.email.smtp_user}")
        console.print(f"[dim]SMTP From:[/dim] {settings.email.smtp_from}")
        console.print(f"[dim]SMTP TLS:[/dim] {settings.email.smtp_use_tls}")
    console.print(f"[dim]Template:[/dim] {template}")
    console.print(f"[dim]Recipient:[/dim] {to}")
    console.print()

    try:
        # Initialize email service
        console.print("[1/3] [cyan]Initializing email service...[/cyan]")
        email_service = get_email_service()
        console.print("    [green]✓ Email service initialized[/green]")

        # Prepare test data based on template
        console.print(f"[2/3] [cyan]Sending test email (template: {template})...[/cyan]")

        success = False
        if template == "welcome":
            success = await email_service.send_welcome_email(
                to=to,
                name="Test User",
            )
        elif template == "password_reset":
            success = await email_service.send_password_reset_email(
                to=to,
                name="Test User",
                reset_token="test-token-123",
            )
        elif template == "email_verification":
            success = await email_service.send_email_verification_email(
                to=to,
                name="Test User",
                verification_token="test-verification-token-123",
            )
        elif template == "password_changed":
            success = await email_service.send_password_changed_email(
                to=to,
                name="Test User",
                ip_address="127.0.0.1",
            )
        elif template == "account_deleted":
            success = await email_service.send_account_deleted_email(
                to=to,
                name="Test User",
            )
        else:
            console.print(f"    [red]✗ Unknown template: {template}[/red]")
            console.print("    [dim]Available templates: welcome, password_reset, email_verification, password_changed, account_deleted[/dim]")
            raise typer.Exit(1)

        # Check result
        console.print("[3/3] [cyan]Checking result...[/cyan]")
        if success:
            console.print("    [green]✓ Email sent successfully[/green]")
        else:
            console.print("    [red]✗ Failed to send email[/red]")
            raise Exception("Email sending failed")

        # Success summary
        console.print()
        console.print("[bold green]✓ Email test passed successfully![/bold green]")
        console.print(f"[dim]Check inbox at: {to}[/dim]")
        console.print()

    except ImportError as e:
        console.print()
        console.print("[bold red]✗ Email service dependencies missing![/bold red]")
        console.print(f"[dim]Error: {e}[/dim]")
        console.print()
        raise typer.Exit(1) from None

    except Exception as e:
        console.print()
        console.print("[bold red]✗ Email test failed![/bold red]")
        console.print(f"[dim]Error: {e}[/dim]")
        console.print()

        # Provide helpful troubleshooting tips
        if settings.email.adapter == "smtp":
            console.print("[yellow]Troubleshooting tips:[/yellow]")
            console.print("  • Verify SMTP host and port are correct")
            console.print("  • Check SMTP username and password")
            console.print("  • Verify SMTP server allows connections from your IP")
            console.print("  • Check if TLS/SSL settings are correct (use_tls)")
            console.print("  • For port 465: use SSL (automatic)")
            console.print("  • For port 587: use TLS with STARTTLS")
            console.print("  • Check firewall settings")

        console.print()
        raise typer.Exit(1) from None
