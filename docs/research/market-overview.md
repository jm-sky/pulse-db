# Market overview — narzędzia do monitoringu i diagnostyki wydajności baz danych

**Data:** 2026-07-30
**Status:** done
**Metoda:** analiza dokumentacji producentów, cenników publicznych i repozytoriów OSS (lipiec 2026).

**Legenda pewności:** ✅ potwierdzone źródłem · 🟡 założenie/estymacja · ❓ otwarte

---

## 1. Jak dzieli się rynek

Rynek nie jest jednorodny. Są to **cztery różne rynki**, które konkurują ze sobą tylko częściowo:

| Segment | Kupujący | Jednostka wartości | Przykłady |
|---------|----------|--------------------|-----------|
| **A. Database Performance Analysis (DPA)** | DBA / zespół bazodanowy | „dlaczego to zapytanie jest wolne" | SolarWinds DPA, Redgate Monitor, Idera SQLdm, DBmarlin |
| **B. Observability platforms** | Platform/SRE, CTO | „jeden pane of glass dla całego stacku" | Datadog, New Relic, Dynatrace |
| **C. Postgres-native SaaS** | zespoły produktowe, developerzy | „napraw mi indeksy i vacuum" | pganalyze, PostgresAI, Crunchy/EDB |
| **D. Open source / self-hosted** | DBA z ograniczonym budżetem, sektor regulowany | „bez licencji i bez wysyłania danych na zewnątrz" | PMM, pgwatch, PerformanceMonitor (Darling Data), Prometheus + exportery |

PulseDB w obecnej definicji celuje w **A + D jednocześnie**: funkcjonalność klasy DPA, model dystrybucji klasy OSS. To jest sensowne — ale **przestrzeń ta przestała być pusta w 2026 roku** (patrz §4).

---

## 2. Ceny — punkt odniesienia

Ceny listowe, per instancja/serwer, rocznie. Realne ceny transakcyjne są zwykle 15–30% niższe.

| Produkt | Cena | Pewność |
|---------|------|---------|
| SolarWinds DPA | ~1 195 USD (SQL Server, edycja bazowa) do ~4 695 USD (Oracle RAC); typowo 2 500–4 000 USD/instancję/rok w subskrypcji | 🟡 dane z agregatorów, nie z cennika producenta |
| Redgate Monitor Standard | od ~1 164–1 220 USD/serwer/rok | 🟡 producent nie publikuje kwot na stronie cennika (tabela ładowana dynamicznie); dane z ComponentSource/G2 |
| Redgate Monitor Enterprise | cena na zapytanie | ✅ |
| Datadog Database Monitoring | ~70 USD/host/miesiąc = **~840 USD/host/rok**, ponad kosztem Infrastructure (15–18 USD/host/mies.) | 🟡 |
| pganalyze | 149 USD/mies. (1 serwer), 399 USD/mies. (do 4 serwerów), +100 USD/mies. za kolejny | ✅ [cennik](https://pganalyze.com/pricing) |
| dbWatch Control Center | od ~550–588 USD/rok | 🟡 |
| Idera SQL Diagnostic Manager | nieujawniana publicznie | ✅ (brak danych = fakt) |
| **PMM, pgwatch, PerformanceMonitor** | **0 USD** | ✅ |

**Wniosek:** dla estate 20 instancji SQL Server rozwiązanie komercyjne kosztuje **20–50 tys. USD/rok**. To jest luka, w którą wchodzi open source — i w 2026 wszedł w nią ktoś jeszcze (§4).

---

## 3. Kluczowe wymiary techniczne rynku

### 3.1 Agent vs agentless

Podział jest mniej istotny, niż sugeruje marketing:

- **DPA jest agentless** — łączy się przez JDBC i odpytuje instancję „quickpoll" **raz na sekundę**, deklarując <1% narzutu. ✅ [dokumentacja SolarWinds](https://documentation.solarwinds.com/en/success_center/dpa/content/dpa-architecture.htm)
- **Datadog wymaga agenta** na hoście + rozszerzeń w bazie (`pg_stat_statements`, użytkownik `datadog` ze schematem funkcji pomocniczych).
- **Redgate jest agentless dla SQL Server** (WMI + T-SQL).
- **PerformanceMonitor (Darling)** — agentless względem monitorowanej instancji, ale wymaga hosta z Windows Service.

**Istotny wniosek dla PulseDB:** agentless to nie przewaga, to standard w segmencie A. Przewagą jest **częstotliwość próbkowania**. DPA próbkuje co 1 s (to jest źródło ich „response time analysis"); `sql-monitor` robi snapshot co 10 min. To dwa różne produkty, mimo podobnego opisu funkcji.

### 3.2 Sampling wait events — to jest rdzeń kategorii

Wartość DPA sprowadza się do jednego mechanizmu: **wysokoczęstotliwościowego próbkowania aktywnych sesji z atrybucją czasu oczekiwania do konkretnego zapytania** (Oracle nazywa to ASH — Active Session History).

Stan na 2026:

| Silnik | Mechanizm | Dostępność |
|--------|-----------|------------|
| SQL Server | `dm_exec_requests` + `dm_os_waiting_tasks` (próbkowanie zewnętrzne); `query_store_wait_stats` (atrybucja wbudowana, kategorie zamiast typów) | ✅ bez rozszerzeń |
| PostgreSQL | `pg_stat_activity` (snapshot); `pg_wait_sampling`/`pgsentinel` (próbkowanie in-process co 10 ms, wymagają `shared_preload_libraries` + restart) | ⚠️ **rozszerzenie + restart** |

**To jest największe ukryte ryzyko MVP PulseDB.** PostgreSQL nie ma wbudowanej historii wait events. Próbkowanie zewnętrzne `pg_stat_activity` z częstotliwością 1 s przez połączenie sieciowe daje dane gorszej jakości niż `pg_wait_sampling`, ale nie wymaga restartu bazy. Decyzja tu determinuje pozycjonowanie produktu — szerzej w [opportunities.md](opportunities.md) §5.

### 3.3 Storage

Rynek zbiegł się na time-series:
- Datadog/New Relic/Dynatrace — własne backendy kolumnowe
- PMM — VictoriaMetrics + ClickHouse (Query Analytics)
- pgwatch v3/v4 — pluggable sinks (PostgreSQL/TimescaleDB, Prometheus, Parquet, Kafka, gRPC) ✅
- PerformanceMonitor Darling — PostgreSQL + **TimescaleDB**, Lite — DuckDB + Parquet (ZSTD) ✅
- pganalyze — PostgreSQL

**Zwykły PostgreSQL bez partycjonowania jest poniżej standardu rynkowego.** TimescaleDB lub partycjonowanie deklaratywne to minimum.

### 3.4 API i integracje — realna luka

| Produkt | REST API |
|---------|----------|
| Redgate Monitor | **tylko w edycji Enterprise** ✅ („Comprehensive Data API" jako feature odróżniający Enterprise od Standard) |
| Datadog | tak, ale to API platformy, nie API bazy danych |
| PerformanceMonitor (Darling) | **brak API** — „point any SQL client at it and query" ✅ |
| PMM / pgwatch | Grafana API + eksport metryk, brak API domenowego |
| pganalyze | API ograniczone |

**To jest najczystsza luka, jaką znalazłem w tym researchu.** W całym segmencie A+D nie ma produktu, w którym pełne API domenowe jest darmowe i pierwszorzędne.

---

## 4. Zdarzenie, które zmienia założenia PulseDB 🔴

**W lutym 2026 Erik Darling opublikował `PerformanceMonitor` — darmowy, open source (MIT) monitoring wydajności SQL Server z wbudowanym serwerem MCP.**

Fakty ✅ ([repozytorium](https://github.com/erikdarlingdata/PerformanceMonitor), [strona produktu](https://erikdarling.com/free-sql-server-performance-monitoring/)):

- Licencja **MIT**, ~3 279 commitów, ~450 gwiazdek, wydania od stycznia 2026 do lipca 2026 (v3.3.0-nightly z 2026-07-29) — bardzo intensywny rozwój
- **36–38 kolektorów**: wait stats (delty co minutę), blocked processes, waiting tasks, scheduler/CPU, latch/spinlock, file I/O, memory, tempdb, perfmon, deadlock graphs, AG health, Query Store, plan cache, default trace, system health, historia jobów
- **Wbudowany serwer MCP — 74 narzędzia** dla Claude Code / Cursor; edycja Darling pozwala agentowi AI także zapisywać (budować widoki, stroić alerty, onboardować flotę)
- Dwie edycje, obie darmowe: **Lite** (desktop, DuckDB + Parquet) i **Darling** (Windows Service 24/7, PostgreSQL + TimescaleDB, web dashboard + WPF viewer, floty 5–500 serwerów)
- Graficzna przeglądarka planów z `PlanAnalyzer` (30 reguł)
- SQL Server 2016–2025, Azure SQL DB, Azure SQL MI, AWS RDS
- Zero telemetrii, brak zależności chmurowych
- Model biznesowy: **software darmowy dla wszystkich, płatne wyłącznie wsparcie** (500 USD/rok — Supported, 2 500 USD/rok — Priority). Brak feature gates.
- Autor to jeden z najbardziej rozpoznawalnych konsultantów SQL Server na świecie (dystrybucja i zaufanie „za darmo")

**Co to oznacza dla PulseDB:**

Trzy z czterech zakładanych przewag PulseDB — *open source*, *self-hosted first*, *MCP integration* — **przestały być przewagą w segmencie SQL Server**. Ktoś już to zrobił, zrobił to szerzej (38 kolektorów vs 8 obszarów), na liberalniejszej licencji (MIT vs AGPLv3) i ma dystrybucję, której PulseDB nie zbuduje.

**Czego PerformanceMonitor NIE ma** (i to jest teraz mapa przewagi PulseDB):

| Luka | Znaczenie |
|------|-----------|
| **Wyłącznie SQL Server** | Brak PostgreSQL, brak jakiejkolwiek innej bazy |
| **Windows-only** | Darling to Windows Service, viewery to WPF. Brak Linuksa, brak Dockera. |
| **Brak REST API** | Wprost deklarowane: „no APIs". Integracja = zapytania SQL do storage. |
| **MCP tylko na localhost** | Bind na localhost, brak zdalnego dostępu w trybie standardowym |
| **Brak trybu SaaS/multi-tenant** | Model jednego zespołu z jednym hostem monitorującym |
| **UI desktopowy jako główny** | Web dashboard jest read-only i opcjonalny (domyślnie wyłączony) |

Pełna analiza: [competitors/opensource.md](competitors/opensource.md) §2.

---

## 5. Trendy 2026

1. **MCP stał się standardem, nie różnicowaniem.** Ponad 500 publicznych serwerów MCP dla baz danych na początku 2026; MCP wspierany przez Anthropic, OpenAI, Google, Microsoft i AWS. Postgres MCP Pro (Crystal DBA, MIT, ~3,1 tys. gwiazdek) robi już index tuning z `hypopg` i analizę `pg_stat_statements`. **„Mamy MCP" nie jest w 2026 argumentem sprzedażowym — jego brak jest wadą.**

2. **Bezpieczeństwo MCP jest nierozwiązane.** Pierwszy złośliwy pakiet MCP pojawił się we wrześniu 2025, pierwsze CVE z oceną 9.4 w 2025. Dla narzędzia z dostępem do produkcyjnych baz to obszar odpowiedzialności, nie tylko funkcja. **To jest szansa dla PulseDB** — read-only by default, audit log, scope'y — pod warunkiem świadomego zaprojektowania.

3. **Konsolidacja właścicielska po stronie komercyjnej.** SolarWinds przejęty przez Turn/River Capital za 4,4 mld USD (zamknięcie 2025-04-17) ✅. Historycznie przejęcia PE oznaczają wzrost cen i spowolnienie innowacji — to poszerza okno dla alternatyw, ale **nie jest to okno wieczne**.

4. **Observability platforms wchodzą w głąb bazy.** Datadog DBM pokrywa dziś Postgres, MySQL, Oracle, SQL Server, MongoDB, DocumentDB i ClickHouse, z query samples, explain plans i rekomendacjami optymalizacyjnymi ✅. Dla zespołów już płacących Datadogowi dołożenie DBM jest decyzją o wiele mniejszą niż wdrożenie osobnego narzędzia.

5. **AGPLv3 to sprawdzona ścieżka, ale z kosztem.** Grafana (2021), PMM — obie AGPLv3 i obie działają komercyjnie. Koszt: część korporacji ma polityki zakazujące AGPL, co bezpośrednio wycina segment enterprise self-hosted. Szerzej: [opportunities.md](opportunities.md) §6.

---

## 6. Wnioski

1. **Segment „darmowy open-source monitoring SQL Server" został zajęty w lutym 2026.** Wejście tam frontalnie jest przegraną walką.

2. **Segment „darmowy open-source monitoring **wielosilnikowy**, natywny dla Linuksa/Dockera, z API-first" jest wolny.** Nikt nie oferuje jednego panelu dla PostgreSQL **i** SQL Server w modelu OSS self-hosted. PMM nie wspiera SQL Server ✅. pgwatch to tylko Postgres. PerformanceMonitor to tylko SQL Server i tylko Windows.

3. **API-first jako darmowa funkcja to najczystsza luka rynkowa.** U Redgate to feature Enterprise; u Darlinga nie istnieje; u reszty OSS jest to API metryk, nie API domenowe.

4. **Sampling jest granicą jakości produktu, nie funkcjonalności.** Bez próbkowania o wysokiej częstotliwości PulseDB będzie „ładniejszym pgwatch", nie „darmowym DPA".

5. **Największym ryzykiem nie jest konkurencja, tylko zakres.** Cztery silniki × cztery interfejsy (Web/REST/CLI/MCP) × alerty × RBAC × chmura to zakres zespołu, nie jednej osoby. Priorytetyzacja jest w [opportunities.md](opportunities.md) §7–8.

---

## Źródła

- [SolarWinds DPA — architektura](https://documentation.solarwinds.com/en/success_center/dpa/content/dpa-architecture.htm) · [podejście wait-based](https://documentation.solarwinds.com/en/success_center/dpa/content/gettingstarted/dpa-gs-wait-based-monitoring.htm) · [przejęcie przez Turn/River](https://www.solarwinds.com/company/newsroom/press-releases/turnriver-completes-acquisition-of-solarwinds)
- [Redgate Monitor — cennik](https://www.red-gate.com/products/redgate-monitor/pricing/) · [edycja Enterprise](https://www.red-gate.com/products/redgate-monitor/enterprise/)
- [Datadog Database Monitoring — dokumentacja](https://docs.datadoghq.com/database_monitoring/)
- [pganalyze — cennik](https://pganalyze.com/pricing) · [Index Advisor](https://pganalyze.com/postgres-index-advisor)
- [PerformanceMonitor — repozytorium](https://github.com/erikdarlingdata/PerformanceMonitor) · [strona produktu](https://erikdarling.com/free-sql-server-performance-monitoring/) · [edycja Darling](https://erikdarling.com/meet-darling-free-headless-fleet-performance-monitoring-for-sql-server/)
- [Postgres MCP Pro](https://github.com/crystaldba/postgres-mcp)
- [pgwatch — repozytorium](https://github.com/cybertec-postgresql/pgwatch/) · [pgwatch v4](https://www.postgresql.org/about/news/pgwatch-v4-is-out-3143)
- [PMM 3 — dokumentacja](https://docs.percona.com/percona-monitoring-and-management/3/index.html)
- [pg_wait_sampling](https://github.com/postgrespro/pg_wait_sampling) · [PostgresAI — wait events](https://postgres.ai/docs/monitoring/metrics/wait-events)
- [Grafana — relicencjonowanie na AGPLv3](https://grafana.com/blog/grafana-loki-tempo-relicensing-to-agplv3/)
