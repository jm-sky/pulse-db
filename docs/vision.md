# PulseDB — wizja i pozycjonowanie

**Data:** 2026-07-30 · **Status:** `verification needed`
**Podstawa:** [research/opportunities.md](research/opportunities.md), [research/market-overview.md](research/market-overview.md), [research/comparison-matrix.md](research/comparison-matrix.md)
**Legenda pewności:** ✅ potwierdzone źródłem · 🟡 założenie do weryfikacji · ❓ otwarte

Ten dokument jest kontraktem na **„nie"**. PRD i roadmapa muszą się z niego wynikać; wszystko, co jest z nim sprzeczne, wymaga najpierw zmiany tego pliku.

---

## 1. Pozycjonowanie

> **PulseDB — diagnostyka wydajności PostgreSQL i SQL Server w jednym panelu. Self-hosted, API-first, bez licencji per instancja.**

Jedno zdanie, jeden przekaz. Nie rozszerzamy go o AI, o chmurę, o kolejne silniki ani o „observability".

### Czym PulseDB jest

Narzędziem klasy **Database Performance Analysis** (segment A rynku) dystrybuowanym w modelu **open source self-hosted** (segment D). Odpowiada na pytanie *„dlaczego to zapytanie było wolne o 14:03"* — nie na *„czy serwer żyje"*.

### Czym PulseDB nie jest

- nie jest platformą observability (to Datadog / Grafana),
- nie jest systemem alertowania z on-call i eskalacją (to PagerDuty / Alertmanager),
- nie jest builderem dashboardów (to Grafana),
- nie jest narzędziem do monitoringu infrastruktury,
- nie jest produktem AI-first.

### Dlaczego to jest wolne miejsce ✅

Trzy fakty z researchu:

1. **Nikt w OSS nie obsługuje PostgreSQL i SQL Server równorzędnie** — PMM nie ma SQL Server, pgwatch to tylko Postgres, PerformanceMonitor to tylko SQL Server i tylko Windows.
2. **Nikt w segmencie A+D nie daje darmowego, pierwszorzędnego API domenowego** — u Redgate to tier Enterprise, u Darlinga nie istnieje („no APIs"), u reszty OSS to API metryk, nie API domenowe.
3. **Zespoły na Linuksie/Kubernetesie nie mają w tym segmencie darmowej ścieżki** — Redgate self-hosted, Idera i PerformanceMonitor wymagają Windowsa.

### Czego już nie deklarujemy ❌

Otwartość kodu, self-hosting i integracja MCP **przestały być przewagą** w lutym 2026, gdy Erik Darling opublikował `PerformanceMonitor` (MIT, ~3 300 commitów w pół roku, 74 narzędzia MCP) ✅. Wymienianie ich jako wyróżników jest dziś nieprawdą rynkową. Są to **wymagania wstępne**, nie argumenty.

---

## 2. Docelowy użytkownik

**ICP:** zespół IT utrzymujący **5–30 instancji baz danych w estate mieszanym PostgreSQL + SQL Server**, na Linuksie lub w Dockerze, bez budżetu na 20–50 tys. USD/rok za licencje komercyjne ✅ lub z wymogiem, by dane monitoringu nie opuszczały infrastruktury.

Trzy sytuacje, w których PulseDB wygrywa:

| Sytuacja | Dziś klient robi | Z PulseDB |
|---|---|---|
| Legacy na SQL Server, nowe usługi na PostgreSQL | dwa osobne narzędzia albo Datadog | jeden panel, jeden model pojęć |
| Sektor regulowany, on-prem, dane nie wychodzą | skrypty własne albo nic | self-hosted, zero telemetrii |
| Chce zintegrować diagnostykę z CI/CD, hurtownią, agentem AI | płaci za tier Enterprise albo pisze zapytania do cudzego storage | pełne API domenowe za darmo |

**Skala, pod którą projektujemy: 5–30 instancji.** Widok floty dla 200+ serwerów to inny produkt i świadomie go nie budujemy.

**Założenie krytyczne 🟡:** że estate mieszane PostgreSQL + SQL Server są w europejskim sektorze średnich firm normą, a przełączanie się między dwoma narzędziami jest realnym bólem. **Cała teza produktu stoi na tym założeniu, a nie jest ono potwierdzone.** Weryfikacja: 5–10 rozmów z DBA/leadami przed zamknięciem PRD ([opportunities.md](research/opportunities.md) §9.2).

---

## 3. Pięć zasad produktu

Zasady, nie funkcje. Każda jest wyborem, który da się złamać jedną złą decyzją implementacyjną — dlatego są tutaj, a nie w PRD.

### 3.1 Jeden model danych dla wszystkich silników 🥇

Użytkownik widzi „wait events" i „top queries" niezależnie od silnika, z rozwinięciem do szczegółów specyficznych. **Nie dwa produkty pod wspólnym logo.**

Warstwa adapterów (`EngineAdapter`) powstaje **przed** pierwszym kolektorem i od pierwszego dnia ma dwie implementacje. Adapter, który powstanie „przy okazji drugiego silnika", będzie przeciekał abstrakcją.

*Dlaczego to jest obronne:* PMM musiałby zbudować SQL Server od zera. Darling musiałby przepisać Windows Service i WPF na wieloplatformowość, a potem nauczyć się PostgreSQL. Kwartały pracy, nie tygodnie.

### 3.2 API jest produktem, UI jest klientem 🥈

Nie „mamy REST API", ale: **każda funkcja produktu jest dostępna przez API, a Web UI nie ma żadnego uprzywilejowanego dostępu.**

Test akceptacyjny, weryfikowalny i niepodlegający negocjacji:

> *Czy zewnętrzny zespół potrafi napisać Web UI PulseDB od nowa, korzystając wyłącznie z publicznego, udokumentowanego API?*

Jeśli w kodzie pojawi się endpoint „dla frontendu" albo zapytanie do bazy z pominięciem warstwy API — zasada jest złamana.

*Dlaczego to jest obronne:* dla Redgate przeniesienie Data API do Standard kanibalizuje tier Enterprise. Dla Darlinga to przebudowa architektury, którą świadomie odrzucił.

### 3.3 MCP po historii, zdalny, read-only 🥉

Trzy różnice względem obu istniejących serwerów MCP:

- **vs Postgres MCP Pro:** PulseDB ma historię. „Pokaż, co się działo w nocy z wtorku na środę" jest nieosiągalne dla serwera odpytującego bazę na żywo.
- **vs PerformanceMonitor:** PulseDB udostępnia MCP zdalnie (agent w CI, cały zespół), nie tylko na localhost.
- **vs wszyscy:** **agent nigdy nie łączy się z monitorowaną bazą — czyta wyłącznie repozytorium PulseDB.**

Zasady obowiązujące od pierwszego dnia: read-only domyślnie · zero wykonywania SQL na monitorowanej bazie przez MCP · tokeny z zakresem per instancja · audit log każdego wywołania · opcjonalna redakcja tekstów zapytań.

Bezpieczeństwo MCP jest w 2026 nierozwiązane (pierwszy złośliwy pakiet MCP we wrześniu 2025, CVE 9.4 w 2025) ✅. Traktujemy to jako **funkcję produktu, nie jako ryzyko do przemilczenia**.

### 3.4 Linux/Docker native

`docker compose up` na dowolnym hoście. Windows nie jest wymagany nigdzie — ani do uruchomienia, ani do obsługi. To jednocześnie wyklucza z porównania Redgate self-hosted, Iderę i PerformanceMonitor.

### 3.5 Load-safety jako mierzalna obietnica

Największym lękiem DBA przed narzędziem monitoringu jest to, że narzędzie samo stanie się problemem. Nikt w OSS nie adresuje tego wprost.

PulseDB deklaruje **budżet narzutu, mierzy go i publikuje**. Każde zapytanie kolektora jest widoczne w repozytorium. Reguły przeniesione z `sql-monitor`: `WITH (NOLOCK)`, `SAMPLED` nigdy `DETAILED`, zakaz własnych sesji Extended Events, limity częstotliwości.

To jest obietnica marketingowa, którą da się zweryfikować — dlatego wolno ją składać.

---

## 4. Rdzeń techniczny: sampling ✅ zdecydowane

**Decyzja (2026-07-30):** PulseDB buduje **sampler aktywnych sesji o konfigurowalnej częstotliwości, domyślnie 1 s, dla obu silników, w MVP** — jako osobną ścieżkę obok snapshotów metryk.

Dla PostgreSQL: zewnętrzne próbkowanie `pg_stat_activity` jako **domyślne** (zero wymagań wobec monitorowanej bazy, brak restartu), z **opcjonalnym** wykorzystaniem `pg_wait_sampling`, jeśli rozszerzenie jest obecne — i jawnym komunikatem w UI o różnicy w jakości danych.

*Uzasadnienie:* wartość całej kategorii DPA bierze się z jednego mechanizmu — wysokoczęstotliwościowego próbkowania aktywnych sesji z atrybucją czasu oczekiwania do konkretnego zapytania (DPA robi to co 1 s ✅). Snapshot co 10 min odpowiada na „co jest generalnie wolne"; sampling 1 s odpowiada na „co się stało o 14:03" i wykrywa incydenty 30-sekundowe. **To nie różnica ilościowa — to dwa różne produkty.** Bez samplera PulseDB jest „ładniejszym pgwatch", nie darmowym DPA.

*Konsekwencja wiążąca:* model danych musi być zaprojektowany pod sampling **od pierwszej migracji** — wymiary `query`/`plan` + fakty time-series, `TIMESTAMPTZ`, partycjonowanie deklaratywne lub TimescaleDB. Przeprojektowanie po zebraniu historii u pierwszych użytkowników będzie drogie. Szczegóły → ADR modelu danych.

Pełna analiza wariantów: [opportunities.md](research/opportunities.md) §5.

---

## 5. Zakres

Rdzeniem produktu jest **platforma** (API, adaptery, wielosilnikowość, deployment) — **nie SQL Server i nie PostgreSQL**. Oba silniki są adapterami. Ta różnica jest mitygacją głównego ryzyka konkurencyjnego (§7.1).

Szczegółowy zakres i fazy → `docs/roadmap.md` i `docs/prd.md`. Tutaj tylko granica.

### W zakresie MVP

Sampler sesji 1 s (oba silniki, z atrybucją wait → sesja → zapytanie) · top queries z historią · plany wykonania z detekcją zmiany planu · analiza indeksów z gotowym DDL · blokady i deadlocki · REST API pokrywające 100% powyższego z OpenAPI · CLI · zdalny serwer MCP · Web UI w zakresie 5 ekranów · alerty (detekcja + webhook/Slack/e-mail) · endpoint `/metrics`.

Auth: użytkownik + hasło + RBAC z `gear-stack`. **Bez OAuth i 2FA** — są w kodzie boilerplate'u, ale wyłączone i nieeksponowane.

### Poza MVP — świadomie odłożone

Baseline'y i detekcja anomalii · raporty i harmonogramy · SSO/SAML · multi-tenancy · HA · cloud · agent mode · kolejne silniki · wizualizator planów.

### Non-goals — czego nie budujemy wcale w horyzoncie 12 miesięcy

| Nie budujemy | Powód |
|---|---|
| Silnika alertowania z routingiem, eskalacją, on-call | Przegrana z PagerDuty/Alertmanager/Grafaną. Robimy: detekcja + webhook |
| Systemu dashboardów budowanych przez użytkownika | To jest Grafana. Robimy: kilka doskonałych widoków opiniotwórczych + `/metrics` |
| Wsparcia dla Oracle, MySQL, MongoDB | Prosta droga do produktu szerokiego i płytkiego |
| Agenta (agent mode) | Agentless pokrywa ~95% przypadków. Zostaje jako możliwość architektoniczna, nie jako praca |
| Własnego silnika time-series | PostgreSQL + partycjonowanie albo TimescaleDB |
| Wizualizatora planów od zera | Bardzo kosztowny. W MVP: przechowywanie XML/JSON + eksport + odnośnik do istniejących wizualizatorów |
| Auto-tuningu i auto-index | Zaufanie DBA zerowe, ryzyko produkcyjne wysokie. Rekomendacja + DDL do skopiowania — tak. Wykonanie — nie |
| Zapisu przez MCP | Darling to ma; my świadomie nie — i czynimy z tego argument bezpieczeństwa |
| Wsparcia dla estate 200+ instancji | Inny produkt |
| Deployment tracking / korelacji z CI/CD w MVP | Wymaga integracji po stronie klienta. Wysoki koszt, wąska grupa |

**Reguła egzekwowania zakresu:** każda funkcja spoza listy MVP przechodzi przez pytanie *„czy bez tego pierwszy użytkownik zewnętrzny zrezygnuje?"*. Odpowiedź „byłoby miło" znaczy „nie teraz".

### Miejsce AI

AI jest **opcjonalnym klientem, nie fundamentem**. PulseDB musi mieć pełną wartość bez AI. Użytkownik podłącza własny model przez API/CLI/MCP — Claude Code, Cursor, ChatGPT, Gemini, OpenRouter, model własny. Zero zależności od jednego dostawcy, zero funkcji, które bez AI przestają działać.

Rynek jest nasycony obietnicami AI; deklaracja „AI jako dodatek" jest **wiarygodniejsza** niż „AI-powered database optimization". Utrzymujemy ją jako świadomy przekaz, nie tłumaczymy się z niej.

---

## 6. Licencja i monetyzacja

### Licencja: AGPLv3 dla rdzenia ✅ utrzymane

Sprawdzone w tej dokładnie kategorii (PMM, Grafana), zatwierdzone przez OSI, chroni przed strip-miningiem, kompatybilne z open core. Docelowy klient self-hosted nie redystrybuuje produktu, więc realny koszt licencji jest dla niego zerowy.

Dwa działania obowiązkowe, bo AGPL ma koszt adopcji ⚠️:

1. **Krótkie, jednoznaczne FAQ licencyjne** — „używanie wewnętrzne nie rodzi żadnych obowiązków". Klauzula sieciowa AGPL rodzi pytania przy produkcie z REST API, a samo pojawienie się pytania w dziale prawnym klienta jest kosztem.
2. **Liberalna licencja dla integracji ❓ do ADR** — klient CLI, biblioteka SDK i definicja serwera MCP na MIT/Apache. Model Grafany: rdzeń AGPL, agenty i pluginy Apache. Integracje muszą być bezpieczne dla każdego.

Świadomie przyjęte ryzyko: część korporacji ma polityki zakazujące AGPL, co wycina fragment segmentu enterprise self-hosted — czyli częściowo tego, do którego celujemy. Bezpośredni konkurent jest na MIT.

### Kolejność monetyzacji — odwrócona względem pierwotnych założeń

1. **Wsparcie i wdrożenia** — wzorem Darlinga (500 / 2 500 USD/rok) i Percony ✅
2. **Funkcje enterprise self-hosted** — SSO/SAML, audyt, HA, rozszerzona retencja
3. **SaaS — dopiero potem i tylko dla baz w chmurze** (RDS, Azure SQL, Cloud SQL)

*Dlaczego SaaS jest ostatni:* wymaga dostępu sieciowego z chmury do baz klienta (VPN/tunel/agent) — czyli dokładnie tego, czego unika klient wybierający self-hosted. Grupa „chce SaaS, ale nie chce Datadoga" jest wąska. **Nie planujemy przychodu z SaaS jako pierwszego.**

*Nierozwiązane ❓:* model open-core wymaga zasobu, którego jeszcze nie mamy — **dystrybucji**. PMM ma za sobą Perconę, Darling osobistą markę, Grafana miała VC. Sam AGPLv3 nie generuje adopcji. Strategia dystrybucji jest luką w tej wizji i wymaga osobnej decyzji.

---

## 7. Ryzyka, które kształtują wizję

### 7.1 Konkurencyjne 🔴 wysokie

PerformanceMonitor rozwija się w tempie ~3 300 commitów w pół roku, jest darmowy, MIT, z dystrybucją opartą na osobistej marce autora ✅. **Jeśli doda PostgreSQL albo wersję kontenerową, przewaga PulseDB w segmencie SQL Server znika całkowicie.**

*Mitygacja wbudowana w wizję:* rdzeniem jest platforma, nie SQL Server (§5).

### 7.2 Zakresu 🔴 najwyższe

Research ocenia pierwotnie zadeklarowany zakres (2 silniki × 4 interfejsy × alerty × RBAC × baseline × plany × indeksy + cloud + enterprise) na **zespół 4–6 osób na 12 miesięcy**. Realna kapacja: **jedna osoba na pełnym zaangażowaniu.**

*Mitygacja:* lista non-goals z §5 i reguła egzekwowania zakresu. Roadmapa musi być **sekwencyjna, nie równoległa** — sampler przed alertami, API przed UI, adapter przed kolektorami. To jest najpoważniejsze ryzyko projektu i jedyne, na które mamy pełny wpływ.

### 7.3 Techniczne 🟠

Podwójna wiedza domenowa (dwa zestawy wait events, dwa modele planów, dwie filozofie indeksowania). Konkurenci są jednosilnikowi nie bez powodu. Model danych musi udźwignąć sampling 1 s od początku (§4).

---

## 8. Kryteria sukcesu i kill criteria

Projekty open source bez kryterium zamknięcia żyją latami bez użytkowników. Poniższe progi są **propozycją 🟡 wymagającą Twojej akceptacji** — liczby, nie intencje.

### Sukces MVP (moment publikacji)

- Sampler 1 s działa na obu silnikach, z **udokumentowanym i zmierzonym** narzutem
- Test API-first z §3.2 przechodzi
- `docker compose up` → działający monitoring w < 15 minut na czystym hoście
- Agent AI (Claude Code / Cursor) odpowiada na „co było wolne wczoraj w nocy" wyłącznie przez MCP PulseDB

### Sukces adopcji — 6 miesięcy od publikacji

- **3 zewnętrzne wdrożenia produkcyjne** (nie gwiazdki, nie klony repo — działające instalacje u kogoś innego)
- Co najmniej 1 wdrożenie w estate mieszanym PG + SQL Server — empiryczne potwierdzenie założenia z §2

### Kill criteria

> Jeśli **6 miesięcy po publikacji** nie ma **3 zewnętrznych wdrożeń produkcyjnych**, PulseDB wraca do roli narzędzia wewnętrznego: przestajemy inwestować w onboarding, dokumentację publiczną i community, utrzymujemy tylko to, co sami używamy.

Dodatkowe kryterium wcześniejsze: jeśli rozmowy walidacyjne z §2 **obalą założenie o estate mieszanych**, wracamy do tego dokumentu przed rozpoczęciem Fazy 1 — bo wtedy upada zasada 3.1, a z nią całe pozycjonowanie.

---

## 9. Decyzje wciąż otwarte ❓

| Decyzja | Gdzie zostanie rozstrzygnięta |
|---|---|
| Model danych: partycjonowanie deklaratywne vs TimescaleDB | ADR modelu danych (przed Fazą 0) |
| Split licencyjny rdzeń AGPL / integracje MIT | ADR licencyjny |
| Strategia dystrybucji i budowania adopcji | osobny dokument — luka w tej wizji (§6) |
| Zakres 5 ekranów Web UI i frontend stack | `docs/prd.md` |
| Granica Cloud vs Enterprise | odłożone; osobny plan gdy pojawi się Cloud |

---

## Powiązane

- [../README.md](../README.md) — README projektu (wymaga aktualizacji do tego dokumentu)
- [research/opportunities.md](research/opportunities.md) — źródło rekomendacji produktowych
- [research/market-overview.md](research/market-overview.md) — krajobraz rynku, ceny, trendy 2026
- [research/current-project-analysis.md](research/current-project-analysis.md) — co przenieść z `sql-monitor`
- [plans/2026-07-30-boilerplate-from-family.md](plans/2026-07-30-boilerplate-from-family.md) — fundament techniczny w budowie
