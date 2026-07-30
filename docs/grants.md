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

Po instalacji `pulsedb_monitor` widzi je przez `pg_monitor` bez dodatkowego
grantu — same widoki `pg_stat_statements`/`pg_wait_sampling` są czytelne dla
tej roli.

### Czego kolektor **nie** dostaje

- Brak `SUPERUSER`, brak członkostwa w `pg_signal_backend` poza tym, co daje
  `pg_monitor` (Faza 3 `KILL SESSION` wymaga osobnych, wyżej uprzywilejowanych
  poświadczeń akcji — §3.6 vision, celowo oddzielone od konta zbierającego).
- Brak `SELECT`/`INSERT`/`UPDATE`/`DELETE` na tabelach domenowych klienta —
  PulseDB nie czyta danych aplikacji, tylko metadane wykonania.

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

## Powiązane

- [roadmap.md](roadmap.md) §3 (Faza 0, element 9)
- [plans/2026-07-30-phase0-foundation.md](plans/2026-07-30-phase0-foundation.md)
- [`backend/app/modules/monitoring/adapters/postgres_adapter.py`](../backend/app/modules/monitoring/adapters/postgres_adapter.py), [`sqlserver_adapter.py`](../backend/app/modules/monitoring/adapters/sqlserver_adapter.py) — źródło `_RELEVANT_ROLES`/`_RELEVANT_PERMISSIONS` powyżej
