# Plan: Desktop UI shell (Faza 2 — wczesny slice)

**Data:** 2026-08-04 · **Status:** `in progress` → `verification needed` (live API + ECharts)
**Kontekst:** [research shell](../research/2026-08-04-desktop-ui-shell.md) · [issue 003](../issues/2026-07-30--003--ide-style-design-research.md) · [roadmap](../roadmap.md) §5
**Uwaga względem roadmapy:** Faza 2 przewiduje CLI/MCP przed UI. Ten plan buduje **tylko chrome + mock**, bez endpointów „dla frontendu" i bez wiązania API pod kształt UI — zgodne z API-first.

## Zakres

1. Layout `DesktopWorkspaceLayout` (menu bar, explorer, tab bar, workspace, status bar).
2. Command Palette (Ctrl/Cmd+K) na istniejącym `CommandDialog`.
3. Mock estate w Explorerze.
4. Trasa `/waits` + redirect `/dashboard` → `/waits`.
5. Placeholder Waits (mock stacked bars CSS/HTML — bez decyzji o bibliotece wykresów).
6. i18n pl/en dla shella.

## Poza zakresem

- Realne dane / REST monitoring
- ECharts spike
- Settings/admin na nowym shellu
- Docking, PPM, split view

## Kryterium wyjścia

- Zalogowany użytkownik widzi shell IDE zamiast SaaS dashboard placeholder.
- Explorer pokazuje mock instancje; wybór zmienia kontekst w status bar.
- ⌘/Ctrl+K otwiera palette z nawigacją do Waits / Settings.
- Settings/admin nadal na `AuthenticatedLayout`.

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

## Co zostaje (manual QA)

- Weryfikacja wizualna w przeglądarce (light/dark, ⌘K, toggle Explorer, przełączanie instancji + live rollupy)
- Drill-in z wykresu (Faza 2 łańcuch §3.7)
- Ekran Queries pod instancją → [2026-08-05-queries-ui.md](2026-08-05-queries-ui.md) (`planned`)

## Powiązane

- Research: [2026-08-04-desktop-ui-shell.md](../research/2026-08-04-desktop-ui-shell.md)
- Granty: [grants.md](../grants.md)
- Scheduler: [2026-07-31-scheduler.md](2026-07-31-scheduler.md)
