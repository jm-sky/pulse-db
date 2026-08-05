# Minimalne uprawnienia konta kolektora

**Data:** 2026-07-30 · **Status:** `verification needed`
**Kontekst:** [roadmap.md](roadmap.md) §3 (Faza 0, element 9) · [vision.md](vision.md) §3.6 · [ADR modelu danych](research/2026-07-30-data-model.md)
**Legenda pewności:** ✅ potwierdzone · 🟡 estymacja · ❓ otwarte

Zasada: konto, którym PulseDB łączy się do monitorowanej instancji, dostaje
**tylko** to, co potrzebne do odczytu stanu silnika — nigdy prawa do zapisu
danych użytkownika, nigdy `SUPERUSER`/`sysadmin`. `cli monitoring
detect-capabilities` łączy się i pokazuje, czego kontu brakuje (kolumna
`grants` w wyniku) — użyj go po nadaniu uprawnień, żeby to potwierdzić,
zamiast zgadywać.

## PostgreSQL

Minimalny grant to wbudowana rola **`pg_monitor`** (PostgreSQL ≥ 10) — daje
odczyt `pg_stat_activity` całej instancji (nie tylko własnych sesji),
`pg_stat_*` statystyk, oraz `pg_stat_statements` jeśli zainstalowane. Nie
wymaga `SUPERUSER`.

```sql
-- Utworzenie konta kolektora
CREATE ROLE pulsedb_monitor LOGIN PASSWORD '<wygenerowane-haslo>';

-- Minimalny grant do wszystkich funkcji kolektora dzisiaj i w Fazie 1
GRANT pg_monitor TO pulsedb_monitor;

-- Połączenie do konkretnej bazy w skope'ie monitoringu
GRANT CONNECT ON DATABASE <monitored_db> TO pulsedb_monitor;
```

### Rozszerzenia (opcjonalne, poprawiają jakość danych — ADR §1, §4 vision)

Kolektor **wykrywa** te rozszerzenia (`detect-capabilities`), ale ich
**instalacja wymaga `SUPERUSER`** i leży po stronie operatora monitorowanej
instancji, nie konta `pulsedb_monitor`:

| Rozszerzenie | Co odblokowuje | Kto instaluje |
|---|---|---|
| `pg_stat_statements` | Top queries z historią (Faza 1 element 2) | admin instancji, raz: `CREATE EXTENSION pg_stat_statements;` + `shared_preload_libraries` |
| `pg_wait_sampling` | Wyższa jakość atrybucji waitów niż `pg_stat_activity` (Faza 1 element 1) | admin instancji, opcjonalne |
| `hypopg` | Walidacja hipotetycznych indeksów (v0.2, poza MVP) | admin instancji, opcjonalne |

Po instalacji `pulsedb_monitor` widzi je bez dodatkowego grantu, ale z dwóch
różnych powodów, zweryfikowanych, nie zgadywanych: `pg_stat_statements` jest
czytelne dla `pg_monitor`; `pg_wait_sampling` samo nadaje `GRANT SELECT ...
TO PUBLIC` na swoje trzy widoki (`pg_wait_sampling_current/_history/_profile`)
w skrypcie instalacyjnym rozszerzenia (`pg_wait_sampling--1.1.sql`) — czytelne
dla **każdej** zalogowanej roli, nie tylko `pg_monitor`.

### Opcjonalnie: plany wykonania (Faza 1 element 3)

`EXPLAIN (FORMAT JSON)` wymaga uprawnień do planowania zapytania — zwykle
`SELECT` na tabelach aplikacji w monitorowanym schemacie. Bez tego tick
`query_plans` **pomija** zapytania z błędem uprawnień i nie pada.

```sql
-- Przykład: odczyt schematu aplikacji pod estymowane plany (nigdy EXPLAIN ANALYZE)
GRANT USAGE ON SCHEMA public TO pulsedb_monitor;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO pulsedb_monitor;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO pulsedb_monitor;
```

SQL Server: `VIEW SERVER STATE` wystarcza do `dm_exec_query_plan` oraz
odczytu ring-buffera sesji XE `system_health` (deadlocki) — bez
dodatkowego grantu względem minimum z sekcji poniżej.

### Czego kolektor **nie** dostaje

- Brak `SUPERUSER`, brak członkostwa w `pg_signal_backend` poza tym, co daje
  `pg_monitor` (Faza 3 `KILL SESSION` wymaga osobnych, wyżej uprzywilejowanych
  poświadczeń akcji — §3.6 vision, celowo oddzielone od konta zbierającego).
- Brak `INSERT`/`UPDATE`/`DELETE` na tabelach domenowych klienta — PulseDB nie
  modyfikuje danych aplikacji. Opcjonalny `SELECT` (wyżej) jest tylko pod
  estymowane plany, nie pod odczyt treści biznesowej w produkcie.

## SQL Server

Minimalne uprawnienia to `VIEW SERVER STATE` (poziom serwera) i `VIEW
DATABASE STATE` (poziom bazy) — dają odczyt DMV (`sys.dm_exec_requests`,
`sys.dm_os_waiting_tasks`, `sys.dm_exec_query_stats`) i Query Store bez
`sysadmin`.

```sql
-- Login na poziomie serwera
CREATE LOGIN pulsedb_monitor WITH PASSWORD = '<wygenerowane-haslo>';
GRANT VIEW SERVER STATE TO pulsedb_monitor;

-- Per monitorowana baza: user + uprawnienie bazodanowe
USE <monitored_db>;
CREATE USER pulsedb_monitor FOR LOGIN pulsedb_monitor;
GRANT VIEW DATABASE STATE TO pulsedb_monitor;
```

`VIEW DATABASE STATE` musi być nadane **w każdej** monitorowanej bazie
osobno (uprawnienie bazodanowe, nie serwerowe) — jeśli instancja ma wiele baz
do monitorowania, powtórz blok `USE ... GRANT` dla każdej.

Query Store (`sys.database_query_store_options`, wykrywane przez
`detect-capabilities`) jest funkcją silnika włączaną per baza przez admina
(`ALTER DATABASE ... SET QUERY_STORE = ON`), nie uprawnieniem konta
kolektora — jeśli wyłączona, Faza 1 element 2 (top queries) pada z powrotem
na same DMV.

### Czego kolektor **nie** dostaje

- Brak `sysadmin`, brak `CONTROL SERVER`.
- Brak `ALTER`/`db_owner` na monitorowanych bazach.

## Weryfikacja po nadaniu uprawnień

```bash
cli monitoring register-instance --name ... --engine postgresql --host ... --port 5432 --database ... --username pulsedb_monitor
cli monitoring detect-capabilities <instance-id>
```

Wypisany słownik `grants` musi mieć same `True` dla uprawnień z tabel
powyżej. `False` na `pg_monitor` / `VIEW SERVER STATE` / `VIEW DATABASE
STATE` znaczy, że kolektor będzie działał w trybie ograniczonym (trywialny
`collect` nadal zadziała — liczy aktywne sesje z zapytania dostępnego każdemu
loginowi — ale Faza 1 sampler i top queries tego wymagają).

## Lokalny development (sibling Postgres)

Do szybkiego self-monitoringu w Dockerze:

```bash
bash scripts/monitoring/register_dev_instances.sh   # pulse-db-local + sql-monitor + taxorder-ksef
bash scripts/monitoring/run_scheduler.sh            # albo: docker compose up -d scheduler
```

| Instancja | Połączenie | Grant (raz) |
|-----------|------------|-------------|
| `pulse-db-local` | `db:5432` w sieci Compose | zwykle niepotrzebny (konto app) |
| `sql-monitor-postgres` | `host.docker.internal:5433` | `GRANT pg_monitor TO sqlmonitor;` |
| `taxorder-ksef-local` | `taxorder-ksef-db-dev:5432` (sieć `taxorder-ksef-dev`) | `GRANT pg_monitor TO "taxorder-ksef";` |

Sampler PostgreSQL bierze tylko `state = 'active'`. Pusty wykres Waits przy
zielonym statusie kolektora zwykle oznacza idle bazę, nie błąd połączenia
(np. metadata DB sql-monitor — `scripts/monitoring/sql_monitor_dev_workload.sh`).

## Powiązane

- [roadmap.md](roadmap.md) §3 (Faza 0, element 9)
- [plans/2026-07-30-phase0-foundation.md](plans/2026-07-30-phase0-foundation.md)
- [plans/2026-08-05-query-plans.md](plans/2026-08-05-query-plans.md) — opcjonalny SELECT pod EXPLAIN
- [plans/2026-08-05-blocking-deadlocks.md](plans/2026-08-05-blocking-deadlocks.md) — blocking + SS deadlocks
- [plans/2026-08-05-index-analysis.md](plans/2026-08-05-index-analysis.md) — inventory + unused/missing DDL
- [`backend/app/modules/monitoring/adapters/postgres_adapter.py`](../backend/app/modules/monitoring/adapters/postgres_adapter.py), [`sqlserver_adapter.py`](../backend/app/modules/monitoring/adapters/sqlserver_adapter.py) — źródło `_RELEVANT_ROLES`/`_RELEVANT_PERMISSIONS` powyżej
