"""CLI package for PulseDB management commands."""

from .commands import db_app, monitoring_app, test_app, users_app
from .main import app, main

app.add_typer(db_app, name="db")
app.add_typer(users_app, name="users")
app.add_typer(test_app, name="test")
app.add_typer(monitoring_app, name="monitoring")

__all__ = ["app", "main"]
