"""User management commands.

This module provides Django-like commands for creating, listing, and managing users.
"""

import asyncio
import sys
from typing import Any

import typer
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..main import COMMAND_GROUPS, show_group_interactive_menu
from ..utils import (
    format_2fa_status,
    format_email_verified,
    format_user_role,
    format_user_status,
    truncate_id,
    validate_email,
    validate_password_strength,
)

# Create users subcommand app
users_app = typer.Typer(
    name="users",
    help="User management commands",
    no_args_is_help=False,  # We handle no-args case ourselves for interactive mode
)


@users_app.callback(invoke_without_command=True)
def users_callback(ctx: typer.Context) -> None:
    """Callback for users command group - shows interactive menu if no subcommand provided."""
    if ctx.invoked_subcommand is None:
        # No subcommand provided, show interactive menu
        show_group_interactive_menu("users", COMMAND_GROUPS["users"])


@users_app.command("create")
def users_create(
    email: str | None = typer.Option(None, "--email", "-e", help="User email address"),
    name: str | None = typer.Option(None, "--name", "-n", help="User full name (blank to guess from email)"),
    password: str | None = typer.Option(
        None,
        "--password",
        help="User password (not recommended, will prompt if not provided)",
    ),
    role: str | None = typer.Option(
        None,
        "--role",
        "-r",
        help="User role: admin, owner, premium, or user",
    ),
    admin: bool = typer.Option(False, "--admin", "-a", help="Create as administrator"),
    owner: bool = typer.Option(False, "--owner", "-o", help="Create as owner"),
    premium: bool = typer.Option(False, "--premium", "-p", help="Create as premium user"),
    no_input: bool = typer.Option(False, "--no-input", help="Skip interactive prompts (requires all options)"),
) -> None:
    """Create a new user interactively with rich prompts and validation.

    Examples:
        # Interactive mode (recommended)
        python -m cli users create

        # Create admin user
        python -m cli users create --admin
        python -m cli users create --role admin

        # Create owner user
        python -m cli users create --owner

        # Create premium user
        python -m cli users create --premium

        # Non-interactive mode (for scripts)
        python -m cli users create --no-input \\
            --email admin@example.com \\
            --name "Admin User" \\
            --password "SecurePass123!" \\
            --role admin
    """
    asyncio.run(_users_create_async(email, name, password, role, admin, owner, premium, no_input))


async def _users_create_async(
    email: str | None,
    name: str | None,
    password: str | None,
    role: str | None,
    admin: bool,
    owner: bool,
    premium: bool,
    no_input: bool,
) -> None:
    """Async implementation of user creation."""
    from rich.console import Console

    console = Console()
    console.print("\n[bold cyan]Create New User[/bold cyan]\n")

    if not no_input and not sys.stdin.isatty():
        console.print("[red]Interactive mode requires a TTY.[/red]")
        console.print("Run with [cyan]-it[/cyan]: docker exec -it pulse-db-app python -m cli users create")
        console.print("Or use [cyan]--no-input[/cyan] with all options: " "--email ... --name ... --password ...")
        raise typer.Exit(1)

    try:
        is_admin, is_owner, is_premium = _resolve_role_flags(role, admin, owner, premium)
    except ValueError as e:
        console.print(f"\n[red]Error:[/red] {e}\n")
        raise typer.Exit(1) from None

    # Get user details interactively if not provided
    email_value = await _get_email(console, email, no_input)
    name_value = await _get_name(console, name, no_input, email_value)
    password_value = await _get_password(console, password, no_input)
    if not no_input and role is None:
        is_admin = await _get_admin_status(console, is_admin, no_input)

    # Show summary
    _show_user_summary(console, email_value, name_value, is_admin, is_owner, is_premium)

    # Confirm creation
    if not no_input:
        if not Confirm.ask("\nCreate this user?", default=True):
            console.print("[yellow]Cancelled[/yellow]")
            return

    # Create user with spinner
    try:
        with console.status("[bold green]Creating user...", spinner="dots"):
            user = await _create_user_in_db(email_value, name_value, password_value, is_admin, is_owner, is_premium)

        # Show success message
        console.print("\n[bold green]✓[/bold green] User created successfully!\n")

        # Show user info panel
        role_str = "Owner" if user.get("isOwner") else ("Administrator" if user.get("isAdmin") else ("Premium" if user.get("isPremium") else "User"))
        user_info = f"""[bold]Email:[/bold] {user['email']}
[bold]Name:[/bold] {user['name']}
[bold]Role:[/bold] {role_str}
[bold]Status:[/bold] {'Active' if user['isActive'] else 'Inactive'}
[bold]ID:[/bold] {user['id']}
[bold]Created:[/bold] {user['createdAt']}"""

        panel = Panel(user_info, title="[bold]User Details[/bold]", border_style="green")
        console.print(panel)
        console.print()

    except Exception as e:
        console.print(f"\n[red]Error creating user:[/red] {e}\n")
        raise typer.Exit(1) from None


async def _get_email(console: Any, email: str | None, no_input: bool) -> str:
    """Get user email with validation."""
    if email and validate_email(email):
        return email

    if no_input:
        raise ValueError("Email is required when --no-input is used")

    while True:
        email_input = Prompt.ask("[cyan]Email address[/cyan]", default=email or "")

        if not email_input:
            console.print("[red]Email is required[/red]")
            continue

        if not validate_email(email_input):
            console.print("[red]Invalid email format[/red]")
            continue

        return email_input


async def _get_name(console: Any, name: str | None, no_input: bool, email: str | None = None) -> str:
    """Get user name (can be blank to guess from email)."""
    if name:
        return name

    if no_input:
        raise ValueError("Name is required when --no-input is used")

    while True:
        name_input = Prompt.ask("[cyan]Full name (blank to guess from email)[/cyan]", default=name or "")

        if not name_input:
            if email:
                name_from_email = email.split("@")[0]
                guessed_name = name_from_email.replace(".", " ").replace("_", " ").title()
                console.print(f"[dim]Using guessed name: {guessed_name}[/dim]")
                return guessed_name
            console.print("[red]Cannot guess name without email[/red]")
            continue

        if len(name_input) < 2:
            console.print("[red]Name must be at least 2 characters[/red]")
            continue

        return name_input


def _resolve_role_flags(
    role: str | None,
    admin: bool,
    owner: bool,
    premium: bool,
) -> tuple[bool, bool, bool]:
    """Resolve role from --role flag or legacy --admin/--owner/--premium flags."""
    valid_roles = {"admin", "owner", "premium", "user"}

    if role is not None:
        role_lower = role.lower().strip()
        if role_lower not in valid_roles:
            raise ValueError(f"Invalid role: {role}. Valid roles are: {', '.join(sorted(valid_roles))}")
        return (
            role_lower == "admin",
            role_lower == "owner",
            role_lower == "premium",
        )

    return admin, owner, premium


async def _get_password(console: Any, password: str | None, no_input: bool) -> str:
    """Get user password with validation."""
    if password:
        # Validate provided password
        is_valid, error = validate_password_strength(password)
        if not is_valid:
            raise ValueError(f"Invalid password: {error}")
        return password

    if no_input:
        raise ValueError("Password is required when --no-input is used")

    while True:
        password_input = Prompt.ask("[cyan]Password[/cyan]", password=True)

        if not password_input:
            console.print("[red]Password is required[/red]")
            continue

        # Validate password strength
        is_valid, error = validate_password_strength(password_input)
        if not is_valid:
            console.print(f"[red]{error}[/red]")
            continue

        # Confirm password
        password_confirm = Prompt.ask("[cyan]Password (confirm)[/cyan]", password=True)

        if password_input != password_confirm:
            console.print("[red]Passwords do not match[/red]")
            continue

        return password_input


async def _get_admin_status(console: Any, admin: bool, no_input: bool) -> bool:
    """Get admin status."""
    if no_input:
        return admin

    return Confirm.ask("[cyan]Create as administrator?[/cyan]", default=admin)


def _show_user_summary(
    console: Any,
    email: str,
    name: str,
    is_admin: bool,
    is_owner: bool = False,
    is_premium: bool = False,
) -> None:
    """Show user creation summary."""
    role_str = "Owner" if is_owner else ("Administrator" if is_admin else ("Premium" if is_premium else "User"))
    summary = f"""[bold]Email:[/bold] {email}
[bold]Name:[/bold] {name}
[bold]Role:[/bold] {role_str}"""

    panel = Panel(summary, title="[bold]User Summary[/bold]", border_style="cyan")
    console.print(panel)


async def _create_user_in_db(
    email: str,
    name: str,
    password: str,
    is_admin: bool,
    is_owner: bool = False,
    is_premium: bool = False,
) -> dict[str, Any]:
    """Create user in database.

    Args:
        email: User email
        name: User name
        password: User password (will be hashed)
        is_admin: Whether user is admin
        is_owner: Whether user is owner
        is_premium: Whether user is premium

    Returns:
        dict: Created user data
    """
    from datetime import UTC, datetime

    from app.core.database import get_db
    from app.modules.auth.repositories import UserRepository

    # Get database session
    async for db in get_db():
        repo = UserRepository(db)

        try:
            # Create user (create_user only supports is_admin, so we'll update flags after)
            user = await repo.create_user(email=email, password=password, full_name=name, is_admin=is_admin)

            # Update role flags if needed
            if is_owner or is_premium:
                user.isOwner = is_owner
                user.isPremium = is_premium
                user = await repo.update_user(user)

            user.isEmailVerified = True
            user.emailVerifiedAt = datetime.now(UTC)
            user = await repo.update_user(user)

            # Convert to dict for display
            return {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "isActive": user.isActive,
                "isAdmin": user.isAdmin,
                "isOwner": user.isOwner,
                "isPremium": user.isPremium,
                "createdAt": user.createdAt,
            }

        except Exception as e:
            # Re-raise with more context
            raise Exception(f"Failed to create user: {e}") from e
        break  # Ensure we only process first iteration

    # This should never be reached, but mypy needs it
    raise RuntimeError("Database session not available")


@users_app.command("list")
def users_list(
    admins_only: bool = typer.Option(False, "--admins", help="Show only administrators"),
    users_only: bool = typer.Option(False, "--users", help="Show only regular users"),
    active_only: bool = typer.Option(False, "--active", help="Show only active users"),
    inactive_only: bool = typer.Option(False, "--inactive", help="Show only inactive users"),
    limit: int | None = typer.Option(None, "--limit", "-l", help="Maximum number of users to show"),
    detailed: bool | None = typer.Option(
        None,
        "--detailed/--no-detailed",
        help="Show detailed information (email verified, 2FA status)",
    ),
    wide: bool | None = typer.Option(
        None,
        "--wide/--no-wide",
        "-w",
        help="Show full IDs and emails without truncation",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all users in a beautiful table with filters.

    Examples:
        # List all users
        python -m cli users list

        # List only administrators
        python -m cli users list --admins

        # List first 10 active users
        python -m cli users list --active --limit 10

        # Show detailed information
        python -m cli users list --detailed

        # Output as JSON
        python -m cli users list --json
    """
    if not json_output:
        if detailed is None:
            detailed = typer.confirm("Show detailed info (email verified, 2FA)?", default=False)
        if wide is None:
            wide = typer.confirm("Show full IDs and emails?", default=False)
    else:
        detailed = detailed or False
        wide = wide or False
    asyncio.run(
        _users_list_async(
            admins_only,
            users_only,
            active_only,
            inactive_only,
            limit,
            detailed,
            wide,
            json_output,
        )
    )


async def _users_list_async(
    admins_only: bool,
    users_only: bool,
    active_only: bool,
    inactive_only: bool,
    limit: int | None,
    detailed: bool,
    wide: bool,
    json_output: bool,
) -> None:
    """Async implementation of user listing."""
    import json as json_lib

    from rich.console import Console

    console = Console()

    try:
        # Get users with spinner
        with console.status("[bold green]Loading users...", spinner="dots"):
            users = await _get_users_from_db(detailed=detailed)

        if not users:
            console.print("\n[yellow]No users found[/yellow]\n")
            return

        # Apply filters
        if admins_only:
            users = [u for u in users if u["isAdmin"]]
        elif users_only:
            users = [u for u in users if not u["isAdmin"]]

        if active_only:
            users = [u for u in users if u["isActive"]]
        elif inactive_only:
            users = [u for u in users if not u["isActive"]]

        # Apply limit
        if limit:
            users = users[:limit]

        if not users:
            console.print("\n[yellow]No users match the filters[/yellow]\n")
            return

        # Output as JSON if requested
        if json_output:
            # Convert datetime objects to ISO format strings for JSON
            json_users = []
            for user in users:
                json_user = {
                    "id": user["id"],
                    "email": user["email"],
                    "name": user["name"],
                    "isAdmin": user["isAdmin"],
                    "isActive": user["isActive"],
                    "createdAt": user["createdAt"].isoformat(),
                }
                if detailed:
                    json_user["isEmailVerified"] = user.get("isEmailVerified", False)
                    json_user["has2FA"] = user.get("has2FA", False)
                json_users.append(json_user)
            print(json_lib.dumps(json_users, indent=2))
            return

        # Create table
        table = Table(
            title=(f"[bold cyan]Users[/bold cyan] " f"[dim]({len(users)} total)[/dim]"),
            show_header=True,
            header_style="bold cyan",
        )

        table.add_column("ID", style="dim", no_wrap=True)
        if wide:
            table.add_column("Email", style="cyan", overflow="fold")
        else:
            table.add_column("Email", style="cyan", overflow="ellipsis", max_width=40)
        table.add_column("Name", style="white")
        table.add_column("Role", justify="center")
        table.add_column("Status", justify="center")
        if detailed:
            table.add_column("Email Verified", justify="center")
            table.add_column("2FA", justify="center")
        table.add_column("Created", style="dim")

        for user in users:
            # Format date
            created = user["createdAt"].strftime("%Y-%m-%d %H:%M")

            row = [
                str(user["id"]) if wide else truncate_id(user["id"]),
                user["email"],
                user["name"],
                format_user_role(
                    is_admin=user.get("isAdmin", False),
                    is_owner=user.get("isOwner", False),
                    is_premium=user.get("isPremium", False),
                ),
                format_user_status(user["isActive"]),
            ]
            if detailed:
                row.append(format_email_verified(user.get("isEmailVerified", False)))
                row.append(format_2fa_status(user.get("has2FA", False)))
            row.append(created)

            table.add_row(*row)

        console.print()
        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"\n[red]Error listing users:[/red] {e}\n")
        raise typer.Exit(1) from None


async def _get_users_from_db(detailed: bool = False) -> list[dict[str, Any]]:
    """Get users from database.

    Args:
        detailed: If True, include email verification and 2FA status

    Returns:
        list[dict]: List of user data
    """
    from sqlalchemy import select

    from app.core.database import get_db
    from app.modules.auth.db_models import UserDB
    from app.modules.two_factor.db_models import PasskeyDB, TotpConfigDB

    async for db in get_db():
        # Query database directly to avoid Pydantic email validation errors
        # This allows us to handle users with invalid emails (e.g., soft-deleted users)
        stmt = select(UserDB)
        result = await db.execute(stmt)
        users_db = result.scalars().all()

        # Convert to dict for display
        result_list = []
        for user_db in users_db:
            # Build user dict directly from database model
            # This avoids Pydantic validation which would fail on invalid emails
            user_dict = {
                "id": user_db.id,
                "email": user_db.email,  # May contain invalid emails (e.g., deleted_xxx@deleted.local)
                "name": user_db.name,
                "isActive": user_db.is_active,
                "isAdmin": user_db.is_admin,
                "isOwner": user_db.is_owner,
                "isPremium": user_db.is_premium,
                "createdAt": user_db.created_at,
            }

            if detailed:
                # Get email verification status
                user_dict["isEmailVerified"] = user_db.is_email_verified

                # Check 2FA status (TOTP or Passkey)
                has_2fa = False

                # Check TOTP
                totp_stmt = select(TotpConfigDB).where(
                    TotpConfigDB.user_id == user_db.id,
                    TotpConfigDB.is_enabled.is_(True),
                )
                totp_result = await db.execute(totp_stmt)
                totp_config = totp_result.scalar_one_or_none()
                if totp_config:
                    has_2fa = True

                # Check Passkeys if TOTP not enabled
                if not has_2fa:
                    passkey_stmt = select(PasskeyDB).where(
                        PasskeyDB.user_id == user_db.id,
                        PasskeyDB.is_enabled.is_(True),
                    )
                    passkey_result = await db.execute(passkey_stmt)
                    passkeys = passkey_result.scalars().all()
                    if passkeys:
                        has_2fa = True

                user_dict["has2FA"] = has_2fa

            result_list.append(user_dict)

        return result_list

    return []


@users_app.command("delete")
def users_delete(
    identifier: str | None = typer.Argument(None, help="User email or ID to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    hard: bool = typer.Option(
        False,
        "--hard",
        help="Permanently remove user from database (default: soft delete)",
    ),
) -> None:
    """Delete a user by email or ID with confirmation.

    By default performs a soft delete (deactivates account, anonymizes email).
    Use --hard to permanently remove the user from the database.

    Examples:
        # Interactive mode (will prompt for email/ID)
        python -m cli users delete

        # Soft delete by email
        python -m cli users delete user@example.com

        # Soft delete by ID without confirmation
        python -m cli users delete 01HQX... --yes

        # Permanently remove user
        python -m cli users delete user@example.com --hard --yes
    """
    asyncio.run(_users_delete_async(identifier, yes, hard))


async def _users_delete_async(identifier: str | None, yes: bool, hard: bool) -> None:
    """Async implementation of user deletion."""
    from rich.console import Console

    console = Console()

    try:
        # Get identifier if not provided
        if not identifier:
            identifier = Prompt.ask("[cyan]Enter user email or ID[/cyan]")

        # Find user
        with console.status("[bold green]Finding user...", spinner="dots"):
            user = await _find_user(identifier)

        if not user:
            console.print(f"\n[red]User not found:[/red] {identifier}\n")
            return

        # Show user info
        console.print("\n[bold yellow]User to delete:[/bold yellow]\n")

        user_info = f"""[bold]ID:[/bold] {user['id']}
[bold]Email:[/bold] {user['email']}
[bold]Name:[/bold] {user['name']}
[bold]Role:[/bold] {'Administrator' if user['isAdmin'] else 'User'}
[bold]Created:[/bold] {user['createdAt']}"""

        panel = Panel(user_info, border_style="yellow")
        console.print(panel)

        # Confirm deletion
        if not yes:
            if hard:
                console.print("\n[bold red]Warning:[/bold red] Hard delete permanently removes " "the user from the database. This cannot be undone!\n")
            else:
                console.print("\n[bold yellow]Note:[/bold yellow] Soft delete deactivates the " "account and anonymizes email (the email can be reused).\n")

            if not Confirm.ask("Are you sure you want to delete this user?", default=False):
                console.print("[yellow]Cancelled[/yellow]")
                return

        # Delete user
        with console.status("[bold red]Deleting user...", spinner="dots"):
            await _delete_user_from_db(user["id"], hard=hard)

        if hard:
            console.print("\n[bold green]✓[/bold green] User permanently deleted\n")
        else:
            console.print("\n[bold green]✓[/bold green] User soft-deleted successfully\n")

    except Exception as e:
        console.print(f"\n[red]Error deleting user:[/red] {e}\n")
        raise typer.Exit(1) from None


async def _find_user(identifier: str) -> dict[str, Any] | None:
    """Find user by email or ID.

    Args:
        identifier: User email or ID

    Returns:
        dict | None: User data if found, None otherwise
    """
    from app.core.database import get_db
    from app.modules.auth.repositories import UserRepository

    async for db in get_db():
        repo = UserRepository(db)

        # Try to find by email first
        if "@" in identifier:
            user = await repo.get_user_by_email(identifier)
        else:
            # Try to find by ID
            user = await repo.get_user_by_id(identifier)

        if user:
            return {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "isActive": user.isActive,
                "isAdmin": user.isAdmin,
                "isOwner": user.isOwner,
                "isPremium": user.isPremium,
                "isEmailVerified": user.isEmailVerified,
                "emailVerifiedAt": user.emailVerifiedAt,
                "createdAt": user.createdAt,
            }

    return None


async def _delete_user_from_db(user_id: str, *, hard: bool = False) -> None:
    """Delete user from database.

    Args:
        user_id: User ID to delete
        hard: If True, permanently remove user; otherwise soft-delete via repository
    """
    from app.core.database import get_db
    from app.modules.auth.repositories import UserRepository

    async for db in get_db():
        repo = UserRepository(db)
        success = await repo.delete_user(user_id, soft_delete=not hard)
        if not success:
            raise ValueError(f"User with id {user_id} not found")
        break


@users_app.command("change-password")
def users_change_password(
    identifier: str | None = typer.Argument(None, help="User email or ID whose password to change"),
    password: str | None = typer.Option(
        None,
        "--password",
        help="New password (not recommended, will prompt if not provided)",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Change a user's password by email or ID (admin override, no current password).

    Examples:
        # Interactive mode (will prompt for email/ID and new password)
        python -m cli users change-password

        # Change password by email
        python -m cli users change-password user@example.com

        # Non-interactive (for scripts)
        python -m cli users change-password user@example.com \\
            --password "SecurePass123!" --yes
    """
    asyncio.run(_users_change_password_async(identifier, password, yes))


async def _users_change_password_async(identifier: str | None, password: str | None, yes: bool) -> None:
    """Async implementation of password change."""
    from rich.console import Console

    console = Console()

    try:
        if not identifier:
            identifier = Prompt.ask("[cyan]Enter user email or ID[/cyan]")

        with console.status("[bold green]Finding user...", spinner="dots"):
            user = await _find_user(identifier)

        if not user:
            console.print(f"\n[red]User not found:[/red] {identifier}\n")
            return

        console.print("\n[bold cyan]User:[/bold cyan]\n")

        user_info = f"""[bold]ID:[/bold] {user['id']}
[bold]Email:[/bold] {user['email']}
[bold]Name:[/bold] {user['name']}
[bold]Role:[/bold] {'Administrator' if user['isAdmin'] else 'User'}"""

        panel = Panel(user_info, border_style="cyan")
        console.print(panel)

        password_value = await _get_password(console, password, no_input=False)

        if not yes:
            if not Confirm.ask(
                "\nAre you sure you want to change this user's password?",
                default=False,
            ):
                console.print("[yellow]Cancelled[/yellow]")
                return

        with console.status("[bold green]Updating password...", spinner="dots"):
            await _change_password_in_db(user["id"], password_value)

        console.print("\n[bold green]✓[/bold green] Password changed successfully\n")
        console.print("[dim]Existing sessions have been invalidated (token version bumped).[/dim]\n")

    except Exception as e:
        console.print(f"\n[red]Error changing password:[/red] {e}\n")
        raise typer.Exit(1) from None


async def _change_password_in_db(user_id: str, new_password: str) -> None:
    """Set a new password for a user and invalidate existing tokens.

    Args:
        user_id: User ID
        new_password: New plaintext password (will be hashed)
    """
    from app.core.database import get_db
    from app.modules.auth.repositories import UserRepository

    async for db in get_db():
        repo = UserRepository(db)
        user = await repo.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        user.set_password(new_password)
        user.clear_reset_token()
        await repo.update_user(user)
        await repo.increment_token_version(user_id)
        break


@users_app.command("toggle-admin")
def users_toggle_admin(
    identifier: str | None = typer.Argument(None, help="User email or ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Toggle admin flag for a user by email or ID.

    Examples:
        # Interactive mode (will prompt for email/ID)
        python -m cli users toggle-admin

        # Toggle admin by email
        python -m cli users toggle-admin user@example.com

        # Toggle admin by ID without confirmation
        python -m cli users toggle-admin 01HQX... --yes
    """
    asyncio.run(_users_toggle_admin_async(identifier, yes))


async def _users_toggle_admin_async(identifier: str | None, yes: bool) -> None:
    """Async implementation of toggle admin."""
    from rich.console import Console

    console = Console()

    try:
        # Get identifier if not provided
        if not identifier:
            identifier = Prompt.ask("[cyan]Enter user email or ID[/cyan]")

        # Find user
        with console.status("[bold green]Finding user...", spinner="dots"):
            user = await _find_user(identifier)

        if not user:
            console.print(f"\n[red]User not found:[/red] {identifier}\n")
            return

        # Determine new admin status
        new_admin_status = not user["isAdmin"]
        action = "promote to administrator" if new_admin_status else "demote to regular user"

        # Show user info
        console.print("\n[bold cyan]User to modify:[/bold cyan]\n")

        user_info = f"""[bold]ID:[/bold] {user['id']}
[bold]Email:[/bold] {user['email']}
[bold]Name:[/bold] {user['name']}
[bold]Current Role:[/bold] {'Administrator' if user['isAdmin'] else 'User'}
[bold]New Role:[/bold] {'Administrator' if new_admin_status else 'User'}"""

        panel = Panel(user_info, border_style="cyan")
        console.print(panel)

        # Confirm change
        if not yes:
            console.print()
            if not Confirm.ask(f"Are you sure you want to {action}?", default=True):
                console.print("[yellow]Cancelled[/yellow]")
                return

        # Toggle admin status
        with console.status("[bold green]Updating user...", spinner="dots"):
            await _toggle_admin_in_db(user["id"], new_admin_status)

        console.print(f"\n[bold green]✓[/bold green] User {'promoted to administrator' if new_admin_status else 'demoted to regular user'} successfully\n")

    except Exception as e:
        console.print(f"\n[red]Error toggling admin status:[/red] {e}\n")
        raise typer.Exit(1) from None


async def _toggle_admin_in_db(user_id: str, is_admin: bool) -> None:
    """Toggle admin status in database.

    Args:
        user_id: User ID to update
        is_admin: New admin status
    """
    from app.core.database import get_db
    from app.modules.auth.repositories import UserRepository

    async for db in get_db():
        repo = UserRepository(db)

        # Get user
        user = await repo.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        # Update admin status
        user.isAdmin = is_admin
        await repo.update_user(user)
        break  # Ensure we only process first iteration


@users_app.command("toggle-owner")
def users_toggle_owner(
    identifier: str | None = typer.Argument(None, help="User email or ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Toggle owner flag for a user by email or ID.

    Examples:
        # Interactive mode (will prompt for email/ID)
        python -m cli users toggle-owner

        # Toggle owner by email
        python -m cli users toggle-owner user@example.com

        # Toggle owner by ID without confirmation
        python -m cli users toggle-owner 01HQX... --yes
    """
    asyncio.run(_users_toggle_owner_async(identifier, yes))


async def _users_toggle_owner_async(identifier: str | None, yes: bool) -> None:
    """Async implementation of toggle owner."""
    from rich.console import Console

    console = Console()

    try:
        # Get identifier if not provided
        if not identifier:
            identifier = Prompt.ask("[cyan]Enter user email or ID[/cyan]")

        # Find user
        with console.status("[bold green]Finding user...", spinner="dots"):
            user = await _find_user(identifier)

        if not user:
            console.print(f"\n[red]User not found:[/red] {identifier}\n")
            return

        # Determine new owner status
        new_owner_status = not user.get("isOwner", False)
        action = "promote to owner" if new_owner_status else "demote from owner"

        # Show user info
        console.print("\n[bold cyan]User to modify:[/bold cyan]\n")

        current_role = "Owner" if user.get("isOwner") else ("Administrator" if user.get("isAdmin") else ("Premium" if user.get("isPremium") else "User"))
        new_role = "Owner" if new_owner_status else ("Administrator" if user.get("isAdmin") else ("Premium" if user.get("isPremium") else "User"))

        user_info = f"""[bold]ID:[/bold] {user['id']}
[bold]Email:[/bold] {user['email']}
[bold]Name:[/bold] {user['name']}
[bold]Current Role:[/bold] {current_role}
[bold]New Role:[/bold] {new_role}"""

        panel = Panel(user_info, border_style="cyan")
        console.print(panel)

        # Confirm change
        if not yes:
            console.print()
            if not Confirm.ask(f"Are you sure you want to {action}?", default=True):
                console.print("[yellow]Cancelled[/yellow]")
                return

        # Toggle owner status
        with console.status("[bold green]Updating user...", spinner="dots"):
            await _toggle_owner_in_db(user["id"], new_owner_status)
            await _toggle_admin_in_db(user["id"], new_owner_status)

        console.print(f"\n[bold green]✓[/bold green] User {'promoted to owner' if new_owner_status else 'demoted from owner'} successfully\n")

    except Exception as e:
        console.print(f"\n[red]Error toggling owner status:[/red] {e}\n")
        raise typer.Exit(1) from None


async def _toggle_owner_in_db(user_id: str, is_owner: bool) -> None:
    """Toggle owner status in database.

    Args:
        user_id: User ID to update
        is_owner: New owner status
    """
    from app.core.database import get_db
    from app.modules.auth.repositories import UserRepository

    async for db in get_db():
        repo = UserRepository(db)

        # Get user
        user = await repo.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        # Update owner status
        user.isOwner = is_owner
        await repo.update_user(user)
        break  # Ensure we only process first iteration


@users_app.command("set-role")
def users_set_role(
    identifier: str | None = typer.Argument(None, help="User email or ID"),
    role: str | None = typer.Option(
        None,
        "--role",
        "-r",
        help="Role to set: user, premium, admin, or owner",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Set user role (user, premium, admin, or owner).

    Examples:
        # Interactive mode (will prompt for email/ID and role)
        python -m cli users set-role

        # Set role by email
        python -m cli users set-role user@example.com --role admin

        # Set role by ID without confirmation
        python -m cli users set-role 01HQX... --role user --yes
    """
    asyncio.run(_users_set_role_async(identifier, role, yes))


async def _users_set_role_async(identifier: str | None, role: str | None, yes: bool) -> None:
    """Async implementation of set role."""
    from rich.console import Console

    console = Console()

    # Valid roles
    VALID_ROLES = ["user", "premium", "admin", "owner"]
    ROLE_DISPLAY_NAMES = {
        "user": "[dim]User[/dim]",
        "premium": "[cyan]Premium[/cyan]",
        "admin": "[yellow]Admin[/yellow]",
        "owner": "[bold magenta]Owner[/bold magenta]",
    }

    try:
        # Get identifier if not provided
        if not identifier:
            identifier = Prompt.ask("[cyan]Enter user email or ID[/cyan]")

        # Find user
        with console.status("[bold green]Finding user...", spinner="dots"):
            user = await _find_user(identifier)

        if not user:
            console.print(f"\n[red]User not found:[/red] {identifier}\n")
            return

        # Get role if not provided
        if not role:
            console.print("\n[bold cyan]Available roles:[/bold cyan]\n")
            for i, role_option in enumerate(VALID_ROLES, 1):
                console.print(f"  {i}. {ROLE_DISPLAY_NAMES[role_option]}")
            console.print()

            while True:
                role_input = (
                    Prompt.ask(
                        "[cyan]Select role[/cyan] (1-4 or name)",
                        default="",
                    )
                    .strip()
                    .lower()
                )

                # Try to parse as number
                if role_input.isdigit():
                    role_num = int(role_input)
                    if 1 <= role_num <= len(VALID_ROLES):
                        role = VALID_ROLES[role_num - 1]
                        break
                    else:
                        console.print(f"[red]Invalid number. Please enter 1-{len(VALID_ROLES)}[/red]")
                        continue

                # Try to parse as role name
                if role_input in VALID_ROLES:
                    role = role_input
                    break

                console.print(f"[red]Invalid role. Please enter 1-{len(VALID_ROLES)} or one of: {', '.join(VALID_ROLES)}[/red]")
        else:
            # Validate provided role
            role = role.lower().strip()
            if role not in VALID_ROLES:
                console.print(f"\n[red]Invalid role:[/red] {role}\n")
                console.print(f"[yellow]Valid roles are:[/yellow] {', '.join(VALID_ROLES)}\n")
                raise typer.Exit(1)

        # Determine current and new role display
        current_role_display = "Owner" if user.get("isOwner") else ("Administrator" if user.get("isAdmin") else ("Premium" if user.get("isPremium") else "User"))

        new_role_display = role.capitalize()

        # Determine flags for new role
        is_admin = role == "admin"
        is_owner = role == "owner"
        is_premium = role == "premium"

        # Show user info
        console.print("\n[bold cyan]User to modify:[/bold cyan]\n")

        user_info = f"""[bold]ID:[/bold] {user['id']}
[bold]Email:[/bold] {user['email']}
[bold]Name:[/bold] {user['name']}
[bold]Current Role:[/bold] {current_role_display}
[bold]New Role:[/bold] {new_role_display}"""

        panel = Panel(user_info, border_style="cyan")
        console.print(panel)

        # Confirm change
        if not yes:
            console.print()
            if not Confirm.ask(
                f"Are you sure you want to set role to {new_role_display}?",
                default=True,
            ):
                console.print("[yellow]Cancelled[/yellow]")
                return

        # Update role
        with console.status("[bold green]Updating user role...", spinner="dots"):
            await _set_role_in_db(user["id"], is_admin, is_owner, is_premium)

        console.print(f"\n[bold green]✓[/bold green] User role set to {new_role_display} successfully\n")

    except Exception as e:
        console.print(f"\n[red]Error setting user role:[/red] {e}\n")
        raise typer.Exit(1) from None


async def _set_role_in_db(user_id: str, is_admin: bool, is_owner: bool, is_premium: bool) -> None:
    """Set user role in database.

    Args:
        user_id: User ID to update
        is_admin: Whether user is admin
        is_owner: Whether user is owner
        is_premium: Whether user is premium
    """
    from app.core.database import get_db
    from app.modules.auth.repositories import UserRepository

    async for db in get_db():
        repo = UserRepository(db)

        # Get user
        user = await repo.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        # Update role flags
        user.isAdmin = is_admin
        user.isOwner = is_owner
        user.isPremium = is_premium

        await repo.update_user(user)
        break  # Ensure we only process first iteration


@users_app.command("verify-email")
def users_verify_email(
    identifier: str | None = typer.Argument(None, help="User email or ID"),
    show_link: bool = typer.Option(
        False,
        "--show-link",
        "-l",
        help="Show email verification link for the user",
    ),
    confirm_email: bool = typer.Option(
        False,
        "--confirm",
        "-c",
        help="Mark email as verified without using a link",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
) -> None:
    """Manage email verification for a user.

    Provides two options:
    - Show verification link (for manual sending/debugging)
    - Mark email as verified directly (without token)

    Examples:
        # Interactive mode (choose between link or direct verification)
        python -m cli users verify-email

        # Show verification link for user
        python -m cli users verify-email user@example.com --show-link

        # Mark email as verified (non-interactive)
        python -m cli users verify-email user@example.com --confirm --yes
    """
    asyncio.run(_users_verify_email_async(identifier, show_link, confirm_email, yes))


async def _users_verify_email_async(
    identifier: str | None,
    show_link: bool,
    confirm_email: bool,
    yes: bool,
) -> None:
    """Async implementation of email verification management."""
    from rich.console import Console

    console = Console()

    # Validate options
    if show_link and confirm_email:
        console.print("\n[red]You cannot use --show-link and --confirm together. Choose one option.[/red]\n")
        raise typer.Exit(1)

    try:
        # Get identifier if not provided
        if not identifier:
            identifier = Prompt.ask("[cyan]Enter user email or ID[/cyan]")

        # Find user
        with console.status("[bold green]Finding user...", spinner="dots"):
            user = await _find_user(identifier)

        if not user:
            console.print(f"\n[red]User not found:[/red] {identifier}\n")
            return

        # Show user info
        console.print("\n[bold cyan]User:[/bold cyan]\n")

        email_verified_str = "Yes" if user.get("isEmailVerified") else "No"

        user_info = f"""[bold]ID:[/bold] {user['id']}
[bold]Email:[/bold] {user['email']}
[bold]Name:[/bold] {user['name']}
[bold]Role:[/bold] {'Owner' if user.get('isOwner') else ('Administrator' if user.get('isAdmin') else ('Premium' if user.get('isPremium') else 'User'))}
[bold]Active:[/bold] {'Yes' if user['isActive'] else 'No'}
[bold]Email verified:[/bold] {email_verified_str}"""

        panel = Panel(user_info, border_style="cyan")
        console.print(panel)

        # Determine action (interactive if neither flag provided)
        action: str | None = None
        if show_link:
            action = "show_link"
        elif confirm_email:
            action = "confirm"
        else:
            console.print("\n[bold cyan]Email verification options:[/bold cyan]\n")
            console.print("  1. Show verification link")
            console.print("  2. Mark email as verified (without link)")
            console.print()

            while True:
                choice = Prompt.ask(
                    "[cyan]Select option[/cyan] (1-2)",
                    default="1",
                ).strip()

                if choice == "1":
                    action = "show_link"
                    break
                if choice == "2":
                    action = "confirm"
                    break

                console.print("[red]Invalid choice. Please enter 1 or 2.[/red]")

        # Execute selected action
        if action == "show_link":
            with console.status("[bold green]Generating verification link...", spinner="dots"):
                link, meta = await _generate_email_verification_link(user["id"])

            console.print("\n[bold green]✓[/bold green] Verification link generated successfully\n")

            link_info = f"""[bold]Verification link:[/bold]
{link}

[bold]Token:[/bold] {meta['token']}
[bold]Expires in:[/bold] {meta['expires_hours']} hours"""

            link_panel = Panel(
                link_info,
                title="[bold]Email Verification Link[/bold]",
                border_style="green",
            )
            console.print(link_panel)
            console.print()

        elif action == "confirm":
            if user.get("isEmailVerified"):
                console.print("\n[yellow]User email is already verified.[/yellow]\n")
                if not yes:
                    if not Confirm.ask("Mark as verified again anyway?", default=False):
                        console.print("[yellow]Cancelled[/yellow]")
                        return
            else:
                if not yes:
                    console.print()
                    if not Confirm.ask("Mark this email as verified?", default=True):
                        console.print("[yellow]Cancelled[/yellow]")
                        return

            with console.status("[bold green]Marking email as verified...", spinner="dots"):
                updated_user = await _mark_email_verified_in_db(user["id"])

            console.print("\n[bold green]✓[/bold green] Email marked as verified successfully\n")

            updated_info = f"""[bold]ID:[/bold] {updated_user.id}
[bold]Email:[/bold] {updated_user.email}
[bold]Name:[/bold] {updated_user.name}
[bold]Email verified:[/bold] {'Yes' if updated_user.isEmailVerified else 'No'}
[bold]Verified at:[/bold] {updated_user.emailVerifiedAt}"""

            updated_panel = Panel(updated_info, title="[bold]Updated User[/bold]", border_style="green")
            console.print(updated_panel)
            console.print()

    except Exception as e:
        console.print(f"\n[red]Error managing email verification:[/red] {e}\n")
        raise typer.Exit(1) from None


async def _generate_email_verification_link(user_id: str) -> tuple[str, dict[str, Any]]:
    """Generate and store email verification token, return verification link and metadata."""
    from datetime import UTC, datetime

    from app.core.config import settings
    from app.core.database import get_db
    from app.modules.auth.auth_utils import create_email_verification_token
    from app.modules.auth.repositories import UserRepository

    async for db in get_db():
        repo = UserRepository(db)

        user = await repo.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        # Generate new token
        token = create_email_verification_token({"sub": user.id, "email": user.email})

        # Store token metadata
        await repo.store_email_verification_token(user.id, token, datetime.now(UTC))

        # Build verification link (same as in email service)
        link = f"{settings.frontend_url}/auth/verify-email?token={token}"

        meta: dict[str, Any] = {
            "token": token,
            "expires_hours": settings.security.email_verification_token_expires_hours,
        }

        return link, meta

    # This should never be reached
    raise RuntimeError("Database session not available")


async def _mark_email_verified_in_db(user_id: str) -> Any:
    """Mark user email as verified directly in database."""
    from datetime import UTC, datetime

    from app.core.database import get_db
    from app.modules.auth.repositories import UserRepository

    async for db in get_db():
        repo = UserRepository(db)

        user = await repo.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        user.mark_email_verified(datetime.now(UTC))
        return await repo.update_user(user)

    # This should never be reached
    raise RuntimeError("Database session not available")
