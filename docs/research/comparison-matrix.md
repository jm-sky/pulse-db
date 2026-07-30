# Macierz porównawcza

**Data:** 2026-07-30 · **Status:** done

Legenda: ✅ pełne · ◐ częściowe/ograniczone · ❌ brak · 🟡 dane niepewne · ❓ nieustalone

---

## 1. Funkcje

| | DPA | Redgate | Idera | dbWatch | Datadog | New Relic | Dynatrace | PMM 3 | pgwatch | **PerfMon (Darling)** | Postgres MCP Pro | Grafana+exp. | **PulseDB (plan)** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Historia zapytań | ✅ | ✅ | ✅ | ◐ | ✅ | ◐ | ◐ | ✅ | ◐ | ✅ | ❌ | ❌ | ✅ |
| Wait statistics | ✅ | ✅ | ✅ | ◐ | ✅ | ◐ | ◐ | ✅ | ◐ | ✅ | ❌ | ❌ | ✅ |
| **Atrybucja wait → zapytanie** | ✅✅ | ◐ | ◐ | ❌ | ✅ | ❌ | ◐ | ✅ | ❌ | ✅ | ❌ | ❌ | **❓ decyzja kluczowa** |
| Execution plans | ✅ | ✅ | ✅ | ◐ | ✅ | ◐ | ◐ | ◐ | ❌ | ✅ + analizator | ✅ (EXPLAIN live) | ❌ | ✅ |
| Śledzenie zmian planu | ✅ | ◐ | ◐ | ❌ | ✅ | ❌ | ◐ | ◐ | ❌ | ✅ | ❌ | ❌ | ❓ |
| Analiza indeksów | ✅ advisor | ◐ | ◐ | ◐ | ◐ | ❌ | ❌ | ◐ | ✅ bloat | ✅ | ✅ hypopg | ❌ | ✅ |
| Blokady / deadlocki | ✅ | ✅ | ✅ | ◐ | ◐ | ❌ | ◐ | ◐ | ◐ | ✅ | ❌ | ❌ | ✅ |
| Alerty | ✅ ML | ✅✅ ~60 typów | ✅ | ✅ | ✅ | ✅ | ✅ AI | ✅ | ◐ Grafana | ✅ | ❌ | ◐ PromQL | **❌ brak w `sql-monitor`** |
| Baseline / anomalie | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅✅ | ◐ | ❌ | ◐ | ❌ | ❌ | ❓ |
| Dashboardy | ✅ | ✅✅ | ◐ | ✅ | ✅✅ | ✅ | ✅ | ✅ | ✅ | ◐ desktop | ❌ | ✅✅ | ◐ |
| Raporty | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ◐ | ❌ | ◐ | ❌ | ◐ | ◐ |
| AI features | ✅ 🟡 | ◐ | ◐ | ❌ | ✅ | ✅ | ✅✅ Davis | ❌ | ❌ | ✅ przez MCP | ✅ rdzeń | ❌ | ✅ przez MCP |

---

## 2. Architektura i integracje

| | DPA | Redgate | Idera | dbWatch | Datadog | PMM 3 | pgwatch | **PerfMon** | **PulseDB (plan)** |
|---|---|---|---|---|---|---|---|---|---|
| Agentless | ✅ | ✅ | ✅ | ◐ | ❌ agent | ❌ agent | ✅ | ✅ | ✅ |
| Częstotliwość próbkowania | **1 s** | ~15–60 s 🟡 | ~60 s 🟡 | min. 🟡 | ~10 s + samples | ~1 s (QAN) | 60 s+ | **60 s (delty)** | **10 min ⚠️** |
| Storage | własne repo | SQL Server | SQL Server | własne | chmura | VictoriaMetrics + ClickHouse | pluggable sinks | PostgreSQL+Timescale / DuckDB | PostgreSQL |
| Partycjonowanie/kompresja | ✅ | ✅ | ✅ | ❓ | ✅ | ✅ | ✅ | ✅ Timescale/ZSTD | **❌ w `sql-monitor`** |
| **REST API domenowe** | ❌ | **❌ (tylko Enterprise)** | ❌ | ❌ | ◐ platformy | ◐ Grafana | ❌ | **❌ „no APIs"** | **✅ pierwszorzędne** |
| **MCP** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ 74 narzędzia, localhost-only** | **✅ zdalny, z historią** |
| CLI | ◐ | ❌ | ❌ | ◐ | ✅ | ◐ | ✅ | ❌ | ✅ |
| Eksport Prometheus | ❌ | ❌ | ❌ | ❌ | ◐ | ✅ | ✅ | ❌ | ❓ zalecane |
| Linux / Docker | ✅ | ❌ Windows | ❌ Windows | ✅ | ✅ | ✅ | ✅ | **❌ Windows** | **✅** |
| Multi-tenant / RBAC | ◐ | ✅ Enterprise | ◐ | ◐ | ✅ | ✅ LBAC | ❌ | ❌ | ✅ (gear-stack) |

---

## 3. Silniki bazodanowe

| | SQL Server | PostgreSQL | MySQL | Oracle | MongoDB | inne |
|---|---|---|---|---|---|---|
| DPA | ✅ | ✅ | ✅ | ✅✅ | ❌ | SAP HANA, MariaDB |
| Redgate | ✅✅ | ◐ | ❌ | ◐ ❓ | ❌ | |
| Idera | ✅✅ | ❌ | ◐ osobny produkt | ❌ | ❌ | |
| dbWatch | ◐ | ◐ | ◐ | ◐ | ❌ | Sybase |
| Datadog | ✅ | ✅ | ✅ | ✅ | ✅ | DocumentDB, ClickHouse |
| PMM 3 | **❌** | ✅ | ✅✅ | ❌ | ✅ | Valkey, Redis |
| pgwatch | ❌ | ✅✅ | ❌ | ❌ | ❌ | |
| **PerfMon (Darling)** | ✅✅ | ❌ | ❌ | ❌ | ❌ | |
| Postgres MCP Pro | ❌ | ✅ | ❌ | ❌ | ❌ | |
| **PulseDB (plan)** | ✅ | ✅ | (później) | (później) | ❌ | |

> **Kluczowa obserwacja:** w wierszach OSS (PMM, pgwatch, PerfMon, Postgres MCP Pro) nie ma **ani jednego** projektu z jednoczesnym ✅ w kolumnach SQL Server i PostgreSQL. To jedyne pole, gdzie PulseDB jest sam.

---

## 4. Model biznesowy i cena

| | Licencja | Self-hosted | Cena (rok, orientacyjnie) | Publiczny cennik |
|---|---|---|---|---|
| DPA | komercyjna | ✅ | 1 195–4 695 USD/instancję 🟡 | ❌ |
| Redgate Standard | komercyjna | ✅ | ~1 164–1 220 USD/serwer 🟡 | ❌ (tabela nie ładuje kwot) |
| Redgate Enterprise | komercyjna | ✅ | na zapytanie | ❌ |
| Idera SQLdm | komercyjna | ✅ | nieujawniana | ❌ |
| dbWatch | komercyjna | ✅ | od ~550–588 USD 🟡 | ◐ |
| Datadog DBM | SaaS | ❌ | ~840 USD/host + infra 🟡 | ✅ |
| pganalyze | komercyjna | ◐ Enterprise | 1 788 USD (1 serwer) / 4 788 USD (4) | ✅ |
| PMM 3 | **AGPLv3** | ✅ | 0 (wsparcie płatne) | — |
| pgwatch | BSD | ✅ | 0 | — |
| **PerfMon (Darling)** | **MIT** | ✅ | **0** (wsparcie 500 / 2 500 USD) | ✅ |
| Postgres MCP Pro | MIT | ✅ | 0 | — |
| **PulseDB (plan)** | **AGPLv3** | ✅ | 0 + cloud/enterprise | ✅ |

---

## 5. Odczyt macierzy — cztery wnioski

1. **Kolumna „REST API domenowe" jest prawie pusta.** Jedyne ✅ to Redgate Enterprise (płatne, cena na zapytanie) i platformy observability (API platformy, nie bazy). To najczystsza luka na całej macierzy.

2. **Kolumna „MCP" ma dokładnie dwa wpisy** — PerformanceMonitor (localhost-only) i Postgres MCP Pro (bez historii). MCP nie jest już luką, ale **MCP zdalny, po historii, wielosilnikowy — wciąż jest**.

3. **Wiersz PulseDB ma dziś dwie czerwone komórki, obie krytyczne:** brak alertów i częstotliwość próbkowania 10 min przy 1 s u lidera kategorii. Bez ich zaadresowania pozostałe ✅ nie mają znaczenia.

4. **Tabela silników jest najsilniejszym argumentem za PulseDB** — i jedynym, którego nikt inny w OSS nie może szybko podważyć (PMM musiałby dodać SQL Server, Darling musiałby przepisać się z Windows na wieloplatformowość i dodać Postgres).

---

## Powiązane
- [market-overview.md](market-overview.md) · [opportunities.md](opportunities.md) · [current-project-analysis.md](current-project-analysis.md)
