"""Monitoring domain CLI commands: register instances, run the trivial
collector, and maintain partitions.

Roadmap Phase 0 exit criteria: "zarejestrowane dwie instancje ... trywialny
kolektor zapisuje fakty ... narzut kolektora jest mierzony i widoczny" --
these commands are the operational surface for that until a real scheduler
and Web UI exist (Phase 2).
"""

import asyncio

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from ..main import COMMAND_GROUPS, show_group_interactive_menu

monitoring_app = typer.Typer(
    name="monitoring",
    help="PulseDB monitoring domain: instances, collector, partitions",
    no_args_is_help=False,
)

console = Console()


@monitoring_app.callback(invoke_without_command=True)
def monitoring_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        show_group_interactive_menu("monitoring", COMMAND_GROUPS["monitoring"])


@monitoring_app.command("register-instance")
def register_instance(
    name: str = typer.Option(..., "--name", help="Display name for this instance"),
    engine: str = typer.Option(..., "--engine", help="postgresql or sqlserver"),
    host: str = typer.Option(..., "--host", help="Hostname/IP of the monitored instance"),
    port: int = typer.Option(..., "--port", help="Port of the monitored instance"),
    database: str = typer.Option(..., "--database", help="Database name to connect to"),
    username: str = typer.Option(..., "--username", help="Read-only monitoring account username"),
    password: str | None = typer.Option(None, "--password", help="Password (prompted if omitted)"),
) -> None:
    """Register a monitored instance. The password is encrypted before storage."""
    from app.modules.monitoring import repository
    from app.modules.monitoring.crypto import CredentialsEncryptionNotConfigured
    from app.modules.monitoring.engine_adapter import Engine

    try:
        engine_enum = Engine(engine)
    except ValueError:
        console.print(f"[red]Unknown engine:[/red] {engine}. Use 'postgresql' or 'sqlserver'.")
        raise typer.Exit(1) from None

    resolved_password = password or Prompt.ask("Password", password=True)

    async def _register() -> str:
        return await repository.register_instance(
            name=name,
            engine=engine_enum,
            host=host,
            port=port,
            database=database,
            username=username,
            password=resolved_password,
        )

    try:
        instance_id = asyncio.run(_register())
    except CredentialsEncryptionNotConfigured as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from None

    console.print(f"[bold green]Registered instance:[/bold green] {instance_id}")


@monitoring_app.command("list-instances")
def list_instances() -> None:
    """List registered monitored instances."""
    from app.modules.monitoring import repository

    instances = asyncio.run(repository.list_instances())
    table = Table(title="Monitored Instances")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Engine")
    table.add_column("Host:Port")
    table.add_column("Database")
    table.add_column("Active")

    for inst in instances:
        table.add_row(inst.id, inst.name, inst.engine.value, f"{inst.host}:{inst.port}", inst.database_name, "yes" if inst.is_active else "no")

    console.print(table)


@monitoring_app.command("detect-capabilities")
def detect_capabilities(instance_id: str = typer.Argument(..., help="Instance ID from list-instances")) -> None:
    """Connect to an instance and store detected extensions/grants (ADR capabilities jsonb)."""
    from app.modules.monitoring.collector import detect_and_store_capabilities

    capabilities = asyncio.run(detect_and_store_capabilities(instance_id))
    console.print(f"[bold]Engine:[/bold] {capabilities.engine.value}  [bold]Version:[/bold] {capabilities.version}")
    console.print(f"[bold]Features:[/bold] {capabilities.features}")
    console.print(f"[bold]Grants:[/bold] {capabilities.grants}")


@monitoring_app.command("collect")
def collect(
    instance_id: str = typer.Argument(..., help="Instance ID from list-instances"),
    interval_ms: int = typer.Option(60_000, "--interval-ms", help="Expected cadence, used for gap detection"),
) -> None:
    """Run one trivial collection tick against an instance (proves the adapter -> fact-table path)."""
    from app.modules.monitoring.collector import run_trivial_collection

    result = asyncio.run(run_trivial_collection(instance_id, interval_ms=interval_ms))

    if result.status == "ok":
        console.print(f"[bold green]OK[/bold green] active_sessions={result.active_session_count} " f"overhead_ms={result.overhead_ms:.2f} clock_offset_ms={result.clock_offset_ms:.2f}")
    else:
        console.print(f"[bold red]ERROR[/bold red] {result.error_message}")

    if result.gap_detected:
        console.print(f"[yellow]Gap detected:[/yellow] {result.gap_seconds:.1f}s since expected previous run")


@monitoring_app.command("partitions-maintain")
def partitions_maintain(
    days_ahead: int = typer.Option(3, "--days-ahead", help="How many days ahead to pre-create partitions"),
) -> None:
    """Create upcoming day partitions and drop ones past retention (ADR §6)."""
    from app.core.database import engine as db_engine
    from app.modules.monitoring.partitions import maintain_all_partitions

    async def _maintain() -> list:
        async with db_engine.begin() as conn:
            return await maintain_all_partitions(conn, days_ahead=days_ahead)

    results = asyncio.run(_maintain())
    for result in results:
        console.print(f"[bold]{result.table}[/bold]: ensured {len(result.created)} partition(s), dropped {len(result.dropped)} expired")
        if result.dropped:
            console.print(f"  [yellow]dropped:[/yellow] {', '.join(result.dropped)}")
