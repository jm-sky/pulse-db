"""In-process scheduler (roadmap Phase 0 element 8, "harmonogram"): runs the
collector/rollup ticks continuously instead of one-off CLI invocations.

Everything up to now (`collector.py`, `rollups.py`) is a single tick per
call -- idempotent, gap-detecting, never-crashing, but somebody still has to
call it on a cadence. That's this module. It does not reimplement any
tick's own correctness logic (overhead measurement, gap detection, watermark
advancement all stay in `collector.py`/`rollups.py`); it only owns *when*
each tick runs and *for which instances*, so the roadmap Phase 1 exit
criterion ("sampler pracuje 7 dni bez przerwy") is something that can
actually happen without a human re-running a CLI command every second.

Design:

- One `TickSpec` per cadence (name, interval, the tick coroutine). Intervals
  are independent -- a 1s session-sample loop and a 60s query-stats loop for
  the same instance run concurrently, not interleaved on a shared clock.
- SQL Server instances only get the `trivial` tick (the only one that isn't
  `NotImplementedError` there, per docs/plans/2026-07-30-phase1-diagnostic-core.md).
  Scheduling the PostgreSQL-only ticks for SQL Server would spend every
  cadence catching-and-logging the same NotImplementedError instead of
  reporting the gap once at registration time.
- Instance membership is polled (not push-based) every
  `instance_refresh_interval_seconds` (default 5 min) -- newly registered or
  deactivated instances are picked up/torn down without restarting the
  scheduler process. 5 minutes is an operational default, not a correctness
  requirement (registering an instance isn't time-sensitive the way sampling
  is).
- Partition maintenance runs on its own global loop (not per-instance --
  `ensure_daily_partitions`/`drop_expired_partitions` operate on the shared
  fact tables, independent of which instances exist).
- A single `asyncio.Event` per running instance is the cancellation
  mechanism: setting it and awaiting the instance's task is how both
  per-instance teardown (deactivated instance) and full shutdown work,
  rather than `Task.cancel()` racing a tick's own cleanup.
"""

from __future__ import annotations

import asyncio
import functools
import logging
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from . import repository
from .collector import run_query_stats_collection, run_session_sample_collection, run_trivial_collection
from .engine_adapter import Engine
from .rollups import run_ash_1h_rollup, run_ash_1m_rollup, run_query_stat_1h_rollup

logger = logging.getLogger(__name__)

_DEFAULT_INSTANCE_REFRESH_INTERVAL_SECONDS = 300.0
_DEFAULT_PARTITIONS_MAINTAIN_INTERVAL_SECONDS = 3600.0


@dataclass(frozen=True, slots=True)
class TickSpec:
    name: str
    interval_seconds: float
    fn: Callable[[str], Awaitable[Any]]


# interval_ms passed explicitly (matching interval_seconds) rather than
# relying on each function's own default -- ADR §4's "interval_ms is data,
# not a constant" discipline applies here too: the scheduler is the one
# place that decides real-world cadence, so it should say so, not assume.
_POSTGRES_ONLY_TICKS: tuple[TickSpec, ...] = (
    TickSpec("session_sample", 1.0, functools.partial(run_session_sample_collection, interval_ms=1_000)),
    TickSpec("query_stats", 60.0, functools.partial(run_query_stats_collection, interval_ms=60_000)),
    TickSpec("rollup_ash_1m", 60.0, run_ash_1m_rollup),
    TickSpec("rollup_ash_1h", 300.0, run_ash_1h_rollup),
    TickSpec("rollup_query_stat_1h", 300.0, run_query_stat_1h_rollup),
)
_UNIVERSAL_TICKS: tuple[TickSpec, ...] = (TickSpec("trivial", 60.0, functools.partial(run_trivial_collection, interval_ms=60_000)),)


def _ticks_for_engine(engine: Engine) -> tuple[TickSpec, ...]:
    if engine == Engine.POSTGRESQL:
        return _UNIVERSAL_TICKS + _POSTGRES_ONLY_TICKS
    return _UNIVERSAL_TICKS


def _log_tick_result(instance_id: str, tick_name: str, result: Any) -> None:
    """Best-effort structured log line. Tick result shapes differ (collector
    results have status/gap fields, RollupResult doesn't) -- duck-typed so
    this doesn't need a case per result class."""
    status = getattr(result, "status", None)
    if status == "error":
        logger.warning("monitoring tick error instance=%s tick=%s error=%s", instance_id, tick_name, getattr(result, "error_message", None))
        return
    if getattr(result, "gap_detected", False):
        logger.warning("monitoring tick gap instance=%s tick=%s gap_seconds=%s", instance_id, tick_name, getattr(result, "gap_seconds", None))
        return
    logger.debug("monitoring tick ok instance=%s tick=%s result=%r", instance_id, tick_name, result)


async def _run_periodic_tick(instance_id: str, spec: TickSpec, *, stop_event: asyncio.Event) -> None:
    """Run `spec.fn(instance_id)` immediately, then every `interval_seconds` until stopped.

    `asyncio.wait_for(stop_event.wait(), timeout=...)` doubles as the sleep:
    a stop mid-interval returns within this call instead of waiting out a
    stale interval (matters most for the 1s session-sample tick -- a 1
    minute rollup tick blocking shutdown for up to a minute would be a much
    smaller deal than session_sample doing the same, but neither should
    happen).
    """
    while not stop_event.is_set():
        try:
            result = await spec.fn(instance_id)
            _log_tick_result(instance_id, spec.name, result)
        except Exception:  # a tick's own try/except already covers "instance unreachable" -- this is the backstop for genuine bugs
            logger.exception("monitoring tick raised unexpectedly instance=%s tick=%s", instance_id, spec.name)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=spec.interval_seconds)
        except TimeoutError:
            pass


async def run_instance_forever(instance_id: str, engine: Engine, stop_event: asyncio.Event) -> None:
    ticks = _ticks_for_engine(engine)
    await asyncio.gather(*(_run_periodic_tick(instance_id, spec, stop_event=stop_event) for spec in ticks))


async def _run_partitions_maintenance_loop(*, stop_event: asyncio.Event, interval_seconds: float) -> None:
    from app.core.database import engine as db_engine

    from .partitions import maintain_all_partitions

    while not stop_event.is_set():
        try:
            async with db_engine.begin() as conn:
                results = await maintain_all_partitions(conn)
            total_created = sum(len(r.created) for r in results)
            total_dropped = sum(len(r.dropped) for r in results)
            logger.info("partitions maintenance: created=%d dropped=%d", total_created, total_dropped)
        except Exception:
            logger.exception("partitions maintenance failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except TimeoutError:
            pass


@dataclass(slots=True)
class _RunningInstance:
    task: asyncio.Task[None]
    stop_event: asyncio.Event


@dataclass(slots=True)
class Scheduler:
    """Owns instance membership (poll-refreshed) and per-instance tick loops.

    `run()` blocks until `stop()` is called (typically from a signal
    handler) or it's cancelled; either way every running instance loop and
    the partition-maintenance loop are stopped and awaited before `run()`
    returns, so no task is left dangling on shutdown.
    """

    instance_refresh_interval_seconds: float = _DEFAULT_INSTANCE_REFRESH_INTERVAL_SECONDS
    partitions_maintain_interval_seconds: float = _DEFAULT_PARTITIONS_MAINTAIN_INTERVAL_SECONDS
    # Coroutine, not the broader Awaitable -- these get passed to
    # asyncio.create_task(), which requires a Coroutine specifically.
    run_instance: Callable[[str, Engine, asyncio.Event], Coroutine[Any, Any, None]] = field(default=run_instance_forever)
    list_instances: Callable[[], Awaitable[list[Any]]] = field(default=repository.list_instances)
    # Injectable so tests don't need a real database connection just to
    # verify the scheduler starts/stops this loop correctly.
    partitions_maintenance_loop: Callable[..., Coroutine[Any, Any, None]] = field(default=_run_partitions_maintenance_loop)
    # `slots=True` only generates slots for declared fields, so these need
    # to be fields too (not plain __post_init__ attributes) to be settable.
    _running: dict[str, _RunningInstance] = field(default_factory=dict, init=False, repr=False)
    _stop_event: asyncio.Event = field(default_factory=asyncio.Event, init=False, repr=False)

    def stop(self) -> None:
        self._stop_event.set()

    async def run(self) -> None:
        partitions_stop = asyncio.Event()
        partitions_task = asyncio.create_task(self.partitions_maintenance_loop(stop_event=partitions_stop, interval_seconds=self.partitions_maintain_interval_seconds))

        try:
            while not self._stop_event.is_set():
                await self._sync_instances()
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self.instance_refresh_interval_seconds)
                except TimeoutError:
                    pass
        finally:
            for instance_id in list(self._running):
                await self._stop_instance(instance_id)
            partitions_stop.set()
            await partitions_task

    async def _sync_instances(self) -> None:
        instances = await self.list_instances()
        active_ids = {inst.id for inst in instances if inst.is_active}

        for instance_id in list(self._running):
            if instance_id not in active_ids:
                logger.info("monitoring scheduler: stopping instance=%s (deactivated or removed)", instance_id)
                await self._stop_instance(instance_id)

        for inst in instances:
            if inst.is_active and inst.id not in self._running:
                logger.info("monitoring scheduler: starting instance=%s engine=%s", inst.id, inst.engine.value)
                self._start_instance(inst.id, inst.engine)

    def _start_instance(self, instance_id: str, engine: Engine) -> None:
        stop_event = asyncio.Event()
        task = asyncio.create_task(self.run_instance(instance_id, engine, stop_event))
        self._running[instance_id] = _RunningInstance(task=task, stop_event=stop_event)

    async def _stop_instance(self, instance_id: str) -> None:
        running = self._running.pop(instance_id)
        running.stop_event.set()
        await running.task
