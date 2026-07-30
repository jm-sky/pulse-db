# Plan: boilerplate PulseDB z hybrydy gear-stack × ops-monitor

**Data:** 2026-07-30 · **Status:** `done`

> **Domknięcie 2026-07-30.** Oba rozjazdy wykryte w inventory Fazy 3 zostały rozwiązane:
> pozostałości `billing` / `tenants` / `feature_limits` usunięte w [issue 001](../issues/2026-07-30--001--boilerplate-dead-code-cleanup.md)
> (zakres poszerzony o i18n `containers`/`items`/`reports`, licencję w `pyproject.toml` i `requires-python`),
> a `backend/migrations/README.md` przepisany pod konwencję PulseDB.
> Rozjazd „i18n `monitor.*`" był rozjazdem na korzyść — tych kluczy nigdy nie skopiowano.
>
> **Pozostaje świadomie:** `MonitorSettings` w `backend/app/core/config.py` (+ `MONITOR_*` w `.env.example`) —
> martwa konfiguracja domeny ops-monitor. Decyzja odłożona do Fazy 0 roadmapy, gdy powstanie
> realna konfiguracja kolektorów PulseDB i będzie wiadomo, czy da się ją przejąć, czy zastąpić.

## Kontekst

- PulseDB jest dziś **docs-only** ([README.md](../../README.md): fundament = gear-stack; AGPLv3; MVP silniki PG + SQL Server).
- Brak playbooka „fork new project” — wzorcem jest reboot ops-monitor (`CHANGELOG` 0.1.0) + kontrakt sync (`ops-monitor/docs/SHARED_CORE.md`).
- LighterPack / „liters” w gear-stack = research domeny gear — **poza zakresem** tej kopii. Przydatne: deployment, env, SHARED_CORE.
- Research ([opportunities.md](../research/opportunities.md) §7–8): Faza 0 = auth użytkownik+hasło+RBAC; OAuth/2FA **nie w MVP**, ale w tym planie **kopiujemy** je z ops (copy-first), wyłączymy env-em później.

## Decyzja źródła (hybryda)

| Warstwa | Źródło | Powód |
|---------|--------|--------|
| Default skeleton | **ops-monitor** | Już bez gear/AI/billing; nowszy CSRF (2026-07-28); pełniejszy compose (dev/prod); lepszy `deploy.sh` |
| `backend/app/core/http_ssrf.py` | **gear-stack** | Brak w ops; przyda się przy outbound do monitorowanych DB |
| Domain gear / AI / billing / tenants / stats | **nie kopiujemy** | Zła domena |
| Domain monitor / `agent/` / `central/` | **nie kopiujemy** | Zła domena; PulseDB zbuduje własną później |
| Billing / Stripe / feature_limits / AI | **nie kopiujemy** | Poza fundamentem; ewentualnie osobny plan Cloud/Enterprise |
| `docs/` z obu źródeł | **nie kopiujemy** | PulseDB ma własne docs |
| Root `DEPLOYMENT.md` z ops | **kopiujemy** jako tymczasowy stub | Bogatszy niż gear root; później rewrite do `docs/deployment/` |

Rozwiązanie napięcia „copy-paste wszystkiego, potem czyść” vs hybryda: **Phase 1 = curated platform** (nie pełny dump + kasowanie domeny). Czyszczenie = strip referencji monitor w routerach + rebrand.

## Chronione w pulse-db (nigdy nie nadpisywać)

- `README.md`, `CLAUDE.md`, cały `docs/`
- `.git/`
- Merge ostrożny: `.gitignore` (nie blind overwrite)

## Nigdy nie kopiować (sekrety / artefakty)

`.env`, `.backups/`, `dist/`, `node_modules/`, `__pycache__/`, `.ruff_cache/`, `.mypy_cache/`, `playwright-report/`, `test-results/`, `backend/.venv/`, `screenshot.png`

## Fazy

### Faza 0 — zapis planu w docs

1. Ten plik + wiersz w [README.md](README.md).

### Faza 1 — curated copy

Z **ops-monitor**: backend platform (core, common, api, auth/users/admin/settings/logs/two_factor, CLI bez monitor), frontend platform, tooling, compose, scripts (bez agent), migracje `000`/`001`/`002`/`066`.

Z **gear-stack**: tylko `backend/app/core/http_ssrf.py` (+ `backend/tests/test_http_ssrf.py`).

Po skopiowaniu: strip monitor z BE/FE routerów; LICENSE = AGPLv3 (nie MIT ze źródeł).

### Faza 2 — rebrand + smoke boot

Rename ops → pulse-db (package, config, compose, deploy, i18n, CSP). Smoke: compose up, migrate, create user, login, `/api/health`.

**Wykonane 2026-07-30:**
- `docker compose -f docker-compose.dev.yml up -d --build db redis app` — health `ok`
- migracje `000`/`001`/`002`/`066` applied
- `cli users create --no-input` (owner)
- login password + CSRF → `accessToken`
- `pnpm install` + `pnpm run type-check` OK
- Usunięto serwis `agent` z compose (dev/yml/prod)

### Faza 3 — inventory keep/drop

| Element | Werdykt | Stan w repo |
|---------|---------|-------------|
| auth password + sessions + RBAC, users, admin, settings, logs | **KEEP** | skopiowane |
| health `/api/health` + `/api/health/details` | **KEEP** | skopiowane |
| CLI users soft/hard delete | **KEEP** | skopiowane |
| `http_ssrf` (+ test) | **KEEP** | z gear-stack |
| OAuth (Google/GitHub/Facebook) | **KEEP w kodzie**, env-off | puste `*_OAUTH_CLIENT_*` / `VITE_*_OAUTH_*` |
| two_factor (TOTP/WebAuthn) | **KEEP w kodzie** | skopiowane; UI dostępne, nie wymagane do login |
| reCAPTCHA | env-off | `RECAPTCHA_ENABLED=false` |
| MonitorSettings w `config.py` | **zostaje na razie** | martwe pola env `MONITOR_*`; do usunięcia w follow-up cleanup |
| i18n klucze `monitor.*` | **zostaje na razie** | dead strings; nie używane bez modułu |
| tenants, billing, AI, feature_limits | **nie w repo** | — |
| monitor/agent/gear | **nie w repo** | strip + brak kopiowania |
| SHARED_CORE discipline | **follow-up** | dodać `docs/SHARED_CORE.md` (pulse-db jako trzeci sibling) |
| Deployment runbook | **follow-up** | root `DEPLOYMENT.md` → później `docs/deployment/` |
| Residual branding w About/Landing copy | **follow-up** | część tekstów nadal „ops-y”; wystarczy do boot |

## Poza zakresem

- Domain PulseDB (adapters, collectors, time-series)
- Bulk-copy gear-stack docs/deployment lub LighterPack research
- Shared npm/pip package extraction
- Commit/push — tylko na osobną prośbę

## Smoke notes

- Email `.local` odrzucany przez walidator — używać `example.com` / prawdziwej domeny.
- Login API wymaga CSRF double-submit (`GET /api/auth/csrf-token` + header `X-CSRF-Token`).
- Lokalne `.env` / `backend/.env` są w `.gitignore` (nie commitować).

## Inventory Fazy 3 (uzupełniane przy implementacji)

> Sekcja nie istniała w pliku przed uzupełnieniem (był tylko nagłówek planowany, treść `_Zostanie uzupełnione po smoke boot._` — nie znaleziono jej w repo). Poniżej stan faktyczny na 2026-07-30, zweryfikowany statycznie (bez `docker compose up`).

### Weryfikacja werdyktów z tabeli „Faza 3"

| Element | Werdykt startowy | Stan faktyczny |
|---|---|---|
| auth password + sessions + RBAC, users, admin, settings, logs | KEEP | ✅ potwierdzone: `backend/app/modules/{auth,users,admin,settings,logs}/`. Uwaga: backend ma moduł `logs`, ale we frontendzie (`src/modules/`) nie ma odpowiadającej strony/widoku logów — tylko backend jest kompletny. |
| health `/api/health` + `/api/health/details` | KEEP | ✅ potwierdzone: `backend/app/api/router.py`, `backend/app/core/health_details.py`, test `backend/tests/test_health_details.py`. |
| CLI users soft/hard delete | KEEP | ✅ potwierdzone: `backend/cli/commands/users.py` (`users_delete` z flagą `--hard`, domyślnie soft-delete). |
| `http_ssrf` (+ test) | KEEP z gear-stack | ✅ potwierdzone: `backend/app/core/http_ssrf.py` + `backend/tests/test_http_ssrf.py`. |
| OAuth (Google/GitHub/Facebook) | KEEP w kodzie, env-off | ✅ potwierdzone: `backend/app/core/oauth.py`; puste `GOOGLE_/FACEBOOK_/GITHUB_OAUTH_CLIENT_*` w `backend/.env.example` i `VITE_*_OAUTH_CLIENT_ID` w `.env.example` (root). |
| two_factor (TOTP/WebAuthn) | KEEP w kodzie | ✅ potwierdzone: `backend/app/modules/two_factor/` + frontend `src/modules/auth/{components,composables,pages}` (Totp*, WebAuthn*, `useTwoFactor.ts`, `useWebAuthn.ts`). |
| reCAPTCHA | env-off | ✅ potwierdzone: `RECAPTCHA_ENABLED=false` w `backend/.env.example`. |
| MonitorSettings w `config.py` | zostaje na razie | ✅ potwierdzone: `backend/app/core/config.py` (klasa `MonitorSettings`, linie ok. 664–710) + `MONITOR_CHECK_INTERVAL_SECONDS` i pokrewne w `backend/.env.example` (linie ok. 156–161). |
| i18n klucze `monitor.*` | zostaje na razie (dead strings) | 🔴 **ROZJAZD**: nie znaleziono ani jednego klucza i18n `monitor.*` w `src/shared/i18n/locales/{en,pl}.ts` ani w i18n modułów (`src/modules/*/i18n/locales/`). Albo nigdy nie zostały skopiowane, albo już wyczyszczone — stan repo jest **lepszy** niż zakładał plan. |
| tenants, billing, AI, feature_limits | nie w repo | 🔴 **ROZJAZD — nieprawda, są ślady**, patrz sekcja „Pozostałości niechcianych domen" niżej. |
| monitor/agent/gear | nie w repo | ✅ potwierdzone: brak katalogów/plików; jedyne trafienia grep to fałszywe pozytywy (`User-Agent`, styl `magenta`, generyczne „monitoring" w opisie produktu PulseDB). |
| SHARED_CORE discipline | follow-up | ✅ potwierdzone: `docs/SHARED_CORE.md` nie istnieje — zgodnie z planem, to wciąż follow-up. |
| Deployment runbook | follow-up | ✅ potwierdzone: root `DEPLOYMENT.md` istnieje jako stub, `docs/deployment/` nie istnieje. |
| Residual branding w About/Landing | follow-up | ❓ nie badano szczegółowo treści marketingowych — poza zakresem tej weryfikacji. |

### Pozostałości niechcianych domen (monitor/agent/gear/billing/AI/tenants/feature_limits)

Mimo werdyktu „nie w repo", znaleziono realne ślady domen billing/AI/tenants/feature_limits:

- **`feature_limits` — martwy, niepodłączony frontend.** `src/modules/admin/services/limitsApiService.ts` i `src/modules/admin/types/limits.types.ts` wołają nieistniejący endpoint `/feature-limits` (backend nie ma modułu `feature_limits`/`billing` — potwierdzone grepem po `backend/app/`). Serwis nie jest nigdzie importowany (`grep -rn "limitsApiService\|IFeatureLimit" src` poza własnymi plikami = 0 wyników) — orphan code.
- **`billing`/AI i18n — martwe stringi.** `src/modules/admin/i18n/locales/en.ts` i `pl.ts` zawierają rozbudowane sekcje „Feature Limits" (AI Limit, Storage Limit) i „Subscriptions"/„Billing" (w tym wzmianka o Stripe: „cancel in Stripe if applicable" / „anuluje w Stripe"). Brak odpowiadającego routingu w `src/modules/admin/routes.ts` i `AdminDashboardPage.vue` — teksty nie są używane.
- **`billing` — realna kolumna w schemacie bazy.** `backend/app/modules/auth/db_models.py:67`: `openrouter_api_token: Mapped[str | None]` pod komentarzem `# Billing fields`. Kolumna jest zerowana przy usuwaniu konta (`backend/app/modules/auth/repositories.py:354`), ale nigdzie nie jest wystawiona w API (brak w `schemas.py`/`router.py`). Martwe pole w tabeli `users`.
- **`tenants` — martwe pola/funkcje w warstwie JWT.** `backend/app/modules/auth/types/jwt.py` (pola `tid`/`trol` — Tenant ID/Role), `src/shared/types/jwt.type.ts` (te same pola) i `src/shared/utils/jwtDecoder.ts` (`getTenantIdFromToken`, `getTenantRoleFromToken`, `hasTenantContext`). Testowane w `backend/tests/test_auth_utils.py`, ale nic w repo nie ustawia tych pól poza testami — martwy hook pod multi-tenant, którego moduł nie istnieje.
- **`billing` — świadomy fallback w CSRF, nie bug.** `backend/app/core/csrf.py:26-29` importuje `app.modules.billing.constants.WEBHOOK_PATHS` w `try/except ImportError` (fallback `[]`); udokumentowane i przetestowane w `backend/tests/test_csrf_middleware.py` z komentarzem „pulse-db has no billing module; WEBHOOK_PATHS defaults to []". To nie jest błąd — to przygotowany hook na przyszły moduł billing, ale technicznie wciąż referencja do domeny wykluczonej planem.
- **`monitor`/`agent`/`gear` (moduł/katalog)** — brak, potwierdzone (patrz tabela wyżej).

### Dodatkowa niespójność dokumentacji (poza zakresem tabeli Faza 3)

- `backend/migrations/README.md` jest nieaktualny/przeklejony ze źródła: opisuje migracje `001.5_create_users_table`, `002_add_gear_tables`, `003_add_missing_gear_fields` (wspomina wprost domenę `gear` — `GearContainerDB`, `GearItemDB`), które **nie odpowiadają** plikom faktycznie obecnym w `backend/migrations/` (`000`, `001`, `002_create_users_table.py`, `066_add_token_version_to_users.py`). Wymaga aktualizacji w osobnym follow-upie (nie ruszane w ramach tego zadania — plik nie jest chroniony przez zasady tego zadania, ale zmiana wykraczałaby poza jego zakres).

### Stan smoke boot (statyczne sprawdzenie, bez `docker compose up`)

- `docker compose config` — ✅ zweryfikowane lokalnie: `docker compose -f docker-compose.yml config --quiet`, `-f docker-compose.dev.yml config --quiet`, `-f docker-compose.prod.yml config --quiet` — wszystkie zwróciły exit code 0 (poprawna składnia/interpolacja zmiennych).
- Numeracja migracji — ✅ pliki obecne: `000_create_schema_migrations.py`, `001_add_email_audit_log.py`, `002_create_users_table.py`, `066_add_token_version_to_users.py`. Skok 002 → 066 jest **zamierzony** (migracja 066 przeniesiona z historii numeracji repo źródłowego), nie jest błędem — ale `backend/migrations/README.md` temu przeczy (patrz wyżej).
- `.env.example` — ✅ potwierdzone kompletne: `diff` kluczy `.env` vs `.env.example` w obu miejscach (root i `backend/`) jest pusty — brak driftu, wszystkie potrzebne zmienne (DB, Redis, SECRET_KEY, OAuth, reCAPTCHA, MONITOR_*, WEBAUTHN_*, RATE_LIMIT_*) są udokumentowane.
- Faktyczny boot (`docker compose up`, migracje na żywej bazie, health check) — ❓ **niesprawdzone, wymaga uruchomienia**. Plan notuje w sekcji „Wykonane 2026-07-30" (Faza 2), że smoke boot był wcześniej wykonany w osobnej sesji; nie było to weryfikowane ponownie w ramach tego zadania (zgodnie z poleceniem: bez `docker compose up`).
