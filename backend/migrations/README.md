# Database Migrations

Migration scripts for the PulseDB repository database (PostgreSQL 17).

## Konwencja

Każda migracja to jeden plik `NNN_nazwa.py` z korutynami `upgrade()` i `downgrade()`,
wykonującymi surowe SQL przez `app.core.database.engine`. Wzorzec:
[`067_drop_openrouter_api_token.py`](067_drop_openrouter_api_token.py).

**Schemat domenowy PulseDB powstaje jako surowe DDL, nie z metadanych SQLAlchemy.**
Tabele faktów są partycjonowane po czasie, a klucze unikalne muszą zawierać kolumnę
czasu — czego `metadata.create_all()` nie wyrazi. Modele SQLAlchemy mogą istnieć do
odczytu, ale źródłem prawdy o DDL są migracje.
Uzasadnienie: [ADR modelu danych](../../docs/research/2026-07-30-data-model.md) §3.

## Available Migrations

| Wersja | Opis | Model / obszar |
|--------|------|----------------|
| `000` | Tabela `schema_migrations` do śledzenia historii migracji | — |
| `001` | Tabela `email_audit_log` | `app.common.models.EmailAuditLog` |
| `002` | Tabela `users` (uwierzytelnianie) | `app.modules.auth.db_models.UserDB` |
| `066` | Kolumna `token_version` w `users` | `UserDB` |
| `067` | Usunięcie kolumny `openrouter_api_token` z `users` | [issue 001](../../docs/issues/2026-07-30--001--boilerplate-dead-code-cleanup.md) |
| `068` | Wymiary domeny monitoringu: `monitored_instance`, `monitored_database`, `query_text`, `query`, `plan_text`, `query_plan`, `wait_class` (+seed), `wait_event` (+seed), `session_attr` | [ADR modelu danych](../../docs/research/2026-07-30-data-model.md) §3 |
| `069` | Fakty domeny monitoringu, partycjonowane dziennie: `session_sample`, `query_stat_delta`, `instance_metric`, `index_snapshot`, `collector_run` + zdarzeniowe/audytowe: `blocking_event`, `deadlock_event`, `deep_mode_window`, `recommendation`, `recommendation_outcome`, `action_audit` | [ADR modelu danych](../../docs/research/2026-07-30-data-model.md) §3, §6; [plan Fazy 0](../../docs/plans/2026-07-30-phase0-foundation.md) |
| `070` | `query_stat_cursor` (kursor kumulatywnych liczników `pg_stat_statements` per zapytanie, do liczenia delt) + `collector_run.kind` (rozróżnienie tick'ów o różnej kadencji dla poprawnego gap-detection) | [plan Fazy 1](../../docs/plans/2026-07-30-phase1-diagnostic-core.md) |

Skok numeracji `002` → `066` jest zamierzony i odziedziczony z boilerplate'u
(rodzina ops-monitor / gear-stack) — migracje domen, których PulseDB nie ma,
nie zostały skopiowane.

## Usage

### Zalecane: CLI

```bash
cd backend
python cli.py db migrate          # uruchamia wszystkie oczekujące migracje
python cli.py db migrate-status   # pokazuje stan
```

CLI wykrywa migracje w tym katalogu, sprawdza, które zostały już zastosowane,
uruchamia tylko oczekujące w kolejności i zapisuje je w `schema_migrations`.

### Alternatywa: `db init` (tylko development)

```bash
python cli.py db init
```

Tworzy tabele z modeli SQLAlchemy i oznacza migrację `000` jako zastosowaną.
**Nie wystarczy dla schematu domenowego PulseDB** — patrz uwaga o surowym DDL wyżej.

### Pojedyncza migracja (debug)

```bash
python migrations/067_drop_openrouter_api_token.py upgrade
python migrations/067_drop_openrouter_api_token.py downgrade
```

**Uwaga:** uruchomienie ręczne **nie** zapisuje migracji w `schema_migrations`.
Do normalnej pracy używaj `cli.py db migrate`.

## Migration Tracking

Tabela `schema_migrations`:

- `version` (PRIMARY KEY) — numer migracji, np. `067`
- `name` — nazwa, np. `drop_openrouter_api_token`
- `applied_at` — znacznik czasu zastosowania

Tworzona automatycznie przy pierwszym `db init`, `db migrate` lub `db migrate-status`.

## Alembic — decyzja odłożona

Świadomie **zostajemy przy tym runnerze** na czas Fazy 0; refaktor działającej
platformy nie jest jej zakresem. Wyzwalacz rewizji: więcej niż ~10 migracji
domenowych albo pierwsza migracja **danych**, nie tylko schematu.
Szczegóły: [ADR modelu danych](../../docs/research/2026-07-30-data-model.md) §3.
