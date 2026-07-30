"""Main CLI application.

This module configures the main Typer application and registers all command groups.
"""

import typer
from rich.console import Console

# Initialize Typer app
app = typer.Typer(
    name="cli",
    help="Management CLI for FastAPI project - Django-inspired commands",
    add_completion=True,
)

# Initialize Rich console (shared across commands)
console = Console()


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
