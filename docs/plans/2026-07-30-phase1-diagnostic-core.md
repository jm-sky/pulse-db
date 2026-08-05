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
| 1/2 | SQL Server: `collect_active_sessions`/`collect_query_stats` — początkowo `NotImplementedError`; zaimplementowane w iteracji 2026-08-05 | `adapters/sqlserver_adapter.py` |
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

## Iteracja 2026-07-30 (b): `pg_wait_sampling` jako opcjonalne źródło wyższej jakości

Roadmap element 1 explicite: *"PostgreSQL: `pg_stat_activity` domyślnie,
`pg_wait_sampling` opcjonalnie gdy obecne, **z komunikatem o różnicy
jakości**"*. Zaimplementowane jako osobna, **świadomie opt-in** ścieżka —
nie jako domyślne zachowanie `sample-sessions` — z konkretnego,
zmierzonego powodu (patrz niżej), nie z ostrożności.

### Co zbadano przed implementacją

Zainstalowano `postgresql-16-pg-wait-sampling` lokalnie i zmierzono
zachowanie rozszerzenia na realnej instancji:

- `pg_wait_sampling_history` próbkuje **każdy backend** (włącznie z
  `autovacuum launcher`, `checkpointer`, `walwriter`, `logical replication
  launcher`) co `pg_wait_sampling.history_period` (domyślnie **10 ms**), nie
  tylko sesje klienckie. Na niemal bezczynnej instancji: **~628
  wierszy/s** z samych procesów tła przy zaledwie 9 różnych pidów.
- Sesja aktywna przez pełną 1 s między dwoma tickami naszego pollera daje
  **~100 próbek** z historii kontra **1 próbkę** z podejścia poll-based —
  100× więcej danych dla tej samej sekundy aktywności.
- Backend nieobecny w danym momencie w `pg_wait_sampling_current`/`_history`
  = na CPU (nie czeka) — ten sam konwencja co `NULL wait_event` w
  `pg_stat_activity`, potwierdzone empirycznie (własna sesja psql
  wykonująca zapytanie nie pojawiła się w `pg_wait_sampling_current`).

To bezpośrednio dotyka budżetu wolumenu z ADR §10 ("Estymaty wolumenu są
🟡, nieoparte na pomiarze") — surowe wpisanie całej historii jako
`session_sample` pomnożyłoby wolumen ~100× ponad założenie ADR (~90
wierszy/s przy 30 instancjach), bez świadomej zgody operatora. Stąd:
filtrowanie do `backend_type = 'client backend'` (usuwa szum procesów tła)
**i** osobna, jawnie opcjonalna komenda zamiast cichej zmiany domyślnego
zachowania.

### Zrobione

| # | Element | Gdzie |
|---|---|---|
| — | Migracja 071: `wait_sampling_cursor` (watermark per instancja) + `collector_run.kind` rozszerzone o `wait_sampling_history` | `backend/migrations/071_add_wait_sampling_history_source.py` |
| 1 | `PostgresEngineAdapter.collect_wait_sampling_history` — `pg_wait_sampling_history` zjoinowany z bieżącym `pg_stat_activity` po `pid` (kontekst sesji: user/app/client/tekst zapytania), filtr `backend_type = 'client backend'`, zwraca też zmierzony `history_period_ms` i najstarszy `ts` wciąż w ring-bufferze (do wykrywania utraty danych) | `backend/app/modules/monitoring/adapters/postgres_adapter.py` |
| 1 | Kolektor: `run_wait_sampling_history_collection` — watermark zamiast stałego interwału (bo brak stałej kadencji wywołań), `interval_ms` na wierszu = **zmierzony** `history_period_ms` silnika (ADR §4 rygorystycznie, nie nasze domyślne 1000ms), korekta `sampled_at` o `clock_offset_ms` (ADR §9), wykrywanie "ring buffer overrun" gdy najstarszy dostępny `ts` przeskoczył nasz watermark | `backend/app/modules/monitoring/collector.py` |
| — | Repozytorium: `get_wait_sampling_watermark`/`set_wait_sampling_watermark`, `get_latest_clock_offset_ms` | `backend/app/modules/monitoring/repository.py` |

CLI: `cli monitoring sample-wait-history <instance-id>` — drukuje jawną
notatkę o różnicy jakości/wolumenu przy każdym uruchomieniu (dosłowna
realizacja "z komunikatem o różnicy jakości" z roadmapy).

### Walidacja

Testy jednostkowe (mockowane `asyncpg`/repozytorium, +6 testów) plus
**walidacja end-to-end na lokalnym PostgreSQL 16** z zainstalowanym i
załadowanym (`shared_preload_libraries`) `pg_wait_sampling`:

- `detect-capabilities` poprawnie raportuje `pg_wait_sampling: True` po instalacji
- migracja 071 przechodzi; downgrade **poprawnie odmówił** zawężenia `collector_run_kind_check` w obecności realnych wierszy `kind='wait_sampling_history'` (`CheckViolationError`, cała transakcja wycofana atomowo — `wait_sampling_cursor` nie zniknęło mimo błędu w drugiej instrukcji) — to jest poprawne zachowanie ochronne, nie defekt
- scenariusz blokady na żywo + `sample-wait-history`: 6 próbek, 1 sesja, `history_period_ms=10`, notatka o jakości wydrukowana; drugie uruchomienie: kolejne 6 nowych próbek (12 łącznie, **bez duplikatów** — watermark poprawnie się przesunął) **i** poprawnie wykryty "ring buffer overrun" (~12,4 s luki, bo 5000-wierszowy bufor przy próbkowaniu wszystkich procesów tła rolluje się w ciągu sekund, nie minut)
- ograniczenie udokumentowane, nie ukryte: `INNER JOIN` do bieżącego `pg_stat_activity` po `pid` pomija próbki dla sesji, które już się rozłączyły do czasu odczytu — zaobserwowane wprost (syntetyczna sesja blokady rozłączyła się zanim `sample-wait-history` zdążyło przeczytać jej próbki z historii)

## Iteracja 2026-08-05: SQL Server, elementy 1–2

Zewnętrzny bloker (brak żywej instancji) odpadł — do walidacji używamy
wyłącznie **S2017 / Portal Test** (`10.171.173.212:1436`, `app_db_test`).
**BSM-SQL13 to produkcja — nie rejestrować, nie uruchamiać kolektora.**

### Zrobione

| # | Element | Gdzie |
|---|---|---|
| 1 | `SqlServerEngineAdapter.collect_active_sessions` — `dm_exec_requests` + `dm_exec_sessions` + `dm_exec_sql_text`, filtr `is_user_process = 1` (bez niego ASH to prawie wyłącznie background na `DISPATCHER_QUEUE_SEMAPHORE` itd.), flat `wait_type` jako `wait_event` (bez `Type:Event` — zgodne z seedami migracji 068), `query_hash` jako `engine_query_key` | `adapters/sqlserver_adapter.py` |
| 2 | `SqlServerEngineAdapter.collect_query_stats` — `dm_exec_query_stats` cumulative (mikrosekundy → ms), filtr do `DB_ID()`, Query Store wykrywany jako capability ale nie jest źródłem MVP (ten sam kształt cumulative→delta co PG) | tamże |
| — | Collector: `_wait_event_native_name` obsługuje flat SQL Server + hierarchical PG; `session.rollback()` po błędzie ticku (żeby `insert_collector_run` nie padał na aborted transaction) | `collector.py` |
| — | Scheduler: SQL Server dostaje pełny zestaw ticków diagnostycznych (nie tylko `trivial`) | `scheduler.py` |
| — | Sanitizacja NUL w tekstach zapytań (`dm_exec_sql_text` cursor API) — bez tego PostgreSQL odrzucał UTF-8 (`CharacterNotInRepertoireError`, potwierdzone na BSM-SQL13) | `repository.normalize_query_text` + adapter |

### Walidacja

Testy jednostkowe (mockowane `pytds`, suite monitoring zielony) plus **walidacja end-to-end na żywych instancjach**:

- **S2017 (Portal Test)** — jedyna dozwolona instancja SQL Server do walidacji
  deweloperskiej (`app_db_test`, `10.171.173.212:1436`). `detect-capabilities`
  / `collect` / `sample-sessions` / `collect-query-stats` zweryfikowane.
- **BSM-SQL13 — NIE używać do walidacji PulseDB.** To baza **produkcyjna**
  (`app_portal_01`). Przez pomyłkę zarejestrowano ją w sesji 2026-08-05 i
  uruchomiono kilka ticków diagnostycznych — instancja została natychmiast
  dezaktywowana (`is_active = false`). Kolejne testy wyłącznie na S2017.

## Iteracja 2026-08-05 (b): element 6 — porównanie okresów (baseline poziom 1)

Roadmap element 6: *porównanie okresów / regresja zapytania* — czyste SQL nad
rollupami, które już są (vision §5 poziom 1).

### Zrobione

| # | Element | Gdzie |
|---|---|---|
| 6 | Porównanie okresów per zapytanie — agregacja `query_stat_1h` w dwóch oknach, delty `avg_time_ms`/calls/total, flaga `is_regression` | `period_comparison.py` + `repository.py` |
| 6 | Podsumowanie instancji + wait-class z `query_stat_1h`/`ash_1h` | tamże |
| 6 | API: `GET /api/monitoring/instances/{id}/queries/period-comparison`, `GET .../period-comparison/summary` + OpenAPI | `router.py`, `schemas.py`, `api/router.py` |
| — | Testy jednostkowe (logika merge, mocki repozytorium, kontrakt API) | `tests/modules/monitoring/test_period_comparison.py` |

### Walidacja

Testy jednostkowe (mockowane repozytorium, 9 testów) plus **walidacja E2E na
lokalnym PostgreSQL 16** — `verification needed` (wymaga uruchomionego
środowiska z historią rollupów).

## Co zostaje

- **Elementy 4–5, 7 Fazy 1** (blokady/deadlocki jako
  zdarzenia, indeksy, baseline sezonowy percentylowy) — nie zaczęte.
- **Element 3 (plany)** — ✅ zaimplementowane; szczegóły:
  [2026-08-05-query-plans.md](2026-08-05-query-plans.md).
- **Query Store jako źródło historii poza plan cache** — capability
  wykrywane, kolektor nadal na `dm_exec_query_stats` (jak
  `pg_stat_statements`). Osobna decyzja / iteracja.
- **Automatyczne przełączanie na `pg_wait_sampling`** gdy obecne — dziś
  celowo opt-in (osobna komenda), nie domyślne zachowanie
  `sample-sessions`, z powodów wolumenu opisanych wyżej. Ewentualne
  domyślne włączenie wymagałoby decyzji o budżecie retencji/wolumenu, nie
  tylko kodu.
- **Sesje, które rozłączyły się między próbką historii a odczytem**
  (`pg_wait_sampling`) — tracone (`INNER JOIN` do bieżącego
  `pg_stat_activity`), udokumentowane ograniczenie, nie naprawione.
- **Kryterium wyjścia Fazy 1** („sampler pracuje 7 dni bez przerwy" na
  obu silnikach) — scheduler istnieje; wymaga ciągłego uruchomienia, nie
  weryfikowalne w jednej sesji.

## Powiązane

- [roadmap.md](../roadmap.md) §4 (Faza 1) — tabela stanu zaktualizowana
- [plan Fazy 0 — fundament domenowy](2026-07-30-phase0-foundation.md)
- [ADR modelu danych](../research/2026-07-30-data-model.md) §5 (tożsamość zapytania, reguła poprawności waitów), §10 (ryzyko normalizacji)
- [docs/grants.md](../grants.md) — grant `pg_monitor` zweryfikowany jako wystarczający w tej iteracji
