"""Raw-SQL repository for the monitoring domain.

The domain schema is raw DDL (migrations/068, migrations/069), not
SQLAlchemy metadata (see backend/migrations/README.md), so reads/writes here
go through `text()` rather than the ORM.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.id_utils import generate_id
from app.core.database import AsyncSessionLocal

from .crypto import decrypt_secret, encrypt_secret
from .engine_adapter import Engine, EngineCapabilities, InstanceConnectionParams


@dataclass(frozen=True, slots=True)
class MonitoredInstanceRecord:
    id: str
    name: str
    engine: Engine
    host: str
    port: int
    database_name: str
    username: str
    timezone: str
    capabilities: dict
    is_active: bool


async def register_instance(
    *,
    name: str,
    engine: Engine,
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    timezone: str = "UTC",
) -> str:
    """Register a monitored instance. Password is encrypted before it ever hits the DB."""
    instance_id = generate_id()
    encrypted_password = encrypt_secret(password)
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                INSERT INTO monitored_instance
                    (id, name, engine, host, port, database_name, username, encrypted_password, timezone)
                VALUES
                    (:id, :name, :engine, :host, :port, :database_name, :username, :encrypted_password, :timezone)
                """),
            {
                "id": instance_id,
                "name": name,
                "engine": engine.value,
                "host": host,
                "port": port,
                "database_name": database,
                "username": username,
                "encrypted_password": encrypted_password,
                "timezone": timezone,
            },
        )
        await session.commit()
    return instance_id


async def list_instances() -> list[MonitoredInstanceRecord]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
                SELECT id, name, engine, host, port, database_name, username, timezone, capabilities, is_active
                FROM monitored_instance
                ORDER BY created_at
                """))
        return [
            MonitoredInstanceRecord(
                id=row.id,
                name=row.name,
                engine=Engine(row.engine),
                host=row.host,
                port=row.port,
                database_name=row.database_name,
                username=row.username,
                timezone=row.timezone,
                capabilities=row.capabilities or {},
                is_active=row.is_active,
            )
            for row in result
        ]


async def get_connection_params(session: AsyncSession, instance_id: str) -> InstanceConnectionParams:
    """Load an instance row and decrypt its password for a live connection.

    Callers own the session's lifetime (kept separate from register/list so
    the collector can reuse one session across several repository calls).
    """
    result = await session.execute(
        text("""
            SELECT engine, host, port, database_name, username, encrypted_password
            FROM monitored_instance
            WHERE id = :id
            """),
        {"id": instance_id},
    )
    row = result.one()
    return InstanceConnectionParams(
        host=row.host,
        port=row.port,
        database=row.database_name,
        username=row.username,
        password=decrypt_secret(row.encrypted_password),
        engine=Engine(row.engine),
    )


async def update_capabilities(session: AsyncSession, instance_id: str, capabilities: EngineCapabilities) -> None:
    await session.execute(
        text("""
            UPDATE monitored_instance
            SET capabilities = CAST(:capabilities AS jsonb), last_seen_at = now(), updated_at = now()
            WHERE id = :id
            """),
        {"id": instance_id, "capabilities": json.dumps(capabilities.to_jsonb())},
    )


async def get_last_collector_run(session: AsyncSession, instance_id: str) -> tuple[datetime | None, int | None]:
    """Return (finished_at, interval_ms) of the most recent run, or (None, None)."""
    result = await session.execute(
        text("""
            SELECT finished_at, interval_ms
            FROM collector_run
            WHERE instance_id = :instance_id AND finished_at IS NOT NULL
            ORDER BY started_at DESC
            LIMIT 1
            """),
        {"instance_id": instance_id},
    )
    row = result.first()
    if row is None:
        return None, None
    return row.finished_at, row.interval_ms


async def insert_collector_run(
    session: AsyncSession,
    *,
    instance_id: str,
    started_at: datetime,
    finished_at: datetime | None,
    status: str,
    interval_ms: int,
    overhead_ms: float | None,
    clock_offset_ms: float | None,
    gap_detected: bool,
    gap_seconds: float | None,
    error_message: str | None,
) -> str:
    run_id = generate_id()
    await session.execute(
        text("""
            INSERT INTO collector_run
                (id, instance_id, started_at, finished_at, status, interval_ms, overhead_ms,
                 clock_offset_ms, gap_detected, gap_seconds, error_message)
            VALUES
                (:id, :instance_id, :started_at, :finished_at, :status, :interval_ms, :overhead_ms,
                 :clock_offset_ms, :gap_detected, :gap_seconds, :error_message)
            """),
        {
            "id": run_id,
            "instance_id": instance_id,
            "started_at": started_at,
            "finished_at": finished_at,
            "status": status,
            "interval_ms": interval_ms,
            "overhead_ms": overhead_ms,
            "clock_offset_ms": clock_offset_ms,
            "gap_detected": gap_detected,
            "gap_seconds": gap_seconds,
            "error_message": error_message,
        },
    )
    return run_id


async def insert_instance_metric(session: AsyncSession, *, instance_id: str, sampled_at: datetime, metric_id: str, value: float) -> None:
    await session.execute(
        text("""
            INSERT INTO instance_metric (id, instance_id, sampled_at, metric_id, value)
            VALUES (:id, :instance_id, :sampled_at, :metric_id, :value)
            """),
        {"id": generate_id(), "instance_id": instance_id, "sampled_at": sampled_at, "metric_id": metric_id, "value": value},
    )
