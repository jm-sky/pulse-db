# Plan: Desktop UI shell (Faza 2 — wczesny slice)

**Data:** 2026-08-04 · **Status:** `done`
**Kontekst:** [research shell](../research/2026-08-04-desktop-ui-shell.md) · [issue 003](../issues/2026-07-30--003--ide-style-design-research.md) · [roadmap](../roadmap.md) §5
**Uwaga względem roadmapy:** Faza 2 przewiduje CLI/MCP przed UI. Ten plan buduje **tylko chrome**, bez endpointów „dla frontendu" i bez wiązania API pod kształt UI — zgodne z API-first.

## Zakres

1. Layout `DesktopWorkspaceLayout` (menu bar, explorer, tab bar, workspace, status bar).
2. Command Palette (Ctrl/Cmd+K) na istniejącym `CommandDialog`.
3. Mock estate w Explorerze → live API.
4. Trasa `/waits` + redirect `/dashboard` → `/waits`.
5. Placeholder Waits → live ECharts.
6. i18n pl/en dla shella.

## Poza zakresem

- Drill-in z wykresu (łańcuch §3.7)
- Docking, PPM, split view
- Admin / Profile na shellu (nadal `AuthenticatedLayout`)

## Kryterium wyjścia

- Zalogowany użytkownik widzi shell IDE zamiast SaaS dashboard placeholder.
- Explorer pokazuje live instancje; wybór zmienia kontekst w status bar.
- ⌘/Ctrl+K otwiera palette z nawigacją do Waits / Queries / Settings.

## Zrobione (2026-08-04)

| Element | Gdzie |
|---------|-------|
| Research shell | `docs/research/2026-08-04-desktop-ui-shell.md` |
| `DesktopWorkspaceLayout` + menu / explorer / tabs / status / palette | `src/modules/monitoring/components/` |
| Trasa `/waits`, redirect `/dashboard` → `/waits` | `src/modules/monitoring/routes.ts` |
| i18n pl/en | `src/modules/monitoring/i18n/` |

## Iteracja 2026-08-05 — live API + ECharts Waits

| Element | Gdzie |
|---------|-------|
| `GET /api/monitoring/instances` | `router.py`, `waits_timeline.py` |
| `GET /api/monitoring/instances/{id}/waits/timeline` | tamże |
| Explorer z API, trasa `/instances/:id/waits` | `InstanceExplorer.vue`, `routes.ts` |
| Wykres Waits (ECharts stacked bar, `ash_1m`/`ash_1h`) | `WaitsChart.vue`, `waitsChartOption.ts` |
| Usunięte mocki | `mocks/instances.ts`, `WaitsChartPlaceholder.vue`, `WaitsPage.vue` |

### Lokalne instancje deweloperskie

| Nazwa | Host (z kontenera) | Skrypt / uwagi |
|-------|--------------------|----------------|
| `pulse-db-local` | `db:5432` | `cli monitoring register-dev-instances --repair` |
| `sql-monitor-postgres` | `host.docker.internal:5433` | metadata DB sql-monitor; często idle → pusty wykres bez workloadu (`scripts/monitoring/sql_monitor_dev_workload.sh`) |
| `taxorder-ksef-local` | `taxorder-ksef-db-dev:5432` | sieć Docker `taxorder-ksef-dev` na `app`/`scheduler` (brak portu na hoście) |

Rejestracja + podpięcie sieci: `bash scripts/monitoring/register_dev_instances.sh`. Scheduler: `bash scripts/monitoring/run_scheduler.sh` albo serwis Compose `scheduler`.

## Iteracja 2026-08-06 — QA + Settings w shellu

Manual QA (live): Waits na wielu instancjach, ⌘/Ctrl+K, toggle Explorer, light/dark — OK.
Uwaga: Ctrl+K koliduje ze skrótem Chrome (omnibox) — palette działa; follow-up: inny skrót albo dokumentacja.

| Element | Gdzie |
|---------|-------|
| `/settings` w `DesktopWorkspaceLayout` (bez `AuthenticatedLayout`) | `modules/settings/pages/SettingsPage.vue` |
| `activeTab` opcjonalny (Settings nie podświetla Waits/Queries) | `DesktopWorkspaceLayout.vue`, `WorkspaceTabBar.vue` |
| i18n: chrome PL, terminy domenowe EN (`Estate`, `Waits`, `Queries`); `lastOneHour` przez i18n | `i18n/locales/{pl,en}.ts`, `useWorkspaceContext.ts` |

Ekran Queries: [2026-08-05-queries-ui.md](2026-08-05-queries-ui.md) (`done`).

## Co zostaje (poza tym planem)

- Drill-in z wykresu (Faza 2 łańcuch §3.7)
- Profil / Admin na shellu
- Alternatywny skrót palety vs Chrome

## Powiązane

- Research: [2026-08-04-desktop-ui-shell.md](../research/2026-08-04-desktop-ui-shell.md)
- Granty: [grants.md](../grants.md)
- Scheduler: [2026-07-31-scheduler.md](2026-07-31-scheduler.md)
