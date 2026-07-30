# Open source i self-hosted — najważniejsza kategoria dla PulseDB

**Data:** 2026-07-30 · **Kategoria:** konkurencja bezpośrednia w modelu dystrybucji (segment D)

> To jest najważniejszy plik tego researchu. **Kategoria zmieniła się radykalnie w lutym 2026** i unieważnia część założeń z `README.md` PulseDB.

---

## 1. Mapa kategorii (lipiec 2026)

| Projekt | Silniki | Licencja | Głębia diagnostyki | API | MCP | Platforma |
|---------|---------|----------|--------------------|-----|-----|-----------|
| **PerformanceMonitor (Darling Data)** | SQL Server | MIT | ★★★★★ | ❌ | ✅ 74 narzędzia | Windows |
| **Percona PMM 3** | MySQL, PostgreSQL, MongoDB, Valkey/Redis | AGPLv3 | ★★★★☆ | 🟡 Grafana API | ❌ | Docker/Linux |
| **pgwatch v3/v4** | PostgreSQL | BSD | ★★★☆☆ | 🟡 sinks | ❌ | Docker/Linux/Windows |
| **Postgres MCP Pro** | PostgreSQL | MIT | ★★★☆☆ (tylko przez agenta) | ❌ | ✅ rdzeń produktu | dowolna |
| **Prometheus + eksportery** | dowolne | Apache 2.0 | ★☆☆☆☆ | ✅ | ❌ | dowolna |
| **SQLWATCH** | SQL Server | MIT | ★★★☆☆ | ❌ | ❌ | Windows (**projekt nierozwijany**) |
| **PulseDB (planowany)** | PostgreSQL + SQL Server | AGPLv3 | ❓ | ✅ | ✅ | Docker/Linux |

---

## 2. PerformanceMonitor / Darling Data 🔴 najważniejszy konkurent

**Autor:** Erik Darling · **Licencja:** MIT · [GitHub](https://github.com/erikdarlingdata/PerformanceMonitor) · [strona produktu](https://erikdarling.com/free-sql-server-performance-monitoring/)

### Fakty ✅

- Pierwsze wydanie: **styczeń 2026**. Serwer MCP: **11 lutego 2026**. Ostatni build: **2026-07-29** (v3.3.0-nightly). ~3 279 commitów, ~450 gwiazdek, ~82 forki. Tempo rozwoju bardzo wysokie.
- **36–38 kolektorów:** query snapshots, blocked processes, waiting tasks, wait stats (**delty co minutę**), scheduler/CPU, latch i spinlock stats, file I/O, memory, tempdb, perfmon counters, deadlock graphs, Availability Group health, Query Store, plan cache, historia jobów, default trace, system health events, konfiguracja indeksów i baz.
- **Serwer MCP z 74 narzędziami** dla klientów LLM (Claude Code, Cursor): discovery, health status, historia alertów, analiza waitów/zapytań/CPU/pamięci/blokad, audyt konfiguracji, analiza indeksów. W edycji Darling agent AI może także **zapisywać**: budować własne widoki, stroić alerty i reguły wyciszania, onboardować całe floty.
- **Dwie edycje, obie darmowe i funkcjonalnie identyczne:**
  - **Lite** — przenośny plik wykonywalny, DuckDB + archiwum Parquet (ZSTD, ~10× kompresji), retencja 3 miesiące, monitoring on-demand, aplikacja WPF.
  - **Darling** — headless Windows Service 24/7, **bundlowany PostgreSQL + TimescaleDB** (instalator sam go stawia), floty 5–500 serwerów, opcjonalny read-only web dashboard (port 5153, domyślnie wyłączony) + viewer WPF.
- Graficzna przeglądarka planów z `PlanAnalyzer` (30 reguł).
- Wszystkie zapytania w `READ UNCOMMITTED`, delty zamiast wartości skumulowanych, harmonogram per kolektor konfigurowalny bez zmian w kodzie. Zbieranie tekstów zapytań i planów **wyłączalne per kolektor** dla środowisk wrażliwych.
- SQL Server 2016–2025, Azure SQL DB, Azure SQL MI, AWS RDS for SQL Server. Minimalne uprawnienie: `VIEW SERVER STATE`.
- Zero telemetrii, brak zależności chmurowych, binaria podpisane (SignPath).
- **Model biznesowy:** oprogramowanie darmowe dla wszystkich; płatne wyłącznie **wsparcie** — Supported 500 USD/rok, Priority 2 500 USD/rok. **Brak feature gates.**

### Co to oznacza dla PulseDB

Założenia z `README.md` PulseDB, które ten projekt unieważnia w kontekście SQL Server:

| Zakładana przewaga PulseDB | Status po lutym 2026 |
|---------------------------|----------------------|
| „self-hosted jako darmowy produkt" | ❌ zajęte, i to na liberalniejszej licencji (MIT) |
| „AI-ready architecture, MCP integration" | ❌ zajęte, 74 narzędzia, także z zapisem |
| „otwartość, budowanie zaufania społeczności" | ❌ autor ma większy kredyt zaufania w społeczności SQL Server niż nowy projekt jest w stanie zbudować |
| „prostota wdrożenia" | ⚠️ ich instalator sam stawia PostgreSQL + TimescaleDB — trudno to pobić |

**Nie da się z tym wygrać frontalnie na SQL Server.** Ilość wiedzy domenowej zakodowanej w 38 kolektorach i 30 regułach PlanAnalyzera to dorobek kilkunastu lat konsultingu.

### Luki, które zostają

| Luka | Waga dla PulseDB |
|------|------------------|
| **Wyłącznie SQL Server** | 🔴 najważniejsza — brak PostgreSQL i jakiejkolwiek innej bazy |
| **Windows-only** | 🔴 Windows Service + WPF. Zespół na Linuksie/Kubernetesie nie ma ścieżki wdrożenia. |
| **Brak REST API** | 🔴 deklarowane wprost: „no APIs"; integracja = zapytania SQL do storage |
| **MCP tylko na localhost** | 🟠 brak zdalnego dostępu w trybie standardowym → nie działa dla agenta w CI ani dla zespołu |
| **UI desktopowy jako podstawowy** | 🟠 web dashboard jest read-only i domyślnie wyłączony |
| **Brak multi-tenancy / RBAC** | 🟠 model jednego zespołu, jednego hosta |
| **Brak ścieżki SaaS** | 🟡 istotne dla planów komercyjnych PulseDB |

**To jest dokładna mapa pozycjonowania PulseDB** — patrz [opportunities.md](opportunities.md) §3.

---

## 3. Percona Monitoring and Management (PMM 3)

**Licencja:** AGPLv3 · [dokumentacja](https://docs.percona.com/percona-monitoring-and-management/3/index.html)

- **Silniki:** MySQL, PostgreSQL, MongoDB, Valkey, Redis. ✅ **Brak SQL Server** — i nic nie wskazuje na plany jego dodania.
- **Query Analytics (QAN)** — realna analiza zapytań z historią, nie tylko metryki. W PMM 3 doszła kontrola dostępu oparta na etykietach (LBAC).
- **Architektura:** PMM Server (Docker) + PMM Client (agent na monitorowanym hoście) → VictoriaMetrics (metryki) + ClickHouse (QAN). Grafana jako warstwa prezentacji.
- **Model biznesowy:** oprogramowanie darmowe (AGPLv3), przychód ze wsparcia i usług Percony. **To jest najbliższy precedens dla modelu PulseDB** i dowód, że AGPLv3 + open core działa w tej kategorii.

**Wnioski:**
- ✅ Precedens licencyjny i biznesowy — AGPLv3 w monitoringu baz jest sprawdzone.
- ✅ Brak SQL Server to trwała luka po stronie PMM.
- ⚠️ Wymóg agenta (PMM Client) na monitorowanym hoście to realne tarcie wdrożeniowe — PulseDB agentless ma tu przewagę.
- ⚠️ Grafana jako UI oznacza, że doświadczenie użytkownika jest „dashboardowe", nie „diagnostyczne". Ta sama uwaga co przy Prometheusie.

---

## 4. pgwatch v3 / v4 (Cybertec)

**Licencja:** BSD · [GitHub](https://github.com/cybertec-postgresql/pgwatch/)

- Wyłącznie PostgreSQL, ale za to **bardzo głęboko**: bloat indeksów, sekwencje zbliżające się do limitu, autovacuum zostający w tyle — rzeczy, których monitoring ogólnego przeznaczenia nie widzi.
- **Architektura pluggable sinks** (v3): równoległy zapis do wielu destynacji — PostgreSQL/TimescaleDB, Prometheus, pliki Parquet, Kafka, gRPC. Bardzo dobra decyzja architektoniczna, warta skopiowania jako koncept.
- v3 dodał wsparcie Windows i provisioning dashboardów przez REST API Grafany; v4 (beta) rozwija sinki gRPC.
- **UI = Grafana.** Brak własnego produktu prezentacyjnego, brak API domenowego, brak alertów poza Grafaną.

**Wnioski:** pgwatch jest **poprzeczką jakości zbierania metryk PostgreSQL**, nie konkurentem produktowym. Jeśli PulseDB nie wykrywa bloatu indeksów, wyczerpania sekwencji i opóźnień autovacuum, będzie w segmencie Postgres wyraźnie płytszy od darmowego standardu.

---

## 5. Postgres MCP Pro (Crystal DBA)

**Licencja:** MIT · [GitHub](https://github.com/crystaldba/postgres-mcp) · ~3,1 tys. gwiazdek

- Serwer MCP dla PostgreSQL: listowanie schematów i obiektów, wykonywanie SQL z kontrolą dostępu, **EXPLAIN z symulacją hipotetycznych indeksów (`hypopg`)**, najwolniejsze zapytania z `pg_stat_statements`.
- **Rekomendacje indeksów algorytmem anytime** — greedy search po przestrzeni kandydatów z analizą kosztu i korzyści na froncie Pareto. To nie jest heurystyka „dodaj indeks na kolumnę z WHERE".
- Health checks: indeksy, wykorzystanie połączeń, buffer cache, vacuum, limity sekwencji, opóźnienie replikacji.
- Wymaga rozszerzeń `pg_stat_statements` i `hypopg`. PostgreSQL 13–17.

**Znaczenie dla PulseDB:** to jest dowód, że **„MCP do bazy danych" jest w 2026 kategorią rozwiązaną, a nie luką**. Jednocześnie pokazuje granicę tego podejścia: Postgres MCP Pro **nie ma historii** — działa na tym, co baza akurat ma w `pg_stat_statements`. Nie odpowie na pytanie „co się działo wczoraj o 3 w nocy".

**To jest właściwe pozycjonowanie MCP w PulseDB: nie „MCP do bazy", tylko „MCP do historii wydajności".** Historia jest tym, czego serwery MCP odpytujące bazę na żywo z definicji nie mają.

---

## 6. Pozostałe

**Prometheus / VictoriaMetrics + eksportery** — metryki numeryczne bez tekstów zapytań, planów i atrybucji waitów. Nie są konkurencją funkcjonalną, ale są **konkurencją o uwagę** („mamy już Grafanę"). Odpowiedź: endpoint `/metrics` w formacie Prometheus i koegzystencja. Szerzej: [datadog.md](datadog.md) §5.

**SQLWATCH** (MIT, SQL Server) — dawniej najpoważniejszy OSS dla SQL Server, **projekt nie jest już aktywnie rozwijany**. Jego użytkownicy migrują dziś do PerformanceMonitor.

**imajaydwivedi/SQLMonitor** — SQL Server na bazie SQL Agent jobs + Grafana + Prometheus + Python. Nisza, wysoki próg wdrożeniowy.

**First Responder Kit / dbatools / sp_WhoIsActive** — nie są monitoringiem, tylko zestawami skryptów diagnostycznych, ale w praktyce **to z nimi PulseDB będzie porównywany przez DBA SQL Server**. Wniosek: integracja (jak w `sql-monitor`, gdzie działają już `sp_BlitzIndex` i `sp_BlitzLock`) jest tańsza i skuteczniejsza niż konkurowanie.

**pganalyze** — nie jest open source, ale wyznacza poprzeczkę dla PostgreSQL: Index Advisor analizujący cały workload i zwracający gotowe `CREATE INDEX`, VACUUM Advisor, wizualizacja planów. Cena: 149 USD/mies. za 1 serwer, 399 USD/mies. do 4 serwerów ✅. Self-hosted dopiero w tierze Enterprise. **Ta cena jest wysoka i to jest okno dla PulseDB w segmencie Postgres.**

---

## 7. Wnioski

1. **Segment „darmowy monitoring SQL Server z MCP" został zajęty w lutym 2026.** Trzeba to przyjąć jako fakt i przebudować pozycjonowanie, a nie kwestionować.

2. **Nikt nie oferuje jednego, darmowego, self-hosted narzędzia obsługującego PostgreSQL i SQL Server równorzędnie.** PMM nie ma SQL Server. pgwatch to tylko Postgres. PerformanceMonitor to tylko SQL Server i tylko Windows. **To jest jedyna pusta przestrzeń w tej kategorii.**

3. **API-first jest wyróżnikiem, ponieważ nikt w tej kategorii tego nie robi.** OSS w tej niszy kończy na „podepnij Grafanę" albo „odpytaj storage SQL-em".

4. **MCP musi być na historii, nie na bazie na żywo.** Inaczej PulseDB duplikuje Postgres MCP Pro, przegrywając prostotą.

5. **Poprzeczka domenowa jest wysoko.** Darmowa konkurencja ma 38 kolektorów (SQL Server) i głęboką wiedzę o bloacie i vacuum (Postgres). „Osiem obszarów metryk" nie zrobi wrażenia — trzeba wybrać wąski zakres i zrobić go lepiej niż ktokolwiek.
