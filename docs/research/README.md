# Research

Analizy, spike'i, porównania i notatki zebrane przed podjęciem decyzji implementacyjnych.

## Status values

`todo` · `planned` · `in progress` · `done` · `verification needed`

## Index

| File | Summary | Status |
|------|---------|--------|
| [market-overview.md](market-overview.md) | Krajobraz rynku monitoringu baz danych — segmenty, ceny, trendy 2026, zdarzenie zmieniające założenia PulseDB | done |
| [comparison-matrix.md](comparison-matrix.md) | Macierz porównawcza 13 produktów: funkcje, architektura, silniki, model biznesowy | done |
| [opportunities.md](opportunities.md) | Przewagi, ryzyka, czego nie budować, rekomendowany zakres MVP | done |
| [current-project-analysis.md](current-project-analysis.md) | Analiza `../../sql-monitor` — co przenieść do PulseDB, co przepisać | done |
| [competitors/solarwinds-dpa.md](competitors/solarwinds-dpa.md) | SolarWinds DPA — benchmark kategorii, mechanizm response time analysis | done |
| [competitors/redgate.md](competitors/redgate.md) | Redgate Monitor — benchmark UX i alertowania; API jako funkcja Enterprise | done |
| [competitors/datadog.md](competitors/datadog.md) | Platformy observability: Datadog, New Relic, Dynatrace, Grafana + eksportery | done |
| [competitors/opensource.md](competitors/opensource.md) | OSS: PerformanceMonitor (Darling Data), PMM 3, pgwatch, Postgres MCP Pro i inne | done |
| [competitors/idera-dbwatch.md](competitors/idera-dbwatch.md) | Idera SQL Diagnostic Manager · dbWatch Control Center | done |
| [2026-07-30-chart-library.md](2026-07-30-chart-library.md) | ADR: wybór biblioteki wykresów Web UI — rekomendacja Apache ECharts, odrzucenie Highcharts/AG Charts Enterprise na licencji, unovis jako najbliższa alternatywa | verification needed |

**Konwencja nazw:** korpus researchu konkurencji z 2026-07-30 używa nazw tematycznych bez prefiksu daty (zamiast `YYYY-MM-DD-slug.md`) — jest to zestaw dokumentów utrzymywanych i aktualizowanych cyklicznie (periodic review co 6 miesięcy), nie jednorazowe notatki. Nowe, jednorazowe analizy: `YYYY-MM-DD-slug.md`.

When adding a new entry: create `YYYY-MM-DD-slug.md`, add a row here.

## Related

- [plans/README.md](../plans/README.md) — plany implementacji wynikające z research
- [reviews/README.md](../reviews/README.md) — sesje przeglądu, które mogą generować research
