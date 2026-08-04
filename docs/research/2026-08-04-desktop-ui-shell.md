# Research: Desktop / IDE UI shell PulseDB

**Data:** 2026-08-04 · **Status:** `done`
**Kontekst:** [issue 003](../issues/2026-07-30--003--ide-style-design-research.md) · [roadmap.md](../roadmap.md) §5 (Faza 2) · [vision](../vision.md) (łańcuch diagnostyczny, nietykalny Waits)
**Zakres tej notatki:** chrome aplikacji (nawigacja, layout), **nie** pełny research 12 narzędzi ani finalny wykres Waits.
**Legenda:** ✅ potwierdzone · 🟡 założenie · ❓ otwarte

---

## 1. Cel

Ustalić **minimalny shell desktopowy**, w którym da się osadzić przyszłe ekrany domenowe (Waits → Queries → Instance), bez kopiowania wyglądu SaaS (sidebar + karta na środku).

Issue 003 zostaje źródłem kierunku; ta notatka zamyka **slice „shell"**, nie cały research UX.

---

## 2. Referencje (wąsko: chrome i nawigacja)

| Narzędzie | Co wziąć | Czego unikać |
|-----------|----------|--------------|
| **Azure Data Studio / VS Code** | Menu bar + Activity/Explorer + taby + status bar + Command Palette | Pełne dockowanie paneli w MVP |
| **DataGrip / DBeaver** | Drzewo obiektów / serwerów jako primary nav estate | Głębokie Object Explorer SQL (PulseDB nie jest IDE SQL) |
| **SolarWinds DPA** | Główna treść = stacked waits + drill-in; estate → instancja → czas ✅ ([solarwinds-dpa.md](competitors/solarwinds-dpa.md) §4, §8) | Ciężki „Java 2015" chrome, wymuszona platforma |
| **Grafana** | Gęstość informacji, time range w statusie/toolbarze | Builder dashboardów jako metafora produktu |

---

## 3. Keep / drop z listy issue 003

| Element | Werdykt shell v1 | Uwaga |
|---------|------------------|-------|
| Menu Bar | **keep** | File / View / Tools / Help — nawet ze stubami |
| Toolbar | **keep (lekki)** | Time range + Refresh; bez ikonowego śmietnika |
| Tree / Explorer | **keep** | Instancje (mock → API); nie Object Explorer tabel |
| Zakładki (Tabs) | **keep (proste)** | Jedna aktywna zakładka na widok; multi-tab później |
| Status Bar | **keep** | Silnik, status kolektora, zakres czasu |
| Command Palette | **keep** | Ctrl/Cmd+K — już mamy `CommandDialog` w UI kit |
| Context Menu (PPM) | **później** | Po realnych akcjach na węzłach |
| Split View | **później** | Po Waits + panel szczegółów |
| Dockowalne panele | **drop z MVP** | Koszt 1 FTE nieproporcjonalny |
| Breadcrumbs | **opcjonalnie** | Wystarczy ścieżka w tab / title bar |
| Skróty klawiaturowe | **keep (minimalnie)** | Palette + Escape; reszta przy funkcjach |

---

## 4. Propozycja layoutu PulseDB

```
┌─────────────────────────────────────────────────────────────┐
│ MenuBar: File  View  Tools  Help          [⚙][user][⌘K]    │
├──────────────┬──────────────────────────────────────────────┤
│ Explorer     │ TabBar: Waits | …                            │
│ ▼ Estate     ├──────────────────────────────────────────────┤
│   ▼ pg-prod  │                                              │
│     · Waits  │           Workspace (slot)                   │
│     · Queries│           (pełna wysokość, bez max-w card)   │
│   ▶ sql-01   │                                              │
│   ▶ pg-dev   │                                              │
├──────────────┴──────────────────────────────────────────────┤
│ Status: PostgreSQL · Collector OK · Last 1h · 14:02 UTC     │
└─────────────────────────────────────────────────────────────┘
```

**Zasady:**

1. Chrome jest **stały** dla tras domenowych; settings/admin mogą zostać na `AuthenticatedLayout` (SaaS) do czasu migracji.
2. Workspace **edge-to-edge** w panelu treści — zero „karty w karcie".
3. Explorer wybiera **instancję + widok**; treść nie jest osobną nawigacją typu marketingowy dashboard.
4. Placeholder Waits w shellu używa **mock danych** — REST monitoringu jeszcze nie istnieje (tylko CLI) ✅.

---

## 5. Uzasadnienie stylu Desktop / IDE

ICP to DBA / leadzy z estate 5–30 instancji — codziennie SSMS, DataGrip, terminal, IDE. Shell IDE:

- skraca onboarding mentalny („gdzie jest lista serwerów"),
- miesci gęsty widok Waits bez marnotrawstwa na hero/marketing,
- odróżnia PulseDB od kolejnego SaaS monitoringu.

Nie kopiujemy SSMS 1:1 — bierzemy **wzorce nawigacji estate + gęstość**, a treść diagnostyczną z DPA (Waits).

---

## 6. Poza zakresem tej iteracji

- Spike ECharts vs Unovis ([2026-07-30-chart-library.md](2026-07-30-chart-library.md))
- REST `/monitoring/*`
- Pełny research issue 003 (plany, indeksy, execution plans UX)
- Docking, multi-tab persistence, PPM

---

## 7. Następny krok

Plan + implementacja: `DesktopWorkspaceLayout` + mock Explorer + Command Palette + Status Bar + placeholder Waits — [plan](../plans/2026-08-04-desktop-ui-shell.md).
