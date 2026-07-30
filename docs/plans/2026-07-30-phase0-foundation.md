# Plan: Faza 0 — fundament domenowy (elementy 5–9)

**Data:** 2026-07-30 · **Status:** `in progress`
**Kontekst:** [roadmap.md](../roadmap.md) §3 (Faza 0) · [ADR modelu danych](../research/2026-07-30-data-model.md)
**Blokował:** elementy 4–9 Fazy 0 były oznaczone `❌ nie rozpoczęte` w tabeli stanu roadmapy

## Zakres tej iteracji

Kolejność z ADR §11: *migracje wymiarów → migracje faktów + zadanie utrzymania
partycji → `EngineAdapter` z wykrywaniem `capabilities` → `collector_run` z
pomiarem narzutu → trywialny kolektor → rollupy z watermarkiem*. Zrealizowano
wszystko poza rollupami (patrz „Co zostaje" niżej).

### Zrobione

| # | Element | Gdzie |
|---|---|---|
| 6 | Model danych — wymiary + fakty partycjonowane dziennie | `backend/migrations/068_create_monitoring_dimensions.py`, `069_create_monitoring_facts.py` |
| 6 | Zadanie utrzymania partycji (create-ahead + drop-po-retencji, `DROP TABLE`, nie `DELETE`) | `backend/app/modules/monitoring/partitions.py`, `cli monitoring partitions-maintain` |
| 5 | `EngineAdapter` — interfejs + dwie implementacje (połączenie, wykrywanie capabilities) | `backend/app/modules/monitoring/engine_adapter.py`, `adapters/postgres_adapter.py`, `adapters/sqlserver_adapter.py` |
| 4 | Poświadczenia monitorowanych instancji szyfrowane (Fernet, klucz tylko w env) | `backend/app/modules/monitoring/crypto.py` |
| 8 | `collector_run` z pomiarem narzutu, offsetem zegara, jawnym oznaczaniem luk | `backend/app/modules/monitoring/collector.py` |
| 5/8 | Trywialny kolektor (zapisuje `instance_metric` + `collector_run`) | `cli monitoring collect` |
| 9 | Wykrywanie capabilities (rozszerzenia, `pg_monitor` / `VIEW SERVER STATE`) | `cli monitoring detect-capabilities` |

CLI: `cli monitoring register-instance / list-instances / detect-capabilities / collect / partitions-maintain`.

### Walidacja

Testy jednostkowe (`backend/tests/modules/monitoring/`, 21 testów, mockowane
`asyncpg`/`pytds`/połączenia) plus **walidacja ręczna end-to-end na lokalnym
PostgreSQL 16** (brak dockera w tym środowisku, więc `docker compose up` nie
było dostępne — użyto `postgresql-16` z apt):

- `cli db migrate` na czystej bazie: migracje 068+069 przechodzą, downgrade też (round-trip sprawdzony)
- insert do `session_sample` trafia we właściwą partycję dnia (`tableoid` sprawdzony)
- `ensure_daily_partitions` / `drop_expired_partitions`: partycja z 2020-01-01 utworzona i poprawnie usunięta jako przeterminowana
- pełny cykl CLI: `register-instance` → `detect-capabilities` (wykryto `pg_monitor`, brak `pg_stat_statements`/`pg_wait_sampling`/`hypopg` na czystej instalacji) → `collect` (zapisał `instance_metric` + `collector_run`, `overhead_ms`/`clock_offset_ms` policzone) → druga `collect` po 6 s przy `--interval-ms 5000` poprawnie oznaczyła `gap_detected`

Raw-DDL migracje (partycjonowanie deklaratywne) nie dają się uruchomić pod
istniejącym `tests/conftest.py`, który wymusza SQLite dla całego pytest suite
— to ograniczenie istniało już dla migracji 067 i wcześniejszych, nie jest
nowe w tej iteracji.

### Efekt uboczny: naprawiony martwy import blokujący CI

`app/api/router.py` importował `app.modules.logs.router`, moduł którego nigdy
nie było w tym repo (boilerplate skopiował referencję bez samego modułu —
ten sam rodzaj długu co [issue 001](../issues/2026-07-30--001--boilerplate-dead-code-cleanup.md)).
To wywalało `create_app()`, więc **cały `pytest` był czerwony na `develop`**
mimo że roadmapa i CLAUDE.md zakładały zielone CI — potwierdzone przez
faktyczny stan workflow (`Pytest (testy)` na commitcie `9b10ab0` = `failure`).
Naprawiono usuwając martwy import/route; patrz [issue 004](../issues/2026-07-30--004--dead-logs-import-broke-ci-pytest.md).

## Iteracja 2026-07-30 (b): dokumentacja grantów + FAQ licencyjne

Dwa z czterech pozostałych punktów poniżej domknięte bez zmian w kodzie
domenowym:

- **Dokumentacja minimalnych grantów per silnik** (roadmap element 9, druga połowa) — [docs/grants.md](../grants.md): `CREATE ROLE` + `GRANT pg_monitor` dla PostgreSQL, `CREATE LOGIN`/`CREATE USER` + `GRANT VIEW SERVER STATE`/`VIEW DATABASE STATE` dla SQL Server, plus tabela rozszerzeń opcjonalnych (`pg_stat_statements`/`pg_wait_sampling`/`hypopg`) i krok weryfikacji przez `cli monitoring detect-capabilities`. Treść oparta bezpośrednio na `_RELEVANT_ROLES`/`_RELEVANT_PERMISSIONS` z adapterów, żeby nie rozjechać się z kodem.
- **FAQ licencyjne** (roadmap element 2, wymóg §6 vision) — [docs/licensing-faq.md](../licensing-faq.md): użycie wewnętrzne (nawet zmodyfikowane) nie rodzi obowiązku publikacji; scenariusz MSP/hostingu dla klientów aktywuje klauzulę sieciową; split licencyjny CLI/SDK/MCP jawnie oznaczony jako nierozstrzygnięty ADR, nie fakt.

`docs/roadmap.md` §3 zaktualizowane (oba wiersze z ❌/🟡 na ✅).

## Co zostaje

- **Rollupy 1 min/1 h z watermarkiem i top-N+other** (ADR §6, roadmap element 7) — nie zaczęte. Wymaga danych z realnego samplera (Faza 1) żeby sensownie przetestować kardynalność; szkielet tabel faktów jest gotowy pod to.
- **Walidacja `SqlServerEngineAdapter` na żywej instancji SQL Server** — brak dostępnego SQL Servera w tym środowisku i w CI. Logika DMV/`HAS_PERMS_BY_NAME` jest napisana i pokryta testami z mockami, ale nieprzetestowana end-to-end. Ryzyko: nazwy kolumn/typy zwracane przez `pytds` mogą się różnić od założeń.
- **Harmonogram/scheduler** dla kolektora — dziś uruchamiany ręcznie przez CLI (`cli monitoring collect`), nie ma jeszcze pętli/cron w aplikacji. Roadmap Faza 0 element 8 mówi o "harmonogramie" jako części runtime'u kolektora; to zostaje do momentu, gdy jest więcej niż jedna instancja do obsługi w praktyce.
- ~~CI: `Frontend` → `Type check` czerwony na `develop`~~ — poza pierwotnym zakresem tej iteracji, ale naprawione przy okazji ([issue 005](../issues/2026-07-30--005--frontend-typecheck-red-on-develop.md)): brakujący `src/lib/` (`cn`, `copyToClipboard`, `valueUpdater`) i `requiresTwoFactorVerification`.

## Powiązane

- [roadmap.md](../roadmap.md) §3 (Faza 0) — tabela stanu zaktualizowana
- [ADR modelu danych](../research/2026-07-30-data-model.md)
- [backend/migrations/README.md](../../backend/migrations/README.md)
