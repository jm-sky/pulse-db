# Plan: Faza 1 element 3 — plany wykonania + detekcja zmiany

**Data:** 2026-08-05 · **Status:** `in progress`
**Kontekst:** [roadmap.md](../roadmap.md) §4 (Faza 1 element 3) · [ADR modelu danych](../research/2026-07-30-data-model.md) §3
**Poprzednik:** [plan Fazy 1 — rdzeń diagnostyczny](2026-07-30-phase1-diagnostic-core.md)

## Dlaczego ten zakres

Roadmapa: *plany wykonania: pobieranie, przechowywanie, detekcja zmiany planu*.
Wymiary `plan_text` / `query_plan` istnieją od migracji 068 — nowy wiersz
`(query_id, plan_hash)` **jest** zdarzeniem zmiany planu (ADR §3). Bez
własnego wizualizatora (vision §5): XML/JSON + eksport API.

## Zrobione

| Element | Gdzie |
|---------|-------|
| `QueryPlanRow` + `EngineAdapter.collect_query_plans` | `engine_adapter.py` |
| PostgreSQL: TOP-N + `EXPLAIN (FORMAT JSON)` (nigdy ANALYZE); skip per-query errors | `adapters/postgres_adapter.py` |
| SQL Server: TOP-N + `CROSS APPLY dm_exec_query_plan` (jeden batch) | `adapters/sqlserver_adapter.py` |
| Migracja 073: `collector_run.kind = query_plans` | `migrations/073_add_query_plans_collector_kind.py` |
| `upsert_plan_text` / `upsert_query_plan` / odczyty API | `repository.py` |
| `run_query_plans_collection` | `collector.py` |
| Scheduler tick 10 min | `scheduler.py` |
| CLI `collect-query-plans` | `cli/commands/monitoring.py` |
| API: list plans, plan body, plan-changes | `router.py`, `schemas.py` |

## API

- `GET /api/monitoring/instances/{id}/queries/{query_id}/plans`
- `GET /api/monitoring/instances/{id}/queries/{query_id}/plans/{plan_hash}`
- `GET /api/monitoring/instances/{id}/queries/plan-changes?since=`

## Walidacja

Testy jednostkowe w `backend/tests/modules/monitoring/test_query_plans.py`
(+ zaktualizowany zestaw ticków w `test_scheduler.py`).

## Co zostaje

- Live E2E na lokalnym PG + S2017 (nie BSM-SQL13)
- Query Store jako źródło historii planów
- UI / wizualizator / alerty na zmianę planu

## Powiązane

- [docs/grants.md](../grants.md) — opcjonalny SELECT pod EXPLAIN (PostgreSQL)
- [sql-monitor](../../../sql-monitor) — wzorzec `dm_exec_query_plan` (u nas batch, nie N RTT)
