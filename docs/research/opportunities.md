# Szanse, ryzyka i rekomendacje produktowe dla PulseDB

**Data:** 2026-07-30 · **Status:** done
**Perspektywa:** CTO startupu budującego produkt open source. Rekomendacje są jednoznaczne, nie są listą opcji.

---

## 1. Teza

> **PulseDB nie powinien być „darmowym monitoringiem baz danych". Powinien być pierwszym narzędziem diagnostyki wydajności, w którym API jest produktem, a Web UI, CLI i MCP są jego klientami — obsługującym PostgreSQL i SQL Server w jednym panelu, natywnie na Linuksie i w Dockerze.**

Uzasadnienie w trzech faktach z researchu:

1. **Nikt w OSS nie obsługuje PostgreSQL i SQL Server równorzędnie** — PMM nie ma SQL Server, pgwatch to tylko Postgres, PerformanceMonitor to tylko SQL Server i tylko Windows.
2. **Nikt w segmencie A i D nie daje darmowego, pierwszorzędnego API domenowego** — u Redgate to funkcja Enterprise bez publicznej ceny, u Darlinga nie istnieje („no APIs"), u reszty OSS to Grafana albo eksport metryk.
3. **W lutym 2026 zniknęły trzy z czterech zakładanych przewag PulseDB** (open source + self-hosted + MCP dla SQL Server) — zajął je Erik Darling na licencji MIT. Pozycjonowanie musi się przesunąć tam, gdzie jest jeszcze pusto.

---

## 2. Gdzie konkurencja jest słaba — weryfikacja hipotez ze zlecenia

Zadanie wymieniało hipotetyczne słabości konkurencji. Research je weryfikuje — **trzy z sześciu okazały się nieaktualne**:

| Hipoteza | Werdykt | Uzasadnienie |
|----------|---------|--------------|
| Trudne wdrożenie | ✅ **potwierdzona częściowo** | Prawdziwa dla DPA (Java, appliance), Idery i PMM (agent na hoście). **Nieprawdziwa dla PerformanceMonitor** — ich instalator sam stawia PostgreSQL + TimescaleDB. |
| Wysoka cena | ✅ **potwierdzona** | 20–50 tys. USD/rok za 10–25 instancji. To realna, trwała słabość segmentu A. Najmocniejszy argument. |
| Zamknięty ekosystem | ✅ **potwierdzona i silniejsza niż zakładano** | Dane monitoringu są zamknięte nawet w produktach self-hosted. API u Redgate = tier Enterprise. |
| Brak AI integration | ❌ **obalona** | Darling ma 74 narzędzia MCP. Postgres MCP Pro robi index tuning z `hypopg`. DPA reklamuje AI root cause. |
| Brak MCP/API | ◐ **połowicznie** | **MCP już jest** u dwóch konkurentów OSS. **API domenowego wciąż nie ma nigdzie za darmo** — i to jest właściwa część tej hipotezy. |
| Brak self-hosted | ❌ **obalona** | Self-hosted ma DPA, Redgate, Idera, dbWatch, PMM, pgwatch, PerformanceMonitor. Wyjątkiem są tylko platformy observability. |

**Wniosek:** hipotezy z `README.md` opisywały rynek sprzed ~12 miesięcy. Utrzymane w mocy: **cena** i **zamknięty dostęp do własnych danych**.

### Słabości, których nie było na liście, a są realne

7. **Windows jako wymóg** — Redgate (self-hosted), Idera i PerformanceMonitor wymagają Windowsa. Zespoły na Linuksie/Kubernetesie nie mają w tym segmencie darmowej ścieżki. 🔴 duża luka
8. **Brak wielosilnikowości w OSS** — opisana wyżej. 🔴 największa luka
9. **Brak historii w narzędziach MCP** — Postgres MCP Pro odpytuje bazę na żywo; nie odpowie, co działo się wczoraj. 🟠
10. **Brak przejrzystości cenowej** — Redgate i Idera nie publikują cen. Tarcie w procesie zakupowym. 🟠
11. **Bezpieczeństwo MCP jest nierozwiązane** — pierwsze złośliwe pakiety i CVE 9.4 w 2025; brak ustalonych wzorców dla dostępu agenta do baz produkcyjnych. 🟠 **szansa, jeśli PulseDB potraktuje to jako funkcję, nie jako ryzyko**

---

## 3. Realna przewaga PulseDB

Pięć przewag, uszeregowanych według obronności (jak trudno konkurencji je zniwelować):

### 3.1 Wielosilnikowość w jednym panelu 🥇 najbardziej obronna

Estate mieszane PostgreSQL + SQL Server jest w polskim i europejskim sektorze średnich firm normą, a nie wyjątkiem — legacy na SQL Server, nowe usługi na PostgreSQL. Dziś takie zespoły potrzebują dwóch narzędzi albo płacą Datadogowi.

**Dlaczego to jest obronne:** PMM musiałby zbudować wsparcie SQL Server od zera (i nic tego nie zapowiada). Darling musiałby przepisać Windows Service i WPF na wieloplatformowość, a potem nauczyć się PostgreSQL. Oba to kwartały pracy, nie tygodnie.

**Warunek:** to musi być jeden model danych i jeden zestaw pojęć, a nie dwa produkty pod wspólnym logo. Użytkownik ma widzieć „wait events" i „top queries" niezależnie od silnika, z rozwinięciem do szczegółów specyficznych.

### 3.2 API-first jako funkcja darmowa 🥈

Nie „mamy REST API", tylko: **każda funkcja produktu jest dostępna przez API, a Web UI nie ma żadnego uprzywilejowanego dostępu**. Test jest prosty i weryfikowalny: *czy Web UI da się w całości napisać od nowa przez zewnętrzny zespół, korzystając wyłącznie z publicznego API?*

**Dlaczego to jest obronne:** dla Redgate przeniesienie Data API do Standard to kanibalizacja tieru Enterprise. Dla Darlinga oznacza to przebudowę architektury, którą świadomie odrzucił.

**Czym to przekłada się na wartość:** własne dashboardy, integracja z CI/CD (test regresji wydajności na PR), eksport do hurtowni, integracja z systemami zgłoszeń, i — najważniejsze — agent AI.

### 3.3 MCP po historii, zdalny, z twardym modelem uprawnień 🥉

Różnicowanie względem obu istniejących serwerów MCP:
- vs **Postgres MCP Pro**: PulseDB ma historię. „Pokaż, co się działo w nocy z wtorku na środę" jest niemożliwe do zrealizowania przez serwer odpytujący bazę na żywo.
- vs **PerformanceMonitor**: PulseDB udostępnia MCP zdalnie (dla agenta w CI, dla zespołu), nie tylko na localhost.
- vs **wszyscy**: PulseDB nie łączy agenta z bazą produkcyjną — **agent czyta wyłącznie repozytorium PulseDB**. To jest poważna różnica w profilu ryzyka, którą da się sprzedać zespołom bezpieczeństwa.

**Zasady, które trzeba przyjąć od pierwszego dnia:** read-only domyślnie · brak wykonywania SQL na monitorowanej bazie przez MCP · tokeny z zakresem per instancja · audit log każdego wywołania · opcjonalna redakcja tekstów zapytań.

### 3.4 Linux/Docker native

`docker compose up` na dowolnym hoście. Wyklucza z gry Redgate self-hosted, Iderę i PerformanceMonitor jednocześnie.

### 3.5 Load-safety jako obietnica produktu

`sql-monitor` ma już skodyfikowane reguły (`WITH (NOLOCK)`, `SAMPLED` nigdy `DETAILED`, zakaz własnych sesji XE, limity częstotliwości). **To jest materiał na obietnicę marketingową, którą da się zweryfikować**: udokumentowany, mierzony narzut, każde zapytanie kolektora widoczne w repozytorium, deklarowany budżet obciążenia.

Największym lękiem DBA przed narzędziem monitoringowym jest to, że narzędzie samo stanie się problemem. Nikt w OSS nie adresuje tego wprost.

---

## 4. Założenia z `README.md`, które wymagają korekty

| Założenie | Ocena | Rekomendacja |
|-----------|-------|--------------|
| „AI jako opcjonalny klient, nie fundament" | ✅ **trafne i warte utrzymania** | Zgodne z rynkiem. Produkt musi mieć wartość bez AI. Utrzymać. |
| „API-first" | ✅ **trafne, niedoceniane** | To jest najmocniejszy element wizji. Podnieść do rangi głównego przekazu. |
| „MVP: PostgreSQL + SQL Server" | ✅ **trafne, to jest przewaga** | Utrzymać — to jedyna pusta przestrzeń w OSS. |
| „Agentless" | ✅ **trafne** | Zgodne ze standardem segmentu A. |
| „Architektura umożliwia dodanie MySQL, Oracle, innych" | ⚠️ **ryzykowne** | Warstwa adapterów — tak. Deklarowanie kolejnych silników w roadmapie — nie. Patrz [idera-dbwatch.md](competitors/idera-dbwatch.md) §2: to prosta droga do produktu szerokiego i płytkiego. |
| „Web UI + REST API + CLI + MCP" | ⚠️ **cztery interfejsy to dużo** | Utrzymać jako cel architektoniczny; w MVP dowieźć **REST + CLI + MCP** w pełni, Web UI w zakresie 4–5 ekranów. CLI i MCP są tanie, gdy API jest dobre. |
| „Fundament: gear-stack (users, auth, RBAC, OAuth, 2FA)" | ✅ **trafne** | Rozwiązuje krytyczną lukę `sql-monitor`. **Ale:** 2FA i OAuth nie są potrzebne w MVP self-hosted; nie inwestować w nie czasu na starcie. |
| „Cloud/SaaS jako przyszłe źródło przychodu" | ❓ **do przemyślenia** | Patrz §6.3 — dla tej kategorii produktu SaaS jest trudniejszy niż się wydaje. |
| „Self-hosted + open source + MCP jako przewaga" | ❌ **nieaktualne** | Zajęte przez PerformanceMonitor (MIT) w lutym 2026. Przewagą jest wielosilnikowość + API + platforma. |

---

## 5. Decyzja krytyczna: częstotliwość i metoda próbkowania

**To jest najważniejsza decyzja techniczna projektu i trzeba ją podjąć przed pierwszą linią kodu.**

Wartość kategorii DPA bierze się z jednego mechanizmu: **wysokoczęstotliwościowego próbkowania aktywnych sesji z atrybucją czasu oczekiwania do konkretnego zapytania**. DPA robi to co 1 s. `sql-monitor` robi snapshot co 10 min.

To nie jest różnica ilościowa. To dwa różne produkty:

| | Snapshot 10 min | Sampling 1–5 s |
|---|---|---|
| Odpowiada na | „co jest generalnie wolne" | „co się stało o 14:03" |
| Wykrywa incydenty 30-sekundowe | ❌ | ✅ |
| Atrybucja wait → sesja → zapytanie | ❌ (tylko korelacja okna) | ✅ |
| Koszt storage | niski | wysoki (wymaga agregacji i partycjonowania) |
| Pozycjonowanie | „narzędzie do analizy trendów" | „alternatywa dla DPA" |

### Stan techniczny per silnik

- **SQL Server:** próbkowanie `dm_exec_requests` + `dm_os_waiting_tasks` jest wykonalne bez rozszerzeń. Dodatkowo Query Store daje wbudowaną atrybucję (kategorie, nie typy) — `sql-monitor` już to zbiera.
- **PostgreSQL:** ⚠️ **tu jest ukryte ryzyko MVP.** Postgres nie ma wbudowanej historii wait events. Opcje:
  - próbkowanie `pg_stat_activity` z zewnątrz co 1 s — działa bez zmian w bazie, ale gubi krótkie zdarzenia i obciąża połączenie;
  - `pg_wait_sampling` / `pgsentinel` — próbkowanie in-process co 10 ms, jakość klasy ASH, ale wymaga `shared_preload_libraries` i **restartu bazy**.

  Wymóg restartu produkcyjnej bazy przy wdrożeniu narzędzia jest poważną barierą adopcji.

### Rekomendacja

**Zbudować sampler o konfigurowalnej częstotliwości (domyślnie 1 s) jako osobną ścieżkę obok snapshotów metryk, dla obu silników, w MVP.** Dla PostgreSQL: zewnętrzne próbkowanie `pg_stat_activity` jako domyślne (zero wymagań wobec bazy), z **opcjonalnym** wykorzystaniem `pg_wait_sampling`, jeśli rozszerzenie jest obecne — i jawnym komunikatem w UI o różnicy w jakości danych.

**Uzasadnienie:** bez tego PulseDB jest „ładniejszym pgwatch". Z tym — jest jedynym darmowym narzędziem klasy DPA dla dwóch silników. Różnica w postrzeganej wartości jest kilkukrotna, a koszt implementacji to jeden komponent, nie przebudowa produktu — **pod warunkiem, że model danych zostanie zaprojektowany pod to od początku** (patrz [current-project-analysis.md](current-project-analysis.md) §4.2C–D).

---

## 6. Ryzyka

### 6.1 Ryzyko konkurencyjne 🔴 wysokie

**PerformanceMonitor rozwija się w tempie ~3 300 commitów w pół roku, jest darmowy, MIT i ma dystrybucję opartą na osobistej marce autora.** Jeśli doda PostgreSQL albo wersję kontenerową, przewaga PulseDB w segmencie SQL Server znika całkowicie.

*Mitygacja:* nie budować produktu, którego rdzeniem jest SQL Server. Rdzeniem ma być **platforma** (API, adaptery, wielosilnikowość, deployment). Traktować SQL Server jako jeden z dwóch adapterów, nie jako punkt ciężkości.

### 6.2 Ryzyko zakresu 🔴 najwyższe

Zadeklarowany zakres: 2 silniki × 4 interfejsy × (alerty + RBAC + baseline + plany + indeksy) + cloud + enterprise. **To jest zakres zespołu 4–6 osób na 12 miesięcy.**

*Mitygacja:* zakres MVP z §8, bezwzględnie egzekwowany. Każda funkcja spoza listy przechodzi przez pytanie: *„czy bez tego pierwszy użytkownik zewnętrzny zrezygnuje?"*.

### 6.3 Ryzyko modelu biznesowego 🟠

Model open-core wymaga zasobu, którego jeszcze nie ma: **dystrybucji**. PMM ma za sobą Perconę i jej usługi. Darling ma osobistą markę. Grafana miała finansowanie VC. Sam AGPLv3 nie generuje adopcji.

Ponadto **SaaS dla monitoringu baz danych jest trudniejszy, niż się wydaje**: wymaga dostępu sieciowego z chmury do baz klienta (VPN/tunel/agent) — czyli dokładnie tego, czego unika klient wybierający self-hosted. Grupa „chce SaaS, ale nie chce Datadoga" jest wąska.

*Mitygacja:* nie planować przychodu z SaaS jako pierwszego. Realniejsze kolejno: (1) wsparcie i wdrożenia, wzorem Darlinga i Percony; (2) funkcje enterprise self-hosted (SSO/SAML, audyt, HA, rozszerzona retencja); (3) dopiero potem SaaS — i wtedy raczej jako „PulseDB Cloud dla baz w chmurze" (RDS, Azure SQL, Cloud SQL), gdzie problem dostępu sieciowego jest mniejszy.

### 6.4 Ryzyko AGPLv3 🟠

**Za:** sprawdzone w tej dokładnie kategorii (PMM), zatwierdzone przez OSI, chroni przed przejęciem produktu przez hyperscalera, kompatybilne z open core.

**Przeciw:**
- Część korporacji ma polityki zakazujące AGPL w jakiejkolwiek formie — to wycina segment enterprise self-hosted, czyli **dokładnie ten, do którego PulseDB celuje** (sektor regulowany, on-prem, dane niewychodzące na zewnątrz).
- Bezpośredni konkurent jest na MIT. Przy porównaniu „ten sam obszar, liberalniejsza licencja" AGPL bywa rozstrzygający.
- Klauzula sieciowa AGPL rodzi pytania przy narzędziu z REST API — czy udostępnienie API wewnątrz firmy to „interakcja sieciowa"? Odpowiedź prawna jest zwykle uspokajająca, ale **samo pojawienie się pytania w dziale prawnym klienta jest kosztem adopcji**.

*Rekomendacja:* **utrzymać AGPLv3** — ochrona przed strip-miningiem jest realna, a docelowy klient self-hosted i tak nie redystrybuuje produktu. **Ale:** (a) opublikować krótkie, jednoznaczne FAQ licencyjne („używanie wewnętrzne nie rodzi żadnych obowiązków"), (b) rozważyć MIT/Apache dla klienta CLI, biblioteki SDK i definicji serwera MCP — integracje muszą być bezpieczne dla każdego. To jest dokładnie model Grafany (rdzeń AGPL, agenty i pluginy Apache).

### 6.5 Ryzyko techniczne 🟠

- Model danych `sql-monitor` nie udźwignie samplingu 1 s (§4.2C–D analizy projektu). Przeprojektowanie po zebraniu historii u pierwszych użytkowników będzie drogie.
- Podwójna wiedza domenowa (SQL Server + PostgreSQL) — dwa różne zestawy wait events, dwa modele planów, dwie filozofie indeksowania. Konkurenci są jednosilnikowi nie bez powodu.
- Adapter, który powstanie „przy okazji drugiego silnika", będzie przeciekał abstrakcją. Musi powstać pierwszy.

### 6.6 Ryzyko „AI-washing" 🟡

Rynek jest nasycony obietnicami AI. Deklaracja „AI jako opcjonalny dodatek" jest **wiarygodniejsza** niż „AI-powered database optimization" i warto ją utrzymać jako świadomy przekaz, a nie tłumaczyć się z niej.

---

## 7. Czego NIE budować

| Nie budować | Uzasadnienie |
|-------------|--------------|
| **Własnego silnika alertowania z routingiem, eskalacją i on-call** | Przegrana z PagerDuty/Alertmanager/Grafaną. Robić: detekcja + webhook + Slack/e-mail. |
| **Własnego systemu dashboardów budowanych przez użytkownika** | To jest Grafana. Robić: kilka doskonałych, opiniotwórczych widoków + endpoint `/metrics` dla Grafany. |
| **Wsparcia dla Oracle, MySQL, MongoDB w horyzoncie 12 miesięcy** | Prosta droga do produktu szerokiego i płytkiego ([idera-dbwatch.md](competitors/idera-dbwatch.md) §2). |
| **Agenta (agent mode)** | Agentless pokrywa 95% przypadków. Agent to dodatkowy artefakt do budowania, podpisywania, aktualizowania i wspierania. Zostawić jako możliwość architektoniczną, nie jako pracę. |
| **Własnego formatu/silnika time-series** | PostgreSQL + partycjonowanie lub TimescaleDB. |
| **Własnej wizualizacji planów wykonania od zera** | Bardzo kosztowna. W MVP: przechowywanie XML/JSON planu + eksport + odnośnik do istniejących wizualizatorów. Darling ma 30-regułowy analizator — nie ma sensu ścigać się w wersji 1.0. |
| **Automatycznego wykonywania rekomendacji (auto-tuning, auto-index)** | Zaufanie DBA jest tu zerowe, a ryzyko produkcyjne wysokie. Rekomendacja + gotowy DDL do skopiowania — tak. Wykonanie — nie. |
| **2FA, OAuth, SSO w MVP** | `gear-stack` je ma, ale w self-hosted MVP nikt ich nie potrzebuje. Zostawić jako funkcję enterprise. |
| **Deployment tracking i korelacji z CI/CD w MVP** | Wymaga integracji po stronie klienta. Wysoki koszt, wąska grupa. |
| **Wsparcia dla estate 200+ instancji** | Projektować pod 5–30. Widok floty dla 200 serwerów to inny produkt. |
| **Zapisu przez MCP (agent modyfikujący konfigurację)** | Darling to ma; PulseDB powinien **świadomie tego nie robić** i uczynić z tego argument bezpieczeństwa. |

---

## 8. Rekomendowany zakres MVP

**Kryterium:** najmniejszy zakres, który jest jednocześnie (a) użyteczny dla realnego DBA, (b) niemożliwy do zastąpienia przez PerformanceMonitor, pgwatch ani PMM.

### Faza 0 — fundament (przed jakąkolwiek funkcją)
1. Warstwa adapterów silnika (`EngineAdapter`) z dwiema implementacjami od pierwszego dnia
2. Model danych: wymiar `query`/`plan` + fakty time-series, `TIMESTAMPTZ`, partycjonowanie/TimescaleDB
3. Poświadczenia w bazie PulseDB, szyfrowane; zero sekretów w plikach montowanych do kontenerów
4. Auth z `gear-stack` (użytkownik + hasło + RBAC; bez OAuth/2FA)
5. `LICENSE` (AGPLv3) + FAQ licencyjne + CI (lint, typy, testy)

### Faza 1 — rdzeń diagnostyczny
6. **Sampler aktywnych sesji, 1 s, oba silniki** — z atrybucją wait → sesja → zapytanie (§5)
7. Top queries z historią (SQL Server: DMV + Query Store; PostgreSQL: `pg_stat_statements`)
8. Plany wykonania — pobieranie i przechowywanie, wykrywanie zmiany planu
9. Analiza indeksów: brakujące, nieużywane, fragmentacja/bloat, z gotowym DDL
10. Blokady i deadlocki

### Faza 2 — produkt
11. **REST API pokrywające 100% powyższego**, z OpenAPI (to jest deliverable, nie efekt uboczny)
12. CLI (w tym wyjście markdown — format pod agenta AI)
13. Serwer MCP: zdalny, read-only, z zakresami tokenów i audit logiem
14. Web UI: **5 ekranów** — Overview floty, Waits (główny wykres w stylu DPA), Queries, Indexes, Instance detail
15. Alerty: **10–12 typów** z sensownymi domyślnymi progami, kanały: webhook + Slack + e-mail
16. Endpoint `/metrics` w formacie Prometheus

### Poza MVP (świadomie)
Baseline'y i wykrywanie anomalii · raporty i harmonogramy · SSO/SAML · multi-tenancy · HA · cloud · agent mode · kolejne silniki · wizualizator planów

---

## 9. Rekomendacje kolejnych kroków (research → planning)

1. **Rozstrzygnąć §5 (sampling) przed pisaniem planu architektury.** To jest rozwidlenie, po którym wszystko inne wygląda inaczej.
2. **Zweryfikować hipotezę o estate mieszanych empirycznie.** 5–10 rozmów z DBA/leadami: czy naprawdę mają PostgreSQL i SQL Server obok siebie i czy naprawdę boli ich przełączanie narzędzi. Cała teza produktu stoi na tym założeniu, a jest ono dziś 🟡.
3. **Zainstalować PerformanceMonitor (edycja Lite) i przejść jego workflow diagnostyczny.** Godzina pracy, która powie o poprzeczce jakości więcej niż cały ten dokument.
4. **Przeprowadzić spike `pg_wait_sampling` vs zewnętrzne próbkowanie `pg_stat_activity`** na realnej bazie — zmierzyć różnicę w jakości danych i narzut.
5. **Zdecydować o pozycjonowaniu jednym zdaniem** i trzymać się go. Propozycja:
   > *„PulseDB — diagnostyka wydajności PostgreSQL i SQL Server w jednym panelu. Self-hosted, API-first, bez licencji per instancja."*
6. **Ustalić kryterium zamknięcia projektu (kill criteria) już teraz** — np. „jeśli po 6 miesiącach od publikacji nie ma 3 zewnętrznych wdrożeń produkcyjnych, wracamy do narzędzia wewnętrznego". Projekty open source bez tego kryterium żyją latami bez użytkowników.

---

## Powiązane
- [market-overview.md](market-overview.md) — krajobraz rynku i trendy
- [comparison-matrix.md](comparison-matrix.md) — macierz funkcji i architektury
- [current-project-analysis.md](current-project-analysis.md) — co przenieść z `sql-monitor`
- [competitors/opensource.md](competitors/opensource.md) — analiza najważniejszego konkurenta
