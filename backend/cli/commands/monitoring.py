"""Monitoring domain CLI commands: register instances, run the trivial
collector, the Phase 1 session sampler and query-stats collector, maintain
partitions, and run the scheduler that ties all of the above into a
continuous process.

Roadmap Phase 0 exit criteria: "zarejestrowane dwie instancje ... trywialny
kolektor zapisuje fakty ... narzut kolektora jest mierzony i widoczny" --
these commands are the operational surface for that until a Web UI exists
(Phase 2). `sample-sessions`/`collect-query-stats` are the Phase 1 elements
1/2 PostgreSQL slice; `sample-wait-history` is the explicit-opt-in richer
source on top of element 1 (docs/plans/2026-07-30-phase1-diagnostic-core.md).
`rollup-*` are Phase 0 element 7 (docs/plans/2026-07-31-rollups.md) -- run
`rollup-ash-1m` before `rollup-ash-1h`, since the hourly rollup reads the
minute rollup, not raw session_sample. `run-scheduler` is Phase 0 element 8
(docs/plans/2026-07-31-scheduler.md): runs every tick above on its own
cadence, for every active instance, until stopped -- the long-running
process a `docker compose up` deployment actually needs instead of someone
re-invoking these commands by hand.
"""

import asyncio
import signal

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


@monitoring_app.command("register-dev-instances")
def register_dev_instances_cmd(
    repair: bool = typer.Option(
        False,
        "--repair",
        help="Update host/credentials for existing dev instances (e.g. fix 127.0.0.1 → db in Docker)",
    ),
) -> None:
    """Register pulse-db-local + sql-monitor-postgres + taxorder-ksef-local (idempotent).

    Run inside the app container so pulse-db-local uses host `db`. After registering
    from the host with 127.0.0.1, run again with --repair inside Docker.

    sql-monitor-postgres uses host.docker.internal:5433. Grant pg_monitor once:

        docker exec -it <sql-monitor-postgres> psql -U sqlmonitor -d sql_monitor \\
          -c "GRANT pg_monitor TO sqlmonitor;"

    taxorder-ksef-local uses Docker DNS taxorder-ksef-db-dev:5432 (network
    taxorder-ksef-dev on app/scheduler). Grant pg_monitor once:

        docker exec -it taxorder-ksef-db-dev psql -U taxorder-ksef -d taxorder-ksef \\
          -c "GRANT pg_monitor TO \\"taxorder-ksef\\";"
    """
    from app.modules.monitoring.dev_instances import register_dev_instances_or_raise

    try:
        created, skipped, repaired = asyncio.run(register_dev_instances_or_raise(repair=repair))
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from None

    if created:
        console.print(f"[bold green]Registered:[/bold green] {', '.join(created)}")
    if repaired:
        console.print(f"[bold yellow]Repaired:[/bold yellow] {', '.join(repaired)}")
    if skipped:
        console.print(f"[dim]Already registered (skipped):[/dim] {', '.join(skipped)}")
    if not created and not skipped and not repaired:
        console.print("[yellow]No instances configured.[/yellow]")


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


@monitoring_app.command("sample-sessions")
def sample_sessions(
    instance_id: str = typer.Argument(..., help="Instance ID from list-instances"),
    interval_ms: int = typer.Option(1_000, "--interval-ms", help="Expected cadence, used for gap detection"),
) -> None:
    """Run one ASH tick: snapshot active sessions with wait attribution (Phase 1 element 1)."""
    from app.modules.monitoring.collector import run_session_sample_collection

    result = asyncio.run(run_session_sample_collection(instance_id, interval_ms=interval_ms))

    if result.status == "ok":
        console.print(f"[bold green]OK[/bold green] sessions={result.session_count} overhead_ms={result.overhead_ms:.2f}")
    else:
        console.print(f"[bold red]ERROR[/bold red] {result.error_message}")

    if result.gap_detected:
        console.print(f"[yellow]Gap detected:[/yellow] {result.gap_seconds:.1f}s since expected previous run")


@monitoring_app.command("collect-query-stats")
def collect_query_stats(
    instance_id: str = typer.Argument(..., help="Instance ID from list-instances"),
    interval_ms: int = typer.Option(60_000, "--interval-ms", help="Expected cadence, used for gap detection"),
) -> None:
    """Run one tick: pull pg_stat_statements deltas into query_stat_delta (Phase 1 element 2, PostgreSQL only)."""
    from app.modules.monitoring.collector import run_query_stats_collection

    result = asyncio.run(run_query_stats_collection(instance_id, interval_ms=interval_ms))

    if result.status == "ok":
        console.print(f"[bold green]OK[/bold green] queries_seen={result.queries_seen} deltas_written={result.deltas_written} overhead_ms={result.overhead_ms:.2f}")
    else:
        console.print(f"[bold red]ERROR[/bold red] {result.error_message}")

    if result.gap_detected:
        console.print(f"[yellow]Gap detected:[/yellow] {result.gap_seconds:.1f}s since expected previous run")


@monitoring_app.command("collect-query-plans")
def collect_query_plans(
    instance_id: str = typer.Argument(..., help="Instance ID from list-instances"),
    interval_ms: int = typer.Option(600_000, "--interval-ms", help="Expected cadence, used for gap detection"),
    top_n: int = typer.Option(20, "--top-n", help="Top-N queries by total time to fetch plans for"),
) -> None:
    """Run one tick: fetch top-N execution plans into plan_text/query_plan (Phase 1 element 3).

    A new (query_id, plan_hash) row is a plan-change event. See docs/plans/2026-08-05-query-plans.md.
    """
    from app.modules.monitoring.collector import run_query_plans_collection

    result = asyncio.run(run_query_plans_collection(instance_id, interval_ms=interval_ms, top_n=top_n))

    if result.status == "ok":
        console.print(f"[bold green]OK[/bold green] plans_seen={result.plans_seen} " f"plans_new={result.plans_new} overhead_ms={result.overhead_ms:.2f}")
    else:
        console.print(f"[bold red]ERROR[/bold red] {result.error_message}")

    if result.gap_detected:
        console.print(f"[yellow]Gap detected:[/yellow] {result.gap_seconds:.1f}s since expected previous run")


@monitoring_app.command("collect-blocking")
def collect_blocking(
    instance_id: str = typer.Argument(..., help="Instance ID from list-instances"),
    interval_ms: int = typer.Option(30_000, "--interval-ms", help="Expected cadence, used for gap detection"),
) -> None:
    """Run one tick: snapshot active lock chains into blocking_event (Phase 1 element 4)."""
    from app.modules.monitoring.collector import run_blocking_collection

    result = asyncio.run(run_blocking_collection(instance_id, interval_ms=interval_ms))

    if result.status == "ok":
        console.print(f"[bold green]OK[/bold green] events_written={result.events_written} overhead_ms={result.overhead_ms:.2f}")
    else:
        console.print(f"[bold red]ERROR[/bold red] {result.error_message}")

    if result.gap_detected:
        console.print(f"[yellow]Gap detected:[/yellow] {result.gap_seconds:.1f}s since expected previous run")


@monitoring_app.command("collect-deadlocks")
def collect_deadlocks(
    instance_id: str = typer.Argument(..., help="Instance ID from list-instances"),
    interval_ms: int = typer.Option(60_000, "--interval-ms", help="Expected cadence, used for gap detection"),
) -> None:
    """Run one tick: drain deadlock history into deadlock_event (Phase 1 element 4).

    SQL Server: system_health XE ring buffer. PostgreSQL: no-op (empty) in MVP.
    """
    from app.modules.monitoring.collector import run_deadlocks_collection

    result = asyncio.run(run_deadlocks_collection(instance_id, interval_ms=interval_ms))

    if result.status == "ok":
        console.print(f"[bold green]OK[/bold green] events_written={result.events_written} overhead_ms={result.overhead_ms:.2f}")
    else:
        console.print(f"[bold red]ERROR[/bold red] {result.error_message}")

    if result.gap_detected:
        console.print(f"[yellow]Gap detected:[/yellow] {result.gap_seconds:.1f}s since expected previous run")


@monitoring_app.command("sample-wait-history")
def sample_wait_history(
    instance_id: str = typer.Argument(..., help="Instance ID from list-instances"),
) -> None:
    """Richer-source ASH tick (PostgreSQL only, opt-in): drain pg_wait_sampling_history since the
    last watermark instead of one pg_stat_activity point sample per poll.

    Substantially higher-resolution than `sample-sessions` (the extension's
    native ~10ms period vs. a ~1s poll) but writes proportionally more
    session_sample rows -- read the printed note before running this on a
    schedule. See docs/grants.md and docs/plans/2026-07-30-phase1-diagnostic-core.md.
    """
    from app.modules.monitoring.collector import run_wait_sampling_history_collection

    result = asyncio.run(run_wait_sampling_history_collection(instance_id))

    if result.status == "ok":
        console.print(f"[bold green]OK[/bold green] samples={result.samples_written} distinct_sessions={result.distinct_sessions} history_period_ms={result.history_period_ms} overhead_ms={result.overhead_ms:.2f}")
    else:
        console.print(f"[bold red]ERROR[/bold red] {result.error_message}")

    if result.note:
        console.print(f"[cyan]Note:[/cyan] {result.note}")

    if result.gap_detected:
        console.print(f"[yellow]Ring buffer overrun:[/yellow] ~{result.gap_seconds:.1f}s of history lost since last collection -- poll more often or accept the gap")


@monitoring_app.command("rollup-ash-1m")
def rollup_ash_1m(
    instance_id: str = typer.Argument(..., help="Instance ID from list-instances"),
    top_n: int = typer.Option(20, "--top-n", help="Heaviest (query, wait class) pairs kept per bucket; rest folds into one 'other' row"),
) -> None:
    """Roll closed 1-minute session_sample buckets into ash_1m (Phase 0 element 7, ADR §6)."""
    from app.modules.monitoring.rollups import run_ash_1m_rollup

    result = asyncio.run(run_ash_1m_rollup(instance_id, top_n=top_n))
    console.print(f"[bold green]OK[/bold green] buckets_processed={result.buckets_processed} rows_written={result.rows_written} last_bucket={result.last_bucket}")


@monitoring_app.command("rollup-ash-1h")
def rollup_ash_1h(
    instance_id: str = typer.Argument(..., help="Instance ID from list-instances"),
    top_n: int = typer.Option(20, "--top-n", help="Heaviest (query, wait class) pairs kept per bucket; rest folds into one 'other' row"),
) -> None:
    """Roll closed 1-hour ash_1m buckets into ash_1h (Phase 0 element 7, ADR §6). Requires rollup-ash-1m to have run first."""
    from app.modules.monitoring.rollups import run_ash_1h_rollup

    result = asyncio.run(run_ash_1h_rollup(instance_id, top_n=top_n))
    console.print(f"[bold green]OK[/bold green] buckets_processed={result.buckets_processed} rows_written={result.rows_written} last_bucket={result.last_bucket}")


@monitoring_app.command("rollup-query-stats-1h")
def rollup_query_stats_1h(
    instance_id: str = typer.Argument(..., help="Instance ID from list-instances"),
    top_n: int = typer.Option(20, "--top-n", help="Heaviest queries by total_time_ms kept per bucket; rest folds into one 'other' row"),
) -> None:
    """Roll closed 1-hour query_stat_delta buckets into query_stat_1h (Phase 0 element 7, ADR §6)."""
    from app.modules.monitoring.rollups import run_query_stat_1h_rollup

    result = asyncio.run(run_query_stat_1h_rollup(instance_id, top_n=top_n))
    console.print(f"[bold green]OK[/bold green] buckets_processed={result.buckets_processed} rows_written={result.rows_written} last_bucket={result.last_bucket}")


@monitoring_app.command("run-scheduler")
def run_scheduler(
    instance_refresh_seconds: float = typer.Option(300.0, "--instance-refresh-seconds", help="How often to re-poll the instance list for newly registered/deactivated instances"),
    partitions_interval_seconds: float = typer.Option(3600.0, "--partitions-interval-seconds", help="How often to run partition maintenance"),
) -> None:
    """Run the continuous scheduler: every collector/rollup tick, for every active instance, until stopped.

    Foreground process, intended as the container's long-running command
    (see docker-compose.yml `scheduler` service) rather than an interactive
    CLI invocation -- stop with SIGINT/SIGTERM for a clean shutdown (every
    running tick loop is stopped and awaited before the process exits, no
    dangling tasks).
    """
    from app.core.logging_config import configure_logging
    from app.modules.monitoring.scheduler import Scheduler

    configure_logging()
    scheduler = Scheduler(instance_refresh_interval_seconds=instance_refresh_seconds, partitions_maintain_interval_seconds=partitions_interval_seconds)

    async def _run() -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, scheduler.stop)
        console.print("[bold green]Scheduler started[/bold green] -- Ctrl+C or SIGTERM to stop")
        await scheduler.run()
        console.print("[bold]Scheduler stopped[/bold]")

    asyncio.run(_run())


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
