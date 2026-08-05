# Plan: Faza 1 element 5 — analiza indeksów z DDL

**Data:** 2026-08-05 · **Status:** `in progress`
**Kontekst:** [roadmap.md](../roadmap.md) §4 (Faza 1 element 5) · [ADR modelu danych](../research/2026-07-30-data-model.md) §3
**Poprzednik:** [plan blokad/deadlocków](2026-08-05-blocking-deadlocks.md)

## Dlaczego ten zakres

Roadmapa: *analiza indeksów z DDL*. Fakty `index_snapshot` / `recommendation`
istnieją od migracji 069. Poziom 1 (vision §5): inwentarz obu silników,
unused (DROP) obu, missing (CREATE) tylko SQL Server DMV. Bez hypopg /
what-if (poziom 2) i bez wykonywania DDL (Faza 3).

## Zrobione

| Element | Gdzie |
|---------|-------|
| `IndexInventoryRow` / `MissingIndexRow` + adapter methods | `engine_adapter.py` |
| PG: `pg_stat_user_indexes`; missing `[]`; `missing_index_dmv: false` | `adapters/postgres_adapter.py` |
| SS: usage + definitions + SAMPLED frag; missing DMV + CREATE DDL | `adapters/sqlserver_adapter.py` |
| Migracja 075: `collector_run.kind = indexes` | `migrations/075_add_indexes_collector_kind.py` |
| Kolektor: snapshot + upsert rekomendacji (dedup `evidence_key`) | `collector.py`, `repository.py` |
| Tick 24 h | `scheduler.py` |
| CLI `collect-indexes` | `cli/commands/monitoring.py` |
| API indexes + recommendations | `router.py`, `schemas.py` |

## API

- `GET /api/monitoring/instances/{id}/indexes` — najnowszy snapshot (`?snapshot_at=` opcjonalnie)
- `GET /api/monitoring/instances/{id}/recommendations?category=&status=open`
- `GET /api/monitoring/instances/{id}/recommendations/{id}`

## Capability

- PG: `missing_index_dmv: false`
- SS: `missing_index_dmv: true`

## Decyzje

| Temat | Wybór |
|-------|-------|
| Kadencja | 24 h |
| Unused | `is_unused` + `unused_index` + DROP (nie PK/unique) |
| Missing | tylko SS |
| Fragmentacja | SS SAMPLED → `bloat_ratio`; PG `NULL` |
| Dedup | upsert po `(instance_id, category, evidence_key)` gdy status `open` |

## Poza zakresem

- hypopg / SQL Server what-if
- DETAILED fragmentation
- `recommendation_outcome` / auto-detekcja wdrożenia
- UI Indexes
- Wykonywanie DDL (Faza 3)

## Powiązane

- [docs/grants.md](../grants.md) — `pg_monitor` / `VIEW DATABASE STATE` wystarczają na odczyt katalogu indeksów
- sql-monitor: `collector/queries/indexes.py`
