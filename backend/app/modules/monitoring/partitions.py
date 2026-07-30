"""Daily partition maintenance for PulseDB's time-series fact tables.

ADR (docs/research/2026-07-30-data-model.md) §3, §6: we deliberately stay on
plain PostgreSQL 17 with declarative partitioning instead of pg_partman (no
extra extension to install on the target host) or TimescaleDB (TSL license
concerns for the AGPL story) -- so partition creation/retention is our own
small job, not someone else's extension.

Each managed table is created (in its migration) as `PARTITION BY RANGE
(<time_column>)` plus a `DEFAULT` partition as a safety net. This module
creates real day partitions ahead of time and drops ones past retention via
`DROP TABLE` (never `DELETE`, per ADR §7).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


@dataclass(frozen=True, slots=True)
class PartitionedTable:
    name: str
    time_column: str
    retention_days: int


# Retention per ADR §7. query_stat_delta isn't listed explicitly there (it
# feeds query_stat_1h, which is 13 months) -- kept short since it's raw,
# high-cadence input, same category as session_sample/instance_metric.
PARTITIONED_TABLES: tuple[PartitionedTable, ...] = (
    PartitionedTable("session_sample", "sampled_at", retention_days=7),
    PartitionedTable("query_stat_delta", "bucket_start", retention_days=35),
    PartitionedTable("instance_metric", "sampled_at", retention_days=35),
    PartitionedTable("index_snapshot", "snapshot_at", retention_days=396),
    PartitionedTable("collector_run", "started_at", retention_days=396),
)


def _partition_name(table: str, day: date) -> str:
    return f"{table}_p{day:%Y%m%d}"


async def ensure_daily_partitions(
    conn: AsyncConnection,
    table: PartitionedTable,
    *,
    days_ahead: int = 3,
    days_behind: int = 1,
    today: date | None = None,
) -> list[str]:
    """Create (idempotently) day partitions covering [today-days_behind, today+days_ahead].

    Returns the names of partitions created by this call.
    """
    today = today or datetime.now(UTC).date()
    created: list[str] = []
    for offset in range(-days_behind, days_ahead + 1):
        day = today + timedelta(days=offset)
        next_day = day + timedelta(days=1)
        partition = _partition_name(table.name, day)
        # DDL (CREATE TABLE ... PARTITION OF) doesn't accept bind
        # parameters over the asyncpg extended protocol -- the bounds are
        # internally generated ISO dates, not user input, so literal
        # interpolation here is safe.
        await conn.execute(text(f'CREATE TABLE IF NOT EXISTS "{partition}" PARTITION OF "{table.name}" ' f"FOR VALUES FROM ('{day.isoformat()}') TO ('{next_day.isoformat()}')"))
        created.append(partition)
    return created


async def drop_expired_partitions(
    conn: AsyncConnection,
    table: PartitionedTable,
    *,
    today: date | None = None,
) -> list[str]:
    """Drop day partitions whose entire range is older than the table's retention."""
    today = today or datetime.now(UTC).date()
    cutoff = today - timedelta(days=table.retention_days)
    prefix = f"{table.name}_p"

    rows = await conn.execute(
        text("""
            SELECT c.relname
            FROM pg_inherits i
            JOIN pg_class c ON c.oid = i.inhrelid
            JOIN pg_class p ON p.oid = i.inhparent
            WHERE p.relname = :parent
            """),
        {"parent": table.name},
    )

    dropped: list[str] = []
    for (partition_name,) in rows:
        if not partition_name.startswith(prefix):
            continue  # e.g. the DEFAULT partition -- never auto-dropped
        suffix = partition_name[len(prefix) :]
        try:
            partition_day = datetime.strptime(suffix, "%Y%m%d").date()
        except ValueError:
            continue
        if partition_day < cutoff:
            await conn.execute(text(f'DROP TABLE IF EXISTS "{partition_name}"'))
            dropped.append(partition_name)
    return dropped


@dataclass(frozen=True, slots=True)
class PartitionMaintenanceResult:
    table: str
    created: list[str]
    dropped: list[str]


async def maintain_all_partitions(conn: AsyncConnection, *, days_ahead: int = 3) -> list[PartitionMaintenanceResult]:
    """Run ensure+drop for every managed table. One connection, caller commits."""
    results: list[PartitionMaintenanceResult] = []
    for table in PARTITIONED_TABLES:
        created = await ensure_daily_partitions(conn, table, days_ahead=days_ahead)
        dropped = await drop_expired_partitions(conn, table)
        results.append(PartitionMaintenanceResult(table=table.name, created=created, dropped=dropped))
    return results
