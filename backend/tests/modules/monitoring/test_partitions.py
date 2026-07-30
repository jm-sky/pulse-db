"""Tests for daily partition maintenance (mocked AsyncConnection).

Real-Postgres coverage (partition creation, insert routing, downgrade, and
actual DROP TABLE on expiry) was run manually against a local PostgreSQL 16
during development -- see docs/plans/2026-07-30-phase0-foundation.md. Raw-DDL
migrations can't run under this suite's SQLite test database
(tests/conftest.py), so these tests pin down the pure logic: which
partitions get named/created/dropped for a given `today`.
"""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.modules.monitoring.partitions import (
    PartitionedTable,
    drop_expired_partitions,
    ensure_daily_partitions,
)

TABLE = PartitionedTable("session_sample", "sampled_at", retention_days=7)


@pytest.mark.asyncio
async def test_ensure_daily_partitions_covers_behind_and_ahead_window() -> None:
    conn = AsyncMock()

    created = await ensure_daily_partitions(conn, TABLE, days_ahead=2, days_behind=1, today=date(2026, 7, 30))

    assert created == [
        "session_sample_p20260729",
        "session_sample_p20260730",
        "session_sample_p20260731",
        "session_sample_p20260801",
    ]
    assert conn.execute.await_count == 4


@pytest.mark.asyncio
async def test_ensure_daily_partitions_uses_half_open_date_range() -> None:
    conn = AsyncMock()

    await ensure_daily_partitions(conn, TABLE, days_ahead=0, days_behind=0, today=date(2026, 7, 30))

    sql = str(conn.execute.await_args.args[0])
    assert "FOR VALUES FROM ('2026-07-30') TO ('2026-07-31')" in sql


@pytest.mark.asyncio
async def test_drop_expired_partitions_drops_only_partitions_past_retention() -> None:
    conn = AsyncMock()
    conn.execute = AsyncMock(
        side_effect=[
            [
                ("session_sample_p20260723",),  # exactly at cutoff (today - 7d) -- kept
                ("session_sample_p20260710",),  # well past retention -- dropped
                ("session_sample_default",),  # never touched
            ],
            None,  # DROP TABLE for the expired partition
        ]
    )

    dropped = await drop_expired_partitions(conn, TABLE, today=date(2026, 7, 30))

    assert dropped == ["session_sample_p20260710"]
    assert conn.execute.await_count == 2


@pytest.mark.asyncio
async def test_drop_expired_partitions_ignores_unparseable_suffixes() -> None:
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=[("session_sample_default",), ("session_sample_weird",)])

    dropped = await drop_expired_partitions(conn, TABLE, today=date(2026, 7, 30))

    assert dropped == []
    assert conn.execute.await_count == 1
