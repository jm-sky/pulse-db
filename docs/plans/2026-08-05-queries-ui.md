# Plan: Web UI — Queries (Faza 2, wczesny slice)

**Data:** 2026-08-05 · **Status:** `verification needed`
**Kontekst:** [roadmap.md](../roadmap.md) §5 element 4 · [vision](../vision.md) § ekran Queries · [shell](2026-08-04-desktop-ui-shell.md)
**Poprzednik API:** [Faza 1 element 6 — period comparison](2026-07-30-phase1-diagnostic-core.md) · [plany wykonania](2026-08-05-query-plans.md)

## Dlaczego teraz

Shell + Waits są na live API. W Explorerze **Queries** jest świadomie `disabled`
(placeholder). Backend Fazy 1 już wystawia ranking z regresją przez
`period-comparison` — UI może iść na istniejącym kontrakcie, bez endpointów
„dla frontendu" (kryterium API-first Fazy 2).

Stary blocker roadmapy („Queries przed live E2E indeksów") nie blokuje startu:
element 5 jest ✅. Przed akceptacją UI warto domknąć E2E elementu 6 na żywych
rollupach (`verification needed`).

## Cel MVP

Ekran **Queries** pod instancją: ranking zapytań w oknie czasu z flagą regresji
względem okna bazowego — wejście w łańcuch §3.7 na poziomie *zapytanie*
(bez jeszcze pełnego → plan → rekomendacja).

## Zakres

1. Trasa `/instances/:instanceId/queries` + strona w `DesktopWorkspaceLayout`.
2. Włączenie węzła Queries w Explorerze (nawigacja jak Waits).
3. Tab bar: aktywna zakładka `waits` | `queries` (przełączanie w kontekście instancji).
4. Klient API + typy + TanStack Query dla
   `GET /api/monitoring/instances/{id}/queries/period-comparison`.
5. Tabela rankingu (gęsty widok IDE, bez kart): tekst zapytania (skrót),
   calls / total / avg (current), delty, `isRegression`.
6. Domyślne okna czasu: **current = ostatnie 24 h**, **baseline = poprzednie 24 h**
   (ziarno `query_stat_1h`). Toggle „tylko regresje" → `regressionsOnly`.
7. Stany: loading / error / empty (brak rollupów — komunikat o schedulerze /
   `collect-query-stats` + `rollup-query-stats-1h`).
8. i18n pl/en; Command Palette: „Open Queries".
9. Refresh (jak Waits).

## Poza zakresem (świadomie)

| Element | Powód |
|---------|--------|
| Drill-in Waits → sesja → zapytanie (§3.7) | Osobny slice po kliku w wykresie Waits |
| Panel planu / `plan-changes` / eksport planu | Osobny slice; API już jest |
| Osobny endpoint „top queries w jednym oknie" | Niepotrzebny, póki UX miesci się w period-comparison |
| Baseline sezonowy percentylowy (Faza 1 el. 7) | Brak API |
| Indexes / Overview / Instance detail | Roadmapa Faza 2 el. 5+ |
| Edytowalny time picker UI | Waits też ma na razie stałe okno; wspólny picker później |
| Sortowanie po stronie klienta poza kontraktem API | API sortuje po severity regresji; ewentualne sortowanie kolumn = follow-up |

## Decyzje projektowe

### Źródło danych = period-comparison ✅

Vision: *ranking z historią, regresja względem okresu*. Endpoint zwraca dokładnie
to (`avgTimeMsDelta*`, `isRegression`, `queryText`). Dwa okna są częścią produktu,
nie obejściem braku API.

🟡 Jeśli UX okaże się mylący bez jawnego „Top by total time (current only)",
rozważyć drugi widok / sort — nadal na tym samym endpointcie (sort client-side
po `current.totalTimeMs`) albo dopiero wtedy nowy read model w API.

### Layout

Wzorzec Waits: pełna wysokość workspace, toolbar (tytuł + zakres + Refresh),
treść edge-to-edge. Tabela, nie karty. Wiersz regresji wyróżniony dyskretnie
(kolor / badge), bez „alert spam".

### Nawigacja

```
Explorer: Estate → {instance} → Waits | Queries
TabBar:   Waits | Queries   (ta sama instanceId)
```

Zmiana zakładki = `router.push` na sibling path; Explorer podświetla aktywny widok.

## Kroki implementacji

| # | Krok | Pliki (orientacyjnie) |
|---|------|------------------------|
| 1 | Typy + `monitoringApiService.getQueryPeriodComparison` | `types/monitoring.type.ts`, `services/monitoringApiService.ts` |
| 2 | `useQueryPeriodComparisonQuery` + query keys | `composables/useMonitoringQueries.ts`, `utils/queryUtils.ts` |
| 3 | Trasy + `InstanceQueriesPage` | `routes.ts`, `pages/InstanceQueriesPage.vue` |
| 4 | `QueriesTable` (lub inline) — kolumny, truncate SQL, empty/error | `components/QueriesTable.vue` |
| 5 | Shell: Explorer enable, TabBar `queries`, layout prop | `InstanceExplorer.vue`, `WorkspaceTabBar.vue`, `DesktopWorkspaceLayout.vue` |
| 6 | Palette + i18n | `DesktopCommandPalette.vue`, `i18n/locales/{en,pl}.ts` |
| 7 | Smoke: Typecheck / istniejące testy frontu jeśli są pod monitoring | — |

## Kryterium wyjścia

- Zalogowany user klika **Queries** pod instancją → tabela z live danymi
  (gdy są rollupy `query_stat_1h`) albo jasny empty state.
- Przełączanie Waits ↔ Queries zachowuje `instanceId`.
- Brak nowych endpointów backendowych w tym slice.
- Manual QA: light/dark, PL/EN, instancja bez historii zapytań, filtr regresji.

## Zrobione (2026-08-05)

| Element | Gdzie |
|---------|-------|
| Typy + `getQueryPeriodComparison` | `types/monitoring.type.ts`, `services/monitoringApiService.ts` |
| TanStack Query composable | `composables/useMonitoringQueries.ts`, `utils/queryUtils.ts` |
| Trasy `/queries`, `/instances/:id/queries` | `routes.ts`, `pages/InstanceQueriesPage.vue`, `QueriesRedirectPage.vue` |
| Tabela rankingu + filtr regresji | `components/QueriesTable.vue` |
| Explorer / TabBar / Palette | `InstanceExplorer.vue`, `WorkspaceTabBar.vue`, `DesktopCommandPalette.vue` |
| i18n pl/en | `i18n/locales/{en,pl}.ts` |
| Format helpers + test | `utils/formatQueryMetrics.ts` |

## Zależności runtime (dev)

- Scheduler / ticki: `collect-query-stats`, `rollup-query-stats-1h` (oraz granty
  `pg_stat_statements` / DMV — [grants.md](../grants.md)).
- Preferencja: przed merge UI potwierdzić E2E `period-comparison` na lokalnym PG
  (status elementu 6).

## Co zostaje po MVP

1. Detail drawer: pełny `queryText` + metryki + link do planów API.
2. Wspólny time-range picker (Waits + Queries + status bar).
3. Drill-in z Waits do Queries (filtr po `queryId` / oknie).
4. UI plan-changes (badge przy wierszu gdy `isPlanChange`).

## Powiązane

- Research shell: [2026-08-04-desktop-ui-shell.md](../research/2026-08-04-desktop-ui-shell.md)
- API: `GET .../queries/period-comparison`, `GET .../period-comparison/summary`
