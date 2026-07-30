# Analiza istniejącego projektu: `sql-monitor`

**Data:** 2026-07-30
**Status:** done
**Zakres:** `/home/madeyskij/projects/sql-monitor` @ `fa13ba0` (37 commitów, 2026-06-22 → 2026-07-29)
**Cel:** ocenić, co z `sql-monitor` przenieść do PulseDB, a co przepisać od zera.

---

## 1. Podsumowanie wykonawcze

`sql-monitor` to **działający, jednosilnikowy (MS SQL) kolektor DMV + REST API + CLI + Web UI**, napisany w ~5 tygodni. Jest to prototyp o zaskakująco wysokiej dojrzałości **domenowej** i niskiej dojrzałości **produktowej**.

| Wymiar | Ocena | Uzasadnienie |
|--------|-------|--------------|
| Wiedza domenowa (SQL Server) | ★★★★★ | Query Store, wait→query correlation, load-safety, FRK, deadlocki z `system_health` |
| Architektura warstw | ★★★★☆ | Czysty podział collector/api/cli na wspólnym pakiecie |
| Model danych | ★★☆☆☆ | Snapshot-centric, brak normalizacji tekstu zapytań, brak partycjonowania |
| Gotowość produktowa | ★☆☆☆☆ | Zero auth, zero alertów, brak licencji, sekrety w plaintext JSON |
| Wielosilnikowość | ☆☆☆☆☆ | T-SQL i `pyodbc` wbudowane w kod, brak warstwy adapterów |
| Testy / CI | ★☆☆☆☆ | 4 pliki testów (~450 linii), brak CI, brak testów API i kolektora |

**Werdykt:** `sql-monitor` to **doskonałe źródło wiedzy domenowej i referencyjnych zapytań DMV**, ale **nie jest fundamentem architektonicznym** dla PulseDB. Przenosimy wiedzę i SQL, przepisujemy warstwę zbierania i model danych.

---

## 2. Skala i stack

**Kod:** ~7 550 linii łącznie
- Python (`sql_monitor/`): ~2 900 linii — kolektor, API, CLI, modele
- Testy: ~450 linii (4 pliki)
- Web (`web/src/`): ~2 200 linii — React 19 + TS
- Reszta: migracje, konfiguracja, dokumentacja

**Największe pliki:** `cli/main.py` (1 085), `collector/collect.py` (595), `web/routes/waits.tsx` (454), `db/models.py` (407).

**Stack backend:** Python 3.12 · FastAPI · SQLAlchemy 2 (async) · Alembic · APScheduler · Click + Rich · pyodbc · Pydantic v2 · PostgreSQL 16

**Stack frontend:** React 19 · TypeScript · Tailwind v4 · shadcn (Radix) · TanStack Router + Query · Recharts · axios · Vite 6

**Deployment:** Docker Compose (postgres, migrate, collector, api, cli, web)

✅ Stack jest zgodny z deklarowanym kierunkiem PulseDB (FastAPI + PostgreSQL + React/TS/Tailwind/shadcn/TanStack/axios) — to realna oszczędność czasu na decyzjach technologicznych.

---

## 3. Co projekt faktycznie robi

### 3.1 Zbierane metryki

| Obszar | Źródło | Częstotliwość | Uwagi |
|--------|--------|---------------|-------|
| Wait stats | `dm_os_wait_stats` | 10 min (1 min intensive) | **z deltami** między snapshotami |
| Top queries | `dm_exec_query_stats` | 10 min | unia TOP N po osiach `cpu`/`reads`/`elapsed` + `pinned_objects` |
| Execution plans | `dm_exec_query_plan` | 10 min | XML, tylko dla zebranych zapytań; wyłączone w trybie intensywnym |
| Index usage | `dm_db_index_usage_stats` | 10 min | |
| Missing indexes | `dm_db_missing_index_*` | 10 min | dedup + `first_seen_at`/`last_seen_at` |
| Index definitions | `sys.indexes` + `allocation_units` | 6 h | kolumny key/include, `size_mb`, fill factor |
| Fragmentacja | `dm_db_index_physical_stats` | 6 h | wyłącznie tryb `SAMPLED` |
| Resources | perfmon counters + `dm_os_sys_memory` | 10 min | model EAV (`metric_name`/`metric_value`) |
| Blocking | `dm_exec_requests` + `dm_exec_sessions` | 10 min | pełny kontekst sesji |
| Deadlocki | sesja XE `system_health` | cyklicznie | zero narzutu — sesja i tak działa |
| Query Store (waits) | `sys.query_store_wait_stats` | 30 min | tylko zamknięte interwały, kursor idempotentny |
| Query Store (runtime) | `sys.query_store_runtime_stats` | 30 min | historia niezależna od plan cache |

### 3.2 Funkcje wyróżniające (rzadkie w narzędziach OSS)

1. **Dwie ścieżki korelacji wait → zapytanie**
   - Query Store (precyzyjna atrybucja przez SQL Server — realna, nie zgadywana)
   - snapshot overlap (przybliżenie, fallback dla waitów instancyjnych spoza QS)

   To jest **rdzeń wartości DPA** (response time analysis) zaimplementowany dwoma niezależnymi metodami. Bardzo dobra decyzja produktowa.

2. **Tryb intensywny (incident mode)** — runtime toggle przez `instances.intensive_until` w PostgreSQL; scheduler co 30 s synchronizuje harmonogram. Skraca interwał do 1 min i wyłącza zbieranie planów. **Nie wymaga restartu kolektora.** Żaden z analizowanych konkurentów OSS tego nie ma.

3. **Skodyfikowane reguły load-safety** — `WITH (NOLOCK)`, `SAMPLED` nigdy `DETAILED`, zakaz SQL Trace / własnych sesji XE, fragmentacja max 1×/6 h. Zapisane w `CLAUDE.md` jako reguła projektu, nie tylko konwencja.

4. **`AI_GUIDE.md` (23 KB)** — interpretacja metryk, mapowanie typów wait → kategorie Query Store, workflow diagnostyczny, wymagane GRANT-y. De facto **prompt/knowledge base dla agenta AI**, tylko dostarczony jako plik markdown zamiast jako MCP.

5. **`pinned_objects`** — watchlist procedur zawsze zbieranych poza rankingiem TOP N. Rozwiązuje realny problem: kluczowa biznesowo procedura nigdy nie trafia do TOP 20 po CPU.

6. **Integracja z First Responder Kit** (`sp_BlitzIndex`, `sp_BlitzLock`) — pragmatyczne wykorzystanie de facto standardu społeczności SQL Server.

7. **Dyscyplina stref czasowych** — UTC w bazie/API, Europe/Warsaw w prezentacji, jawnie udokumentowane. Częsty błąd w narzędziach monitoringowych, tu rozwiązany świadomie.

---

## 4. Ocena architektury

### 4.1 Mocne strony

**Podział warstw jest poprawny i przekłada się 1:1 na wizję PulseDB:**

```
SQL Server → Collector → PostgreSQL → { REST API, CLI } → Web UI
```

- API **nigdy nie łączy się z monitorowaną bazą** — czyta wyłącznie z PostgreSQL. To dobra granica bezpieczeństwa i wydajności.
- Wspólny pakiet `sql_monitor` dla trzech entry pointów — brak duplikacji modeli i konfiguracji.
- `pyodbc` jest blokujący, więc wywołania idą przez `run_in_executor` — świadome podejście do async.
- Ingest Query Store jest **idempotentny**: kursor `last_interval_id` per (instancja, baza) + `ON CONFLICT DO NOTHING`. Re-ingest jest bezpieczny. To wzorzec do przeniesienia wprost.
- Migracje Alembic od pierwszego commitu (7 migracji).
- Walidacja konfiguracji: Pydantic + JSON Schema (`json-schemas/instances.schema.json`).

### 4.2 Ograniczenia architektoniczne (blokujące dla PulseDB)

**A. Brak warstwy adapterów silnika bazodanowego** 🔴

`pyodbc`, T-SQL i nazwy DMV są wplecione w kod kolektora, modeli i API. Nazwy tabel PostgreSQL (`wait_stats`, `query_stats`) są neutralne, ale **semantyka kolumn jest 100% SQL-Serverowa** (`signal_wait_time_ms`, `plan_handle`, `query_hash` jako `String(34)`).

Dodanie PostgreSQL jako monitorowanego silnika wymaga przepisania: kolektora, modeli, endpointów, CLI i UI. **To jest główny powód, dla którego PulseDB nie może być forkiem `sql-monitor`.**

**B. Jedna baza danych na instancję** 🔴

`InstanceConfig.database` to pojedynczy string. Ingest Query Store działa tylko dla `cfg.database`, definicje indeksów też. Serwer z 40 bazami wymaga 40 wpisów konfiguracyjnych (albo jest niemonitorowalny). Model docelowy musi być `instance → databases[] → objects[]`.

**C. Model danych: snapshot-centric bez normalizacji** 🟠

`query_stats` zapisuje pełny wiersz z `sql_text` (TEXT) **przy każdym snapshocie**. Przy 3 osiach × TOP 20 + pinned = do ~60 wierszy co 10 min = ~8 600 wierszy/dobę/instancję, każdy z powtórzonym tekstem zapytania. W trybie intensywnym 10× więcej.

Query Store ma to zrobione poprawnie (wymiar `qs_queries` + fakty `qs_runtime_stats`), ale ścieżka DMV — nie. **PulseDB musi mieć jeden model: wymiar `query` (tekst, hash, obiekt) + fakty time-series.**

**D. Brak partycjonowania i kompresji** 🟠

Retencja to `DELETE ... WHERE collected_at < cutoff` po liście ID snapshotów. Na dużym wolumenie: długie transakcje, bloat, presja na autovacuum. Konkurencja (Darling edition Erika Darlinga) używa TimescaleDB; PulseDB powinien od razu przyjąć partycjonowanie deklaratywne albo TimescaleDB.

**E. Chatty collection loop** 🟠

- `_collect_queries` robi `session.flush()` per wiersz **i osobne zapytanie do SQL Server po plan XML per wiersz** — do ~60 round-tripów na snapshot.
- `_collect_missing_indexes` wykonuje `SELECT` per wiersz zamiast bulk upsert.

Nie łamie to reguł load-safety (zapytania są tanie), ale skaluje się liniowo z liczbą instancji i podnosi `collection_duration_ms`.

**F. `network_mode: host` dla collectora i CLI** 🟠

Obejście routingu VPN do SQL Server. Skutki: `POSTGRES_DSN` musi być nadpisany na `localhost:5433`, kontenery tracą izolację sieciową, konfiguracja przestaje być przenośna. Dla produktu self-hosted, który ma być "łatwy we wdrożeniu", to antywzorzec — PulseDB potrzebuje normalnej sieci Dockera + jawnej konfiguracji route/proxy.

### 4.3 Braki produktowe

| Brak | Waga | Komentarz |
|------|------|-----------|
| **Uwierzytelnianie i autoryzacja** | 🔴 krytyczna | API bez auth, `CORSMiddleware(allow_origins=["*"])`. Każdy z dostępem sieciowym czyta pełne teksty zapytań i plany — czyli dane produkcyjne. |
| **Zarządzanie sekretami** | 🔴 krytyczna | Hasła do monitorowanych baz w `config/instances.json` w plaintext, montowanym read-only do 3 kontenerów. Plik jest w `.gitignore` (✅), ale to nie jest rozwiązanie dla produktu. |
| **Alerty** | 🔴 krytyczna | Zero. To table stakes u całej konkurencji komercyjnej i u Darlinga. |
| **Baseline / wykrywanie regresji** | 🟠 wysoka | Dane pozwalają (`qs_runtime_stats` ma szereg czasowy per plan), ale logiki nie ma. To najmocniejszy argument sprzedażowy DPA i pganalyze. |
| **MCP** | 🟠 wysoka | Integracja AI = „agent czyta `AI_GUIDE.md` i odpala CLI w Dockerze". Sprytne, ale nie jest produktem. |
| **Licencja** | 🔴 krytyczna | README wprost: „Brak pliku licencji w repozytorium". Bez tego kod jest zastrzeżony i nienadający się do publikacji. |
| **Multi-tenancy / RBAC** | 🟠 wysoka | Brak pojęcia użytkownika. Fundament `gear-stack` ma to rozwiązać. |
| **CI** | 🟠 wysoka | Brak konfiguracji CI; lint i testy odpalane ręcznie przez `docker compose run`. |

### 4.4 Konkretne błędy znalezione w kodzie

1. **`retention.py` — naruszenie klucza obcego przy czyszczeniu** 🔴
   `purge_old_data()` usuwa `QueryStat`, ale **nie usuwa `QueryPlan`**, mimo że `QueryPlan.query_stat_id` ma `ForeignKey("query_stats.id")`. Model `QueryPlan` jest zaimportowany w pliku i nigdy nieużyty — pętla czyszcząca to `(WaitStat, QueryStat, ResourceStat, BlockingSession, IndexUsage)`.
   **Skutek:** pierwszy przebieg retencji obejmujący snapshot z zebranym planem zakończy się `ForeignKeyViolationError` i cała retencja przestanie działać. Ponieważ retencja domyślna to 60 dni, a projekt ma ~5 tygodni, **błąd jeszcze się nie ujawnił**.
   `sql_monitor/collector/retention.py:39`

2. **`DeadlockEvent` rośnie bez ograniczeń** 🟠 — nieobjęty retencją.

3. **Timestampy jako `DateTime` bez `timezone=True`** 🟠 — cała dyscyplina UTC opiera się na konwencji i funkcji `utc_now()`, nie na typie kolumny. `TIMESTAMPTZ` wyeliminowałby całą klasę błędów (był już jeden incydent: `docs/issues/2026-07-29--qs-ingest-datetimeoffset.md`).

4. **`VITE_API_URL: http://api:8000` w compose** 🟡 — to nazwa hosta wewnątrz sieci Dockera, a zmienna trafia do kodu wykonywanego w przeglądarce. Działa tylko dlatego, że `web/.env.local` (w repo) nadpisuje ją na `http://localhost:8001`. Konfiguracja jest sprzeczna sama ze sobą.

5. **Serwis `web` w compose robi `npm install && vite dev`** 🟡 — brak build produkcyjnego, brak serwera statycznego.

---

## 5. Co przenieść do PulseDB

### 5.1 Przenieść wprost (najwyższa wartość)

| Element | Dlaczego |
|---------|----------|
| **`AI_GUIDE.md` — wiedza interpretacyjna** | Tabela wait type → przyczyna, mapowanie DMV → kategoria Query Store, workflow „szybka diagnoza w 5 minut", wymagane GRANT-y. To jest **treść przyszłych narzędzi MCP i tekstów w UI**. Największe aktywo tego repo. |
| **Zapytania SQL z `collector/queries/`** | Zwalidowane produkcyjnie, load-safe. Do przeniesienia jako adapter `mssql`. |
| **Wzorzec ingestu Query Store** | Kursor + zamknięte interwały + upsert wymiaru + `ON CONFLICT DO NOTHING`. Ten sam wzorzec zadziała dla `pg_stat_statements`. |
| **Reguły load-safety jako reguła projektu** | Wpisać do `CLAUDE.md`/`CONTRIBUTING.md` PulseDB. To jest **argument sprzedażowy** (patrz `opportunities.md`). |
| **Koncept trybu intensywnego** | Realna przewaga, tania w implementacji, brak jej u konkurencji OSS. |
| **`pinned_objects` (watchlist)** | Rozwiązuje realny problem TOP-N. |
| **Dyscyplina stref czasowych** | UTC w storage/API, lokalna w prezentacji — z etykietą. |
| **Shell Web UI** | Layout, sidebar, komponenty shadcn, konfiguracja TanStack Router/Query, wzorzec `lib/api.ts`. ~800 linii boilerplate do zaoszczędzenia. |
| **Formaty wyjścia CLI** (table/json/csv/**markdown**) | Markdown jest formatem pod agenta AI — trafna decyzja. |

### 5.2 Przepisać

| Element | Zamiast |
|---------|---------|
| Model danych | Wymiar `query`/`plan` + fakty time-series; partycjonowanie/TimescaleDB; `TIMESTAMPTZ` |
| Warstwa zbierania | Interfejs `EngineAdapter` (`collect_waits()`, `collect_top_queries()`, `collect_plan()`, …) z implementacjami `mssql` i `postgres` |
| Konfiguracja instancji | Z pliku JSON → do bazy PulseDB, z szyfrowanymi poświadczeniami i CRUD-em przez API |
| Model instancji | `instance → databases[]` zamiast jednej bazy per wpis |
| API | Zasoby wersjonowane i neutralne silnikowo, z auth z `gear-stack` |
| Scheduler | APScheduler in-process jest OK dla MVP; przy wielu workerach potrzebny leader election lub kolejka |

### 5.3 Nie przenosić

- `network_mode: host` i override `POSTGRES_DSN`
- `CORSMiddleware(allow_origins=["*"])`
- Poświadczenia w pliku JSON montowanym do kontenerów
- Model EAV dla `resource_stats` (`metric_name`/`metric_value` jako stringi) — do metryk numerycznych lepiej sprawdzi się jawny schemat lub hypertable z tagami
- `cli/main.py` w obecnej formie (1 085 linii w jednym pliku)

---

## 6. Wnioski dla planowania PulseDB

1. **`sql-monitor` to nie jest MVP PulseDB — to jego spike.** Dowiódł, że zebranie sensownych danych z SQL Server bez obciążania go jest wykonalne w 5 tygodni. Nie dowiódł niczego o wielosilnikowości, bezpieczeństwie ani skali.

2. **Największym przenoszonym aktywem jest wiedza, nie kod.** `AI_GUIDE.md` + zapytania DMV + reguły load-safety = kilka miesięcy nauki domeny, których nie trzeba powtarzać.

3. **Adapter silnika musi powstać przed jakąkolwiek funkcjonalnością.** Każdy tydzień pisania kodu SQL-Server-specific to dług, który trzeba będzie spłacić przy dodawaniu PostgreSQL.

4. **Retencja, partycjonowanie i model wymiar/fakt to decyzje dnia pierwszego.** Migracja modelu danych po zebraniu 60 dni historii u pierwszych użytkowników jest droga.

5. **Bez auth i alertów PulseDB nie jest produktem, tylko skryptem.** Oba muszą znaleźć się w MVP, nie w „fazie 2".

---

## Powiązane

- [market-overview.md](market-overview.md) — krajobraz rynku
- [opportunities.md](opportunities.md) — gdzie jest realna przewaga
- [comparison-matrix.md](comparison-matrix.md) — macierz porównawcza
