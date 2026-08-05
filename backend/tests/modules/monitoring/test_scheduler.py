"""Tests for the scheduler (roadmap Phase 0 element 8): tick-engine
selection, the generic periodic-tick loop, and instance-membership
sync/shutdown -- all with fake tick/instance-listing callables so nothing
here touches a real database or sleeps out a real cadence."""

import asyncio
from dataclasses import dataclass, field

import pytest

from app.modules.monitoring.engine_adapter import Engine
from app.modules.monitoring.scheduler import (
    Scheduler,
    TickSpec,
    _run_periodic_tick,
    _ticks_for_engine,
    run_instance_forever,
)


class TestTicksForEngine:
    def test_postgresql_gets_all_ticks(self) -> None:
        names = {spec.name for spec in _ticks_for_engine(Engine.POSTGRESQL)}

        assert names == {"trivial", "session_sample", "query_stats", "rollup_ash_1m", "rollup_ash_1h", "rollup_query_stat_1h"}

    def test_sqlserver_gets_all_ticks(self) -> None:
        names = {spec.name for spec in _ticks_for_engine(Engine.SQLSERVER)}

        assert names == {"trivial", "session_sample", "query_stats", "rollup_ash_1m", "rollup_ash_1h", "rollup_query_stat_1h"}


@dataclass
class _Counter:
    calls: list[str] = field(default_factory=list)


@pytest.mark.asyncio
async def test_run_periodic_tick_calls_fn_and_stops_promptly() -> None:
    """fn stops the loop itself after 3 calls -- deterministic without racing real time."""
    counter = _Counter()
    stop_event = asyncio.Event()

    async def fake_fn(instance_id: str) -> str:
        counter.calls.append(instance_id)
        if len(counter.calls) >= 3:
            stop_event.set()
        return "ok"

    spec = TickSpec("fake", 0.01, fake_fn)

    await asyncio.wait_for(_run_periodic_tick("instance-1", spec, stop_event=stop_event), timeout=2.0)

    assert counter.calls == ["instance-1", "instance-1", "instance-1"]


@pytest.mark.asyncio
async def test_run_periodic_tick_survives_exceptions_and_keeps_ticking() -> None:
    counter = _Counter()
    stop_event = asyncio.Event()

    async def flaky_fn(instance_id: str) -> str:
        counter.calls.append(instance_id)
        if len(counter.calls) == 1:
            raise RuntimeError("boom")
        stop_event.set()
        return "ok"

    spec = TickSpec("fake", 0.01, flaky_fn)

    await asyncio.wait_for(_run_periodic_tick("instance-1", spec, stop_event=stop_event), timeout=2.0)

    assert len(counter.calls) == 2


@pytest.mark.asyncio
async def test_run_instance_forever_runs_all_ticks_for_engine_concurrently() -> None:
    stop_event = asyncio.Event()
    seen: set[str] = set()

    async def fake_tick_a(instance_id: str) -> None:
        seen.add("a")
        if seen >= {"a", "b"}:
            stop_event.set()

    async def fake_tick_b(instance_id: str) -> None:
        seen.add("b")
        if seen >= {"a", "b"}:
            stop_event.set()

    from unittest.mock import patch

    fake_ticks = (TickSpec("a", 0.01, fake_tick_a), TickSpec("b", 0.01, fake_tick_b))

    with patch("app.modules.monitoring.scheduler._ticks_for_engine", return_value=fake_ticks):
        await asyncio.wait_for(run_instance_forever("instance-1", Engine.POSTGRESQL, stop_event), timeout=2.0)

    assert seen == {"a", "b"}


@pytest.mark.asyncio
async def test_scheduler_starts_and_stops_instances_as_membership_changes() -> None:
    started: list[str] = []
    stop_events: dict[str, asyncio.Event] = {}

    async def fake_run_instance(instance_id: str, engine: Engine, stop_event: asyncio.Event) -> None:
        started.append(instance_id)
        stop_events[instance_id] = stop_event
        await stop_event.wait()

    @dataclass
    class FakeInstance:
        id: str
        is_active: bool
        engine: Engine = Engine.POSTGRESQL

    call_count = 0

    async def fake_list_instances() -> list[FakeInstance]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [FakeInstance("i1", True), FakeInstance("i2", True)]
        return [FakeInstance("i1", True), FakeInstance("i2", False)]  # i2 deactivated

    scheduler = Scheduler(run_instance=fake_run_instance, list_instances=fake_list_instances)

    await scheduler._sync_instances()
    await asyncio.sleep(0)  # let the newly created instance tasks run up to their first await
    assert started == ["i1", "i2"]
    assert set(scheduler._running) == {"i1", "i2"}

    await scheduler._sync_instances()
    assert set(scheduler._running) == {"i1"}
    assert stop_events["i2"].is_set()

    # clean up i1
    await scheduler._stop_instance("i1")
    assert scheduler._running == {}


@pytest.mark.asyncio
async def test_scheduler_run_stops_cleanly_and_awaits_everything() -> None:
    @dataclass
    class FakeInstance:
        id: str
        is_active: bool
        engine: Engine = Engine.POSTGRESQL

    instance_stop_events: dict[str, asyncio.Event] = {}

    async def fake_run_instance(instance_id: str, engine: Engine, stop_event: asyncio.Event) -> None:
        instance_stop_events[instance_id] = stop_event
        await stop_event.wait()

    async def fake_list_instances() -> list[FakeInstance]:
        return [FakeInstance("i1", True)]

    partitions_calls: list[float] = []

    async def fake_partitions_loop(*, stop_event: asyncio.Event, interval_seconds: float) -> None:
        partitions_calls.append(interval_seconds)
        await stop_event.wait()

    scheduler = Scheduler(
        instance_refresh_interval_seconds=60.0,
        run_instance=fake_run_instance,
        list_instances=fake_list_instances,
        partitions_maintenance_loop=fake_partitions_loop,
    )

    run_task = asyncio.create_task(scheduler.run())
    # give the scheduler a moment to perform its first sync and start the instance loop
    for _ in range(50):
        if "i1" in instance_stop_events:
            break
        await asyncio.sleep(0.02)
    assert "i1" in instance_stop_events

    scheduler.stop()
    await asyncio.wait_for(run_task, timeout=2.0)

    assert instance_stop_events["i1"].is_set()
    assert scheduler._running == {}
    assert partitions_calls == [3600.0]
