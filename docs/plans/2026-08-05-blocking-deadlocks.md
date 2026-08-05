# Plan: Faza 1 element 4 — blokady i deadlocki

**Data:** 2026-08-05 · **Status:** `in progress`
**Kontekst:** [roadmap.md](../roadmap.md) §4 (Faza 1 element 4) · [ADR modelu danych](../research/2026-07-30-data-model.md) §3
**Poprzednik:** [plan planów wykonania](2026-08-05-query-plans.md)

## Dlaczego ten zakres

Roadmapa: *blokady i deadlocki*. Fakty `blocking_event` / `deadlock_event`
istnieją od migracji 069. SQL Server ma zero-cost źródło historii deadlocków
(`system_health`); PostgreSQL w MVP ma pełny **blocking**, historię deadlocków
— jawny brak (brak ring-buffera bez parsowania logów).

## Zrobione

| Element | Gdzie |
|---------|-------|
| `BlockingRow` / `DeadlockRow` + adapter methods | `engine_adapter.py` |
| PG: `pg_locks` × `pg_stat_activity`; deadlocks `[]` | `adapters/postgres_adapter.py` |
| SS: DMV blocking + `system_health` deadlocks | `adapters/sqlserver_adapter.py` |
| Migracja 074: kinds + `deadlock_cursor` | `migrations/074_add_blocking_deadlocks_collector.py` |
| Kolektor + watermark | `collector.py`, `repository.py` |
| Tick 30 s / 60 s | `scheduler.py` |
| CLI `collect-blocking` / `collect-deadlocks` | `cli/commands/monitoring.py` |
| API list + deadlock detail | `router.py`, `schemas.py` |

## API

- `GET /api/monitoring/instances/{id}/blocking?since=`
- `GET /api/monitoring/instances/{id}/deadlocks?since=`
- `GET /api/monitoring/instances/{id}/deadlocks/{event_id}`

## Capability

- PG: `deadlock_history: false`
- SS: `deadlock_history: true` gdy sesja `system_health` obecna

## Powiązane

- [docs/grants.md](../grants.md) — VIEW SERVER STATE wystarcza na odczyt XE ring buffer
- sql-monitor: `collector/queries/blocking.py`, `deadlocks.py`
