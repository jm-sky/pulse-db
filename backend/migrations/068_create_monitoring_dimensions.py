"""Migration 068: PulseDB monitoring domain -- dimension tables.

Raw DDL, not SQLAlchemy metadata (backend/migrations/README.md;
docs/research/2026-07-30-data-model.md §3): dimensions here are small,
deduplicated reference data joined by the (larger, partitioned) fact tables
added in migration 069.
"""

from sqlalchemy import text

from app.core.database import engine

WAIT_CLASSES: list[tuple[str, str]] = [
    ("cpu", "CPU"),
    ("lock", "Lock"),
    ("latch_buffer", "Latch/Buffer"),
    ("io_read", "IO Read"),
    ("io_write", "IO Write"),
    ("log_commit", "Log/Commit"),
    ("network_client", "Network/Client"),
    ("memory", "Memory"),
    ("idle", "Idle"),
    ("other", "Other"),
]

# Starting set only -- unknown native waits fall back to 'other' with the
# native name preserved (ADR §5), so this never blocks collection. Extended
# as Phase 1 sampler work uncovers more native wait names.
WAIT_EVENTS: list[tuple[str, str, str, bool]] = [
    # (engine, native_name, wait_class_id, is_idle)
    ("postgresql", "Client:ClientRead", "idle", True),
    ("postgresql", "Client:ClientWrite", "idle", True),
    ("postgresql", "Activity:AutoVacuumMain", "idle", True),
    ("postgresql", "Lock:relation", "lock", False),
    ("postgresql", "Lock:tuple", "lock", False),
    ("postgresql", "Lock:transactionid", "lock", False),
    ("postgresql", "LWLock:WALWrite", "log_commit", False),
    ("postgresql", "LWLock:WALInsert", "log_commit", False),
    ("postgresql", "LWLock:BufferContent", "latch_buffer", False),
    ("postgresql", "BufferPin", "latch_buffer", False),
    ("postgresql", "IO:DataFileRead", "io_read", False),
    ("postgresql", "IO:DataFileWrite", "io_write", False),
    ("postgresql", "IO:WALWrite", "io_write", False),
    ("sqlserver", "SOS_SCHEDULER_YIELD", "cpu", False),
    ("sqlserver", "LCK_M_X", "lock", False),
    ("sqlserver", "LCK_M_S", "lock", False),
    ("sqlserver", "PAGEIOLATCH_SH", "io_read", False),
    ("sqlserver", "PAGEIOLATCH_EX", "io_write", False),
    ("sqlserver", "WRITELOG", "log_commit", False),
    ("sqlserver", "ASYNC_NETWORK_IO", "network_client", False),
    ("sqlserver", "CXPACKET", "other", False),
    ("sqlserver", "MEMORY_ALLOCATION_EXT", "memory", False),
]


async def upgrade() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("""
                CREATE TABLE monitored_instance (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    engine TEXT NOT NULL CHECK (engine IN ('postgresql', 'sqlserver')),
                    host TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    database_name TEXT NOT NULL,
                    username TEXT NOT NULL,
                    encrypted_password BYTEA NOT NULL,
                    timezone TEXT NOT NULL DEFAULT 'UTC',
                    tenant_id TEXT,
                    capabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    last_seen_at TIMESTAMPTZ,
                    UNIQUE (host, port, database_name)
                )
                """))
        # ADR §8: tenant_id lives only here; every fact table carries
        # instance_id and resolves tenant via this dimension.
        await conn.execute(text("CREATE INDEX idx_monitored_instance_tenant ON monitored_instance (tenant_id)"))

        await conn.execute(text("""
                CREATE TABLE monitored_database (
                    id TEXT PRIMARY KEY,
                    instance_id TEXT NOT NULL REFERENCES monitored_instance(id) ON DELETE CASCADE,
                    database_name TEXT NOT NULL,
                    first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
                    last_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE (instance_id, database_name)
                )
                """))

        # raw_text nullable: redaction (vision §3.3) becomes a config flag,
        # not a schema change -- we simply never populate the column.
        await conn.execute(text("""
                CREATE TABLE query_text (
                    norm_hash TEXT PRIMARY KEY,
                    normalized_text TEXT NOT NULL,
                    raw_text TEXT
                )
                """))

        await conn.execute(text("""
                CREATE TABLE query (
                    id TEXT PRIMARY KEY,
                    instance_id TEXT NOT NULL REFERENCES monitored_instance(id) ON DELETE CASCADE,
                    engine TEXT NOT NULL CHECK (engine IN ('postgresql', 'sqlserver')),
                    engine_query_key TEXT NOT NULL,
                    norm_hash TEXT NOT NULL REFERENCES query_text(norm_hash),
                    first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
                    last_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE (instance_id, engine_query_key)
                )
                """))
        await conn.execute(text("CREATE INDEX idx_query_norm_hash ON query (norm_hash)"))

        # No visualizer of our own (vision §5 non-goals) -- plans are stored
        # once and exported, not rendered.
        await conn.execute(text("""
                CREATE TABLE plan_text (
                    plan_hash TEXT PRIMARY KEY,
                    plan_format TEXT NOT NULL CHECK (plan_format IN ('xml', 'json')),
                    plan_body TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """))

        # A new row for a known query_id is the plan-change event itself.
        await conn.execute(text("""
                CREATE TABLE query_plan (
                    query_id TEXT NOT NULL REFERENCES query(id) ON DELETE CASCADE,
                    plan_hash TEXT NOT NULL REFERENCES plan_text(plan_hash),
                    first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
                    last_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (query_id, plan_hash)
                )
                """))

        await conn.execute(text("""
                CREATE TABLE wait_class (
                    id TEXT PRIMARY KEY,
                    label TEXT NOT NULL
                )
                """))
        for wait_class_id, label in WAIT_CLASSES:
            await conn.execute(
                text("INSERT INTO wait_class (id, label) VALUES (:id, :label)"),
                {"id": wait_class_id, "label": label},
            )

        # Native name always preserved (ADR §5) even though it's normalized
        # into our wait_class taxonomy.
        await conn.execute(text("""
                CREATE TABLE wait_event (
                    engine TEXT NOT NULL CHECK (engine IN ('postgresql', 'sqlserver')),
                    native_name TEXT NOT NULL,
                    wait_class_id TEXT NOT NULL REFERENCES wait_class(id),
                    is_idle BOOLEAN NOT NULL DEFAULT FALSE,
                    PRIMARY KEY (engine, native_name)
                )
                """))
        for wait_engine, native_name, wait_class_id, is_idle in WAIT_EVENTS:
            await conn.execute(
                text("""
                    INSERT INTO wait_event (engine, native_name, wait_class_id, is_idle)
                    VALUES (:engine, :native_name, :wait_class_id, :is_idle)
                    """),
                {"engine": wait_engine, "native_name": native_name, "wait_class_id": wait_class_id, "is_idle": is_idle},
            )

        await conn.execute(text("""
                CREATE TABLE session_attr (
                    id TEXT PRIMARY KEY,
                    instance_id TEXT NOT NULL REFERENCES monitored_instance(id) ON DELETE CASCADE,
                    db_user TEXT NOT NULL,
                    program TEXT NOT NULL DEFAULT '',
                    client_host TEXT NOT NULL DEFAULT '',
                    UNIQUE (instance_id, db_user, program, client_host)
                )
                """))


async def downgrade() -> None:
    async with engine.begin() as conn:
        for table in (
            "session_attr",
            "wait_event",
            "wait_class",
            "query_plan",
            "plan_text",
            "query",
            "query_text",
            "monitored_database",
            "monitored_instance",
        ):
            await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
