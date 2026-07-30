# Plan: Faza 1 — rdzeń diagnostyczny, slice PostgreSQL (elementy 1–2)

**Data:** 2026-07-30 · **Status:** `in progress`
**Kontekst:** [roadmap.md](../roadmap.md) §4 (Faza 1) · [ADR modelu danych](../research/2026-07-30-data-model.md)
**Poprzednik:** [plan Fazy 0 — fundament domenowy](2026-07-30-phase0-foundation.md) (`in progress`, blokery zewnętrzne: brak SQL Servera, rollupy czekają na dane z tego planu)

## Dlaczego ten zakres

Faza 0 ma trzy pozostałe punkty, wszystkie zablokowane z przyczyn zewnętrznych
(brak SQL Servera w tym środowisku, świadomie odłożony harmonogram) — poza
jednym: **rollupy (element 7) explicite czekają na realne dane z samplera
Fazy 1**, nie na nic innego. Rozpoczęcie Fazy 1 przed formalnym zamknięciem
Fazy 0 jest więc uzasadnionym wyjątkiem od reguły sekwencyjności (§0
roadmapy), bo element 7 Fazy 0 i element 1 Fazy 1 są tym samym blokerem.

Zakres tej iteracji: **PostgreSQL, elementy 1 (sampler aktywnych sesji) i 2
(top queries)**, budowane razem — nie osobno. ADR §5/§10 wymaga, żeby
tożsamość zapytania (`query.norm_hash`) pochodziła z tego, co silnik już
znormalizował (`pg_stat_statements`), nie z surowego tekstu
`pg_stat_activity`. Budowa samplera bez kolektora statystyk zapytań
najpierw dałaby błędną atrybucję zapytań, którą trzeba by potem przerabiać —
dokładnie koszt, przed którym ostrzega ADR. SQL Server zostaje na
kolejną iterację (ten sam wzorzec co adaptery Fazy 0 — `NotImplementedError`,
jawnie zadeklarowany brak wsparcia, nie cichy brak funkcji).

## Zrobione

| # | Element | Gdzie |
|---|---|---|
| — | Migracja 070: `query_stat_cursor` (kursor kumulatywnych liczników per zapytanie) + `collector_run.kind` (rozróżnienie tick'ów trivial/session_sample/query_stats, bo mieszanie ich gap-detection przy różnych kadencjach fałszywie wykrywałoby luki) | `backend/migrations/070_create_query_stat_cursor_and_collector_kind.py` |
| 1 | `EngineAdapter.collect_active_sessions` — PostgreSQL: `pg_stat_activity WHERE state = 'active'`, wait attribution (`wait_event_type:wait_event`), `query_id` gdy dostępny (fallback bez kolumny na starszych/niezkonfigurowanych instancjach) | `backend/app/modules/monitoring/adapters/postgres_adapter.py` |
| 2 | `EngineAdapter.collect_query_stats` — PostgreSQL: `pg_stat_statements` (cumulative), pusta lista gdy rozszerzenie niezainstalowane (nigdy błąd) | tamże |
| 1/2 | SQL Server: `collect_active_sessions`/`collect_query_stats` jawnie `NotImplementedError` z odnośnikiem do tego planu | `backend/app/modules/monitoring/adapters/sqlserver_adapter.py` |
| 1 | Kolektor: `run_session_sample_collection` — rozwiązywanie tożsamości zapytania (natywny klucz → istniejący `query` → interim upsert), `session_attr` upsert, `ensure_wait_event` (nieznany wait → `other`, nie blokuje zbierania), zapis `session_sample` | `backend/app/modules/monitoring/collector.py` |
| 2 | Kolektor: `run_query_stats_collection` — delta względem `query_stat_cursor` (`max(0, current - previous)`, przetrwa reset statystyk), pierwsze wystąpienie zapytania tylko ustanawia kursor bez zapisu delty | tamże |
| — | Repozytorium: `upsert_query`, `find_query_id_by_engine_key`, `ensure_wait_event`, `upsert_session_attr`, `insert_session_sample`, `get_query_stat_cursor`/`upsert_query_stat_cursor`, `insert_query_stat_delta`, `normalize_query_text`/`compute_norm_hash` | `backend/app/modules/monitoring/repository.py` |

CLI: `cli monitoring sample-sessions <instance-id>` / `cli monitoring
collect-query-stats <instance-id>`.

## Walidacja

Testy jednostkowe (mockowane `asyncpg`, 31 testów w
`backend/tests/modules/monitoring/`) plus **walidacja ręczna end-to-end na
lokalnym PostgreSQL 16** (self-monitoring: instancja `pulse_db` monitoruje
samą siebie, `pg_stat_statements` włączone przez `shared_preload_libraries`):

- `cli db migrate`: migracja 070 przechodzi, downgrade→upgrade round-trip sprawdzony ręcznie (kolumna `kind` + tabela `query_stat_cursor` znikają i wracają poprawnie)
- `register-instance` → `detect-capabilities`: `pg_monitor: True` na koncie z samym grantem z [docs/grants.md](../grants.md) — potwierdza, że dokumentacja grantów jest wystarczająca w praktyce
- `collect-query-stats` uruchomiony dwukrotnie: pierwszy przebieg — 123 zapytania widziane, 0 delt (ustanowienie kursora); drugi przebieg po wygenerowaniu ruchu — 128 widzianych, 12 delt zapisanych z poprawną różnicą względem kursora
- **Scenariusz blokady na żywo**: sesja A trzyma blokadę wiersza (`UPDATE ... pg_sleep(8)`), sesja B czeka na tę samą blokadę; `sample-sessions` w trakcie poprawnie złapał obie: sesja B na `Lock:transactionid` (zaseedowany wait, poprawna klasyfikacja), sesja A na `Timeout:PgSleep` (**nieznany** wait, auto-zarejestrowany w `wait_event` jako klasa `other`, `is_idle=false`, próbka mimo to zapisana) — bezpośrednie potwierdzenie reguły ADR §5 "nieznany wait nie psuje zbierania"
- `query_stat_delta` zjoinowany przez `query`/`query_text` do czytelnego tekstu zapytania — potwierdza dwupoziomową tożsamość z ADR §5 działa end-to-end

## Co zostaje

- **SQL Server, elementy 1–2** — ten sam wzorzec co PostgreSQL (DMV
  `sys.dm_exec_requests`/`sys.dm_os_waiting_tasks` dla sesji,
  `sys.dm_exec_query_stats`/Query Store dla statystyk), niezaimplementowane.
  Blokowane tym samym brakiem dostępnej instancji co walidacja adaptera w
  Fazie 0.
- **`pg_wait_sampling` jako opcjonalne źródło wyższej jakości** (zamiast
  samego `pg_stat_activity`) — capability już wykrywana, ale sampler jej
  jeszcze nie używa.
- **Ciągła pętla / harmonogram 1 s** — dziś `sample-sessions` to pojedynczy
  tick przez CLI, tak jak trywialny kolektor. Kryterium wyjścia z Fazy 1
  ("sampler pracuje 7 dni bez przerwy") wymaga schedulera, którego jeszcze
  nie ma (roadmap Faza 0 element 8, świadomie odłożony) — nie da się go też
  zweryfikować w efemerycznym środowisku tej sesji.
- **Elementy 3–7 Fazy 1** (plany wykonania, blokady/deadlocki jako
  zdarzenia, indeksy, baseline) — nie zaczęte.
- **Rollupy Fazy 0 (element 7)** — teraz odblokowane danymi z tej iteracji
  (`session_sample`/`query_stat_delta` mają realne wiersze), ale wciąż
  nie zaimplementowane; naturalny następny krok.

## Powiązane

- [roadmap.md](../roadmap.md) §4 (Faza 1) — tabela stanu zaktualizowana
- [plan Fazy 0 — fundament domenowy](2026-07-30-phase0-foundation.md)
- [ADR modelu danych](../research/2026-07-30-data-model.md) §5 (tożsamość zapytania, reguła poprawności waitów), §10 (ryzyko normalizacji)
- [docs/grants.md](../grants.md) — grant `pg_monitor` zweryfikowany jako wystarczający w tej iteracji
