# Plan: Desktop UI shell (Faza 2 — wczesny slice)

**Data:** 2026-08-04 · **Status:** `in progress`
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
| Mock estate + placeholder Waits | `mocks/instances.ts`, `WaitsChartPlaceholder.vue` |
| Trasa `/waits`, redirect `/dashboard` → `/waits` | `src/modules/monitoring/routes.ts` |
| i18n pl/en | `src/modules/monitoring/i18n/` |

## Co zostaje (manual QA)

- Weryfikacja wizualna w przeglądarce (light/dark, ⌘K, toggle Explorer)
- Podpięcie REST gdy API monitoring będzie gotowe
- Spike ECharts przed prawdziwym wykresem

## Powiązane

- Research: [2026-08-04-desktop-ui-shell.md](../research/2026-08-04-desktop-ui-shell.md)
