# Plan: boilerplate PulseDB z hybrydy gear-stack × ops-monitor

**Data:** 2026-07-30 · **Status:** `verification needed`

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
