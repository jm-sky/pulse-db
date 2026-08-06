# Issues

Tracked work items (bugs, improvements) live here — not in GitHub Issues.

## Status values

| Status | Meaning |
|--------|---------|
| `todo` | Identified, not started |
| `planned` | Scoped and scheduled |
| `in progress` | Actively being worked on |
| `done` | Fix merged / accepted |
| `verification needed` | Fix applied; needs manual or QA check |

## Index

| ID | File | Summary | Status |
|----|------|---------|--------|
| 001 | [2026-07-30--001--boilerplate-dead-code-cleanup.md](2026-07-30--001--boilerplate-dead-code-cleanup.md) | Pozostałości billing/tenant/feature_limits po boilerplate — w tym martwa kolumna `openrouter_api_token` w tabeli użytkowników | `done` |
| 002 | [2026-07-30--002--ci-continue-on-error.md](2026-07-30--002--ci-continue-on-error.md) | Cztery kroki CI przepuszczane przez `continue-on-error`: black, mypy, pytest (2 failujące testy), vitest | `done` |
| 003 | [2026-07-30--003--ide-style-design-research.md](2026-07-30--003--ide-style-design-research.md) | IDE/Desktop style design research — shell slice: [research](../research/2026-08-04-desktop-ui-shell.md) | `done` |
| 004 | [2026-07-30--004--dead-logs-import-broke-ci-pytest.md](2026-07-30--004--dead-logs-import-broke-ci-pytest.md) | Martwy import `app.modules.logs` wywalał `create_app()` — cały pytest był czerwony na `develop` | `done` |
| 005 | [2026-07-30--005--frontend-typecheck-red-on-develop.md](2026-07-30--005--frontend-typecheck-red-on-develop.md) | CI `Frontend` → `Type check` czerwony — brak `src/lib/` (`cn`, `copyToClipboard`, `valueUpdater`) i `requiresTwoFactorVerification` | `done` |

When adding a new issue: pick next `NNN`, create `YYYY-MM-DD--NNN--slug.md`, add a row here.
