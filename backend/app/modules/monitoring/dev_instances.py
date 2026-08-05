"""Idempotent registration of default monitored instances for local development."""

from __future__ import annotations

import os

from . import repository
from .crypto import CredentialsEncryptionNotConfigured
from .engine_adapter import Engine

DEV_INSTANCES: list[dict[str, str | int]] = [
    {
        "name": "pulse-db-local",
        "engine": "postgresql",
        "host": os.getenv("PULSEDB_SELF_HOST", "db"),
        "port": int(os.getenv("PULSEDB_SELF_PORT", "5432")),
        "database": os.getenv("POSTGRES_DB", os.getenv("PULSEDB_SELF_DATABASE", "pulse_db")),
        "username": os.getenv("POSTGRES_USER", os.getenv("PULSEDB_SELF_USERNAME", "backend")),
        "password": os.getenv("POSTGRES_PASSWORD", os.getenv("PULSEDB_SELF_PASSWORD", "changeme")),
    },
    {
        "name": "sql-monitor-postgres",
        "engine": "postgresql",
        "host": os.getenv("SQL_MONITOR_PG_HOST", "host.docker.internal"),
        "port": int(os.getenv("SQL_MONITOR_PG_PORT", "5433")),
        "database": os.getenv("SQL_MONITOR_PG_DATABASE", "sql_monitor"),
        "username": os.getenv("SQL_MONITOR_PG_USER", "sqlmonitor"),
        "password": os.getenv("SQL_MONITOR_PG_PASSWORD", "sqlmonitor"),
    },
    # taxorder-ksef-db-dev has no host port; reach it via Docker network taxorder-ksef-dev
    # (attach app/scheduler in docker-compose — see external network taxorder-ksef-dev).
    {
        "name": "taxorder-ksef-local",
        "engine": "postgresql",
        "host": os.getenv("TAXORDER_KSEF_PG_HOST", "taxorder-ksef-db-dev"),
        "port": int(os.getenv("TAXORDER_KSEF_PG_PORT", "5432")),
        "database": os.getenv("TAXORDER_KSEF_PG_DATABASE", "taxorder-ksef"),
        "username": os.getenv("TAXORDER_KSEF_PG_USER", "taxorder-ksef"),
        "password": os.getenv("TAXORDER_KSEF_PG_PASSWORD", "password"),
    },
]


async def register_dev_instances(repair: bool = False) -> tuple[list[str], list[str], list[str]]:
    """Register dev instances. With repair=True, refresh connection params for existing names."""
    existing = {row.name: row for row in await repository.list_instances()}
    created: list[str] = []
    skipped: list[str] = []
    repaired: list[str] = []

    for spec in DEV_INSTANCES:
        name = str(spec["name"])
        host = str(spec["host"])
        port = int(spec["port"])
        database = str(spec["database"])
        username = str(spec["username"])
        password = str(spec["password"])

        if name in existing:
            if repair:
                await repository.update_instance_connection(
                    instance_id=existing[name].id,
                    host=host,
                    port=port,
                    database=database,
                    username=username,
                    password=password,
                )
                repaired.append(f"{name} ({existing[name].id})")
            else:
                skipped.append(name)
            continue

        engine = Engine(str(spec["engine"]))
        instance_id = await repository.register_instance(
            name=name,
            engine=engine,
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
        )
        created.append(f"{name} ({instance_id})")

    return created, skipped, repaired


async def register_dev_instances_or_raise(repair: bool = False) -> tuple[list[str], list[str], list[str]]:
    try:
        return await register_dev_instances(repair=repair)
    except CredentialsEncryptionNotConfigured as exc:
        raise RuntimeError(str(exc)) from exc
