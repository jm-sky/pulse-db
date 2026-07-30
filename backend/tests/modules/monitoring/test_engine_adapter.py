"""Tests for the EngineAdapter data types."""

from datetime import UTC, datetime

from app.modules.monitoring.engine_adapter import Engine, EngineCapabilities


def test_capabilities_to_jsonb_serializes_engine_and_timestamp() -> None:
    capabilities = EngineCapabilities(
        engine=Engine.POSTGRESQL,
        version="17.0",
        features={"pg_stat_statements": True, "hypopg": False},
        grants={"pg_monitor": True},
        detected_at=datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC),
    )

    payload = capabilities.to_jsonb()

    assert payload == {
        "engine": "postgresql",
        "version": "17.0",
        "features": {"pg_stat_statements": True, "hypopg": False},
        "grants": {"pg_monitor": True},
        "detected_at": "2026-07-30T12:00:00+00:00",
    }


def test_engine_capabilities_defaults_are_independent_dicts() -> None:
    a = EngineCapabilities(engine=Engine.POSTGRESQL, version="17.0")
    b = EngineCapabilities(engine=Engine.SQLSERVER, version="2022")

    a.features["x"] = True

    assert "x" not in b.features
