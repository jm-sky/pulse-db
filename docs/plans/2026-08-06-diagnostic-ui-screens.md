# Plan: UI — Plans, Indexes, Instance (blocking/deadlocks)

**Data:** 2026-08-06 · **Status:** `verification needed`
**Kontekst:** [vision §5](../vision.md) · [roadmap §11](../roadmap.md) · API Fazy 1 (plany / blocking / indeksy)
**Wzorzec:** [2026-08-05-queries-ui.md](2026-08-05-queries-ui.md)

## Cel

Dodać brakujące wejścia UI do istniejącego API:

1. **Plans** — drawer na Queries (nie osobny liść Explorera)
2. **Indexes** — ekran inventory + rekomendacje z DDL
3. **Instance** — header + blocking + deadlocks

## Zrobione

### Slice A — Plans w Queries

- Typy + API: `plan-changes`, `…/plans`, `…/plans/{hash}`
- `QueryPlanDrawer` (Sheet): pełny tekst, lista planów, export/copy body
- Badge `Plan change` na wierszach z `isPlanChange` (ostatnie 24 h)
- Klik wiersza w `QueriesTable` otwiera drawer

### Slice B — Indexes

- Trasy `/instances/:id/indexes`, `/indexes`
- `IndexesPanel`: inventory + unused/missing recommendations + Copy DDL
- PG: komunikat zamiast missing-index DMV
- Shell: Explorer / TabBar / Command Palette

### Slice C — Instance

- Trasy `/instances/:id/instance`, `/instance`
- `InstanceDetailPanel`: engine/host/collector/lastSample + blocking (24 h) + deadlocks
- PG: empty state dla deadlock history
- Export XML deadlocka (SS, gdy `hasXml`)

## Nawigacja

```
Explorer: Estate → {instance} → Waits | Queries | Indexes | Instance
TabBar:   te same 4 zakładki
```

Terminy EN: `Indexes`, `Instance`, `Blocking`, `Deadlocks`, `Plan change`.

## Kryterium akceptacji

- Pod aktywną instancją PG i S2017 widać Indexes + Instance
- Na Queries klik wiersza pokazuje plan(y) gdy kolektor je zebrał
- PG nie udaje historii deadlocków ani missing indexes

## Poza zakresem

Wizualizer planów · Overview · wspólny time picker · drill-in Waits→Queries · capabilities w list-instances · akcje DDL/KILL
