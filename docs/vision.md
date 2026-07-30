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

## 3. Siedem zasad produktu

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

PulseDB deklaruje **budżet narzutu, mierzy go i publikuje**. Każde zapytanie kolektora jest widoczne w repozytorium. Reguły domyślne, przeniesione z `sql-monitor`: `WITH (NOLOCK)`, `SAMPLED` zamiast `DETAILED`, brak własnych sesji Extended Events, limity częstotliwości.

To jest obietnica marketingowa, którą da się zweryfikować — dlatego wolno ją składać.

**Domyślnie bezpieczny, na żądanie głęboki.** Powyższe reguły są **domyślne, nie absolutne**. DBA może włączyć **tryb głębokiego badania** ze świadomą akceptacją chwilowego obniżenia wydajności instancji.

Uzasadnienie nie jest kompromisem, lecz wzmocnieniem tej zasady: **zakaz nie eliminuje ryzyka, tylko wypycha je poza nasz zasięg.** DBA, który potrzebuje `DETAILED`, uruchomi to ręcznie w SSMS — bez limitu czasu, bez pomiaru narzutu, bez wpisu w audycie i bez oznaczenia okna w historii. Opt-in z zabezpieczeniami jest lepszą kontrolą niż zakaz.

Deep mode **dziedziczy ramę zgody z §3.6** (per instancja · osobne uprawnienie RBAC · potwierdzenie · audit log · bezpiecznik deploymentowy) i dokłada trzy warunki, których akcje naprawcze nie potrzebują — bo akcja jest dyskretna i jednorazowa, a deep mode działa w sposób ciągły:

1. **Time-box z automatycznym wygaszeniem** — „włącz na 15 minut", twardy termin, nie przełącznik. Tryb awarii do uniknięcia: włączone w trakcie incydentu o 2 w nocy, nikt nie wyłączył, miesiąc później narzędzie jest winne chronicznego narzutu.
2. **Auto-abort po przekroczeniu budżetu narzutu** — mierzymy własny narzut i tak, więc deep mode potrafi się sam ubić. „Akceptuję ryzyko" staje się „ryzykiem z bezpiecznikiem".
3. **Oznaczenie okna w danych** + baner w UI — okres z deep mode ma inną charakterystykę; bez znacznika zanieczyszcza własną historię i porównania okresów (§5) kłamią.

Zakres trybu głębokiego:

| Operacja | Uwaga | Kiedy |
|---|---|---|
| `DETAILED` fragmentacja indeksów (SQL Server) | pełny skan, ciężkie IO, ale skończone | **MVP** |
| Podniesiona częstotliwość samplingu (poniżej 1 s) | ciągłe — wymaga time-boxa | **MVP** |
| Odczyt spójny (rezygnacja z `NOLOCK`) | ryzyko blokowania | v0.2 |
| Własna sesja Extended Events | osobny artefakt do zarządzania | później |
| `pgstattuple` — dokładny bloat (PostgreSQL) | rozszerzenie, wzorzec opt-in-if-present | v0.2 |
| `EXPLAIN` bez `ANALYZE` | nic nie wykonuje — dozwolone zawsze, nie wymaga deep mode | MVP |
| `EXPLAIN (ANALYZE)` | ⚠️ **`EXPLAIN ANALYZE` na `UPDATE` wykonuje ten `UPDATE`.** Wyłącznie dla `SELECT`, po jawnej weryfikacji typu zapytania | poza MVP |

### 3.6 Rozdział zbierania od działania — niezmiennik

> **Ścieżka zbierania danych jest zawsze read-only.** Zapis do monitorowanej bazy jest możliwy wyłącznie jako **jawna, nazwana akcja naprawcza, zainicjowana przez człowieka, na osobnych poświadczeniach, zapisana w audycie**. Agent AI nie ma prawa zapisu nigdy. Nie udostępniamy wykonywania dowolnego SQL.

Uzasadnienie odejścia od prostszego „nigdy nie piszemy": rekomendacja, której nie da się wykonać w tym samym narzędziu, to połowa produktu. Kopiowanie DDL do zewnętrznego klienta jest tarciem, które sprawia, że narzędzia diagnostyczne kończą jako „ładne wykresy". Zapis jest **wartością UX** — pod warunkiem, że jest ograniczony konstrukcyjnie, a nie regulaminowo.

**Dwa połączenia, nie jedno.** To jest sedno niezmiennika:

| Połączenie | Uprawnienia | Domyślnie |
|---|---|---|
| Kolektor | bez prawa zapisu — `pg_monitor` (PostgreSQL), `VIEW SERVER STATE` / `VIEW DATABASE STATE` (SQL Server) | zawsze, obowiązkowo |
| Akcje naprawcze | podwyższone, nadane świadomie przez klienta | **nieustawione** |

Dzięki temu gwarancja narzutu i bezpieczeństwa kolektora (§3.5) obowiązuje **niezależnie** od tego, czy tryb akcji jest włączony — nie trzeba jej za każdym razem renegocjować.

**Warunki włączenia trybu akcji** — wszystkie obowiązkowe. Ta sama rama obsługuje **tryb głębokiego badania** z §3.5; nie budujemy dwóch mechanizmów zgody:

- osobne uprawnienie RBAC, odrębne od `admin` i od odczytu
- włączanie **per instancja**, nie globalnie (produkcja off, staging on)
- podgląd dokładnego SQL przed wykonaniem + jawne potwierdzenie
- wpis w audit logu: kto, kiedy, co, na czym, z jakim skutkiem
- **bezpiecznik deploymentowy**: zmienna środowiskowa wymuszająca read-only dla całej instalacji, nieprzestawialna z UI — żeby dział bezpieczeństwa mógł zagwarantować tryb tylko do odczytu dowodliwie, a nie na słowo

**Agent AI nie dostaje zapisu — i to nie podlega konfiguracji.** Asymetria jest strukturalna: człowiek klikający „Wykonaj" działa świadomie, jednorazowo i atrybutowalnie. Agent przez MCP czyta **teksty zapytań pochodzące z monitorowanej bazy** — czyli treść wprowadzoną przez użytkowników aplikacji klienta. Agent z prawem zapisu jest ścieżką prompt injection z danych aplikacyjnych do DDL na produkcji. Bezpieczeństwo MCP jest w 2026 nierozwiązane (§3.3); tu granica zostaje.

**Konsola dowolnego SQL — non-goal trwały.** Endpoint wykonujący dowolny SQL czyni z PulseDB ścieżkę zdalnego wykonania kodu do każdej monitorowanej bazy, z naszym auth jako jedyną bramką. Wyliczony katalog akcji (§5) da się zaudytować; „execute" nie. Poza tym nie jesteśmy klientem SQL — tym są DBeaver, SSMS i psql.

**Świadomy koszt:** „PulseDB nigdy nie pisze" było własnością weryfikowalną przez sprawdzenie grantów. „PulseDB pisze tylko gdy włączysz" jest polityką, którą audytor musi sprawdzić w konfiguracji. Dla sektora regulowanego to realna różnica; odzyskujemy ją częściowo bezpiecznikiem deploymentowym.

**Rozszerzenia doradcze** (`pg_wait_sampling` w §4, `hypopg` w §5) instaluje klient z własnej woli. PulseDB ich nie instaluje, nie wymaga i działa bez nich — wykrywa je i korzysta, jeśli są.

### 3.7 Jeden łańcuch diagnostyczny, bez ślepych zaułków

Narzędzie diagnostyczne, w którym widać *że* jest problem, ale nie da się dojść *dlaczego*, jest zbiorem wykresów. Wartość powstaje w przejściu od objawu do przyczyny — i to przejście musi być jedną spójną ścieżką, klikalną na każdym kroku:

```
ostrzeżenie / wykres → okno czasu → typ wait → sesja → zapytanie → plan → rekomendacja → akcja → zmierzony skutek
```

**DPA kończy ten łańcuch na rekomendacji.** PulseDB ma o dwa ogniwa więcej — akcję naprawczą (§3.6) i rejestr skutków (§5) — więc łańcuch jest **domknięty**, a nie tylko dłuższy. To jest UX-owy sens wszystkich pozostałych decyzji z tego dokumentu.

**Wzorce kopiujemy, nie wymyślamy.** Research jest tu kategoryczny ([solarwinds-dpa.md](research/competitors/solarwinds-dpa.md) §8.1):

- **Główny widok = stacked bar chart czasu odpowiedzi wg typu wait na osi czasu, klikalny w dół.** To jest wzorzec branżowy, po którym rozpoznaje się kategorię. Nie projektujemy własnego.
- **Widok floty = kafle instancji z natychmiastową identyfikacją problemu** — wzorzec Redgate, najlepszy w kategorii ✅.
- **Rekomendacja zawsze z uzasadnieniem i dowodami**, nigdy samo „dodaj indeks" (§5, poziom 1).
- **Lista ostrzeżeń jako punkt wejścia** do łańcucha, nie jako osobna zakładka bez wyjścia.

**Zasada braku ślepego zaułka:** każda liczba, słupek i wiersz na ekranie musi prowadzić do swojej przyczyny albo do surowych danych. Element, którego nie da się kliknąć, wymaga uzasadnienia.

**Dlaczego to jest przewaga, a nie kosmetyka.** Lider kategorii ma UI, który „wygląda i działa jak aplikacja z 2015 roku, ciężki, oparty o Javę" 🟡 (powtarzalne w recenzjach). Darmowy konkurent ma jako główny interfejs aplikację desktopową WPF na Windows, a web dashboard read-only i domyślnie wyłączony ✅. **Nowoczesny web UI jest w tym segmencie luką, nie ozdobą.**

**Uwaga na złe odczytanie §3.2.** „API jest produktem, UI jest klientem" to zdanie o architekturze — o braku uprzywilejowanego dostępu — **nie o jakości UI**. UI jest tym klientem, który decyduje, czy ktokolwiek zacznie z produktu korzystać. Mantra API-first pod presją czasu potrafi wyprodukować dokładnie tę słabość, która pogrąża DPA w recenzjach.

**Jak utrzymać wysoką poprzeczkę przy jednej osobie** — trzy ograniczenia, nie większy budżet:

1. **Mało ekranów, każdy dopracowany** (§5). Jeśli czasu brakuje, spada *liczba* ekranów, nigdy ich jakość.
2. **Sprawdzone wzorce zamiast własnych** — patrz wyżej.
3. **Biblioteka komponentów, nie własny design system.** Stack odziedziczony z boilerplate'u ✅: Vue 3 + Vite + Tailwind 4 + shadcn-vue (reka-ui) + TanStack Query/Table + axios. Do rozstrzygnięcia zostaje **biblioteka wykresów** — w tym produkcie najtrudniejsza decyzja frontendowa, bo główny widok to interaktywny stacked bar na osi czasu z drill-inem (§9).

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

Sampler sesji 1 s (oba silniki, z atrybucją wait → sesja → zapytanie) · top queries z historią · plany wykonania z detekcją zmiany planu · analiza indeksów z gotowym DDL · blokady i deadlocki · **porównanie okresów i regresja zapytania** · **baseline sezonowy z percentyli** · **rejestr rekomendacji ze zmierzonym skutkiem** · **szkielet akcji naprawczych + `KILL SESSION` i `ANALYZE`/`UPDATE STATISTICS`** (opt-in, §3.6) · **tryb głębokiego badania** (opt-in, §3.5) · REST API pokrywające 100% powyższego z OpenAPI · CLI · zdalny serwer MCP · Web UI w zakresie 5 ekranów · alerty (detekcja + webhook/Slack/e-mail) · endpoint `/metrics`.

Auth: użytkownik + hasło + RBAC z `gear-stack`. **Bez OAuth i 2FA** — są w kodzie boilerplate'u, ale wyłączone i nieeksponowane.

### Pięć ekranów Web UI — każdy jest wejściem w ten sam łańcuch

Ekrany nie są niezależnymi modułami; to pięć wejść do jednej ścieżki z §3.7.

| Ekran | Rola | Wyjście w łańcuchu |
|---|---|---|
| **Overview floty** | kafle instancji, natychmiastowa identyfikacja problemu (wzorzec Redgate) + lista ostrzeżeń | → instancja / → ostrzeżenie |
| **Waits** | **główny widok produktu** — stacked bar czasu oczekiwania wg typu wait na osi czasu (wzorzec DPA) | → okno czasu → wait → sesja → zapytanie |
| **Queries** | ranking z historią, regresja względem okresu i baseline'u (§5) | → zapytanie → plan → rekomendacja |
| **Indexes** | brakujące, nieużywane, fragmentacja/bloat — z dowodami i DDL | → rekomendacja → akcja → skutek |
| **Instance detail** | metryki instancji, blokady i deadlocki, stan kolektora, tryby opt-in (§3.5, §3.6) | → sesja → zapytanie |

Jeśli harmonogram nie domyka się, cięcie idzie po **liczbie** ekranów (Indexes i Overview są najbardziej odraczalne), nie po ich jakości.

### Rekomendacje wydajnościowe — ambicja i granica

**Ambicja jest wysoka:** PulseDB ma dawać *inteligentne, konkretne sugestie poprawy wydajności* — nie listę metryk do samodzielnej interpretacji. Blisko tego, co rynek nazywa auto-tuningiem, ale **bez ostatniego kroku**. Granicę wyznacza zasada 3.6, nie brak ambicji:

| Poziom | Co to jest | Werdykt |
|---|---|---|
| 1. Rekomendacja | analiza + gotowy DDL do skopiowania + dowody (które zapytania, ile wykonań, jakie waity, jaki udział w czasie oczekiwania) + **koszt uboczny** (narzut na zapisy, storage) | **MVP** |
| 2. Walidacja bez wdrożenia | indeks hipotetyczny: „ten indeks obniżyłby koszt o X" bez tworzenia go — `hypopg` (PostgreSQL), what-if (SQL Server) | **MVP, opcjonalnie** ✅ zdecydowane |
| 3. Wykonanie | PulseDB wykonuje akcję naprawczą na monitorowanej bazie | **opt-in, człowiek inicjuje** — katalog akcji niżej, warunki w §3.6 |

Poziom 2 działa **tylko gdy rozszerzenie jest obecne** — dokładnie ten sam wzorzec, co `pg_wait_sampling` w §4: domyślnie wyłączone, wykrywane automatycznie, z jawnym komunikatem w UI o różnicy w jakości analizy. Nie instalujemy niczego i nie wymagamy niczego. Uzasadnienie: Postgres MCP Pro robi już index tuning z `hypopg` ✅ — dla PostgreSQL walidacja hipotetyczna przestała być luksusem, stała się oczekiwaniem.

### Katalog akcji naprawczych

Poziom 3 to **katalog wyliczony imiennie**, nie uprawnienie ogólne „zapis". Każda akcja ma własną implementację, podgląd dokładnego SQL i opis skutku. Warunki włączenia: §3.6.

| Akcja | Ryzyko | Kiedy |
|---|---|---|
| `KILL SESSION` — ubicie sesji blokującej | niskie, nie zmienia schematu | **MVP** — najwyższa wartość w trakcie incydentu |
| `ANALYZE` / `UPDATE STATISTICS` | niskie | **MVP** |
| `CREATE INDEX` (`CONCURRENTLY` / `ONLINE` gdzie dostępne) | średnie — długo trwa, obciąża IO | **v0.2** — flagowy UX „rekomendacja → wykonanie" |
| `REINDEX` / rebuild | średnie | v0.2 |
| Wymuszenie planu (Query Store `sp_query_store_force_plan`) | średnie | v0.2 |
| `DROP INDEX` | **wysokie** — psuje wydajność natychmiast, a analiza „nieużywany" myli się przy krótkim oknie obserwacji | później, z wymogiem N dni dowodów |

W MVP powstaje **szkielet akcji + dwie najbezpieczniejsze pozycje**. Reszta dokłada się bez zmian architektury. Rozszerzanie katalogu jest tanie; rozszerzanie uprawnień — nie, dlatego katalog jest zamknięty i jawny.

**Zysk dla rejestru rekomendacji:** akcja wykonana z PulseDB wpada do rejestru z dokładnym momentem i dokładną zmianą. Skutek przestaje być wnioskowany z diffu inwentarza — pętla „rekomendacja → wykonanie → zmierzony efekt" domyka się z pełną atrybucją.

**Skąd bierze się „inteligencja" — deterministycznie, nie z modelu.** Reguły + dowody + własna historia. AI pozostaje warstwą opcjonalną nad tym (przez MCP), nigdy warunkiem działania — inaczej łamiemy zasadę z §5 „Miejsce AI". Nie ścigamy się też liczbą reguł z `PlanAnalyzer` Darlinga (30 reguł ✅) — nasz kąt jest inny: rekomendacja z dowodem, dla dwóch silników, ze zmierzonym skutkiem.

**Rejestr rekomendacji ze skutkiem** — to jest ta ostatnia część i wyróżnik, którego nie ma nikt:

> PulseDB zapisuje, co zarekomendował. Później sam wykrywa z własnej historii, że indeks powstał (diff inwentarza indeksów — dane zbierane i tak dla analizy nieużywanych indeksów), i pokazuje, co faktycznie stało się z zapytaniami, które miały skorzystać.

Rekomendacje przestają być listą sugestii, a stają się **rejestrem z wynikami**. Działa to w obu trybach: gdy zmianę wprowadził ktoś inny poza PulseDB — skutek jest wnioskowany z diffu inwentarza; gdy zmianę wykonano akcją z PulseDB (§3.6) — znamy dokładny moment i dokładną zmianę, więc atrybucja jest pełna. Koszt: zapytanie nad danymi, które MVP i tak ma. Wartość: domknięcie pętli, którego nie ma żaden konkurent.

### Baseline'y — cztery poziomy, nie jedna funkcja

„Baseline'y i detekcja anomalii" to nie jedna pozycja. Rozbicie po koszcie:

| Poziom | Co to | Werdykt |
|---|---|---|
| 1. Porównanie okresów | okno A vs okno B dla zapytania / waita / instancji → **regresja zapytania** | **MVP** — czyste SQL nad faktami, które i tak mamy |
| 2. Baseline sezonowy z percentyli | p50/p95 per (zapytanie, godzina-tygodnia) z ostatnich N tygodni | **MVP** — rollup + tabela + retencja, bez statystyki i bez modelu |
| 3. Detekcja odchyleń | flaga gdy wartość > p95 przez K próbek, z progiem minimalnym i minimalną liczbą wywołań | **v0.2** — reguły, nie ML |
| 4. Statystyka / ML | Holt-Winters, dekompozycja STL, changepoint detection, korelacje wielowymiarowe | **nie** — wysoki koszt, tuning-heavy, łatwo wypuścić coś, co wyje bez powodu |

Dwa powody, dla których poziomy 1–2 są tańsze, niż wyglądają:

- **Warstwa rollupów powstaje i tak.** Przy samplingu 1 s retencja surowych danych jest krótka, a UI musi być szybkie nad tygodniami — agregaty 1 min / 1 h są w Fazie 0/1 niezależnie od baseline'ów. Gdy istnieją, baseline percentylowy jest małym dodatkiem, nie podsystemem.
- **Poziom 1 domyka niespójność w MVP:** detekcja zmiany planu jest w zakresie, a detekcja regresji czasu zapytania nie była — a oba potrzebują dokładnie tego samego porównania „teraz" z „przedtem".

A powód, dla którego poziom 3 czeka do v0.2, nie jest kosztem: **baseline potrzebuje 2–4 tygodni historii, więc pierwszy użytkownik nie ma go w dniu premiery niezależnie od tego, czy kod jest gotowy.** Przesunięcie nic nie kosztuje w odbiorze produktu, a daje realne dane do kalibracji progów zamiast zgadywania.

**Konsekwencja architektoniczna:** silnik alertów musi przyjmować **warunek jako abstrakcję**, nie zaszyty próg — wtedy alerty względem baseline'u dokładają się w v0.2 bez przepisywania silnika. Ten sam wzorzec, co szew tenancy: przygotować szew, nie funkcję.

**Konsekwencja dla ADR modelu danych:** skoro baseline'y wchodzą, **TimescaleDB staje się istotnie atrakcyjniejsze** (continuous aggregates + hyperfunkcje percentylowe). Zastrzeżenie 🟡: część hyperfunkcji Timescale jest pod licencją TSL, nie Apache-2 — przy dystrybucji AGPL we własnym obrazie Dockera wymaga to sprawdzenia prawnego, nie założenia.

### Poza MVP — świadomie odłożone

| Pozycja | Priorytet | Uwaga |
|---|---|---|
| SSO/SAML | **nr 1 po MVP** | Pierwsza funkcja enterprise (§6 krok 2). ICP = sektor regulowany, on-prem — ta grupa pyta o SSO w pierwszej rozmowie, nie w trzeciej |
| Detekcja odchyleń od baseline'u (poziom 3 wyżej) | średni, **v0.2** | Poziomy 1–2 są w MVP. Poziom 3 czeka na 2–4 tygodnie historii, nie na budżet. Razem z nim wchodzą alerty „wolniejsze niż zwykle" |
| Statystyka / ML w detekcji anomalii (poziom 4) | **nie** | Poza horyzontem — patrz tabela wyżej |
| Multi-tenancy | **w planach, nie non-goal** | Warunek konieczny Cloud (§6) — bez niej chmury nie ma. W MVP jeden tenant, ale **szew** przygotowany — patrz niżej |
| Raport audytu (CLI, jeden szablon) | **v0.2** | Mechanika adopcji, nie funkcja raportowania — §6 |
| Raporty harmonogramowane, eksporty, szablony | niski | Przy API-first raport = `cron` + CLI z wyjściem markdown. Użytkownik zrobi to sam pierwszego dnia |
| HA | niski | Dla 5–30 instancji przestój monitoringu jest znośny. **Nie mylić z wymaganiem MVP:** kolektor musi przeżyć restart i przerwę bez psucia historii (zbieranie idempotentne, jawne oznaczanie luk) — to higiena, nie HA |
| Cloud | niski | §6 — trzeci i ostatni krok monetyzacji |

**Multi-tenancy — jak to pogodzić z MVP.** Przedwczesne dodanie `tenant_id` do każdej tabeli jest zmianą inwazyjną w każdym zapytaniu i kosztuje w MVP codziennie. Ale odłożenie bez przygotowania oznacza późną migrację przez cały model danych. Wyjście: **przygotować szew, nie kolumnę** — cały dostęp do danych przechodzi przez warstwę zapytań z obowiązkowym parametrem zakresu. W MVP tym zakresem jest **instancja** (potrzebujemy go i tak dla tokenów MCP z §3.3); tenant dołoży się później jako kolejny wymiar tej samej warstwy, bez przepisywania kolektorów. Koszt w MVP: bliski zeru. Rozstrzygnięcie szczegółów → ADR modelu danych.

Dwa wymagania projektowe, które z tego wynikają:

1. **W instalacji jednotenantowej tenancy musi być niewidoczna** — domyślny tenant, zero dodatkowych pojęć w UI, zero kroków w onboardingu. Inaczej opodatkowujemy 95% użytkowników za przyszłość 5%.
2. **Izolacja danych (szew) ≠ multi-tenancy operacyjna.** Per-tenant limity, rozliczenia, onboarding i problem hałaśliwego sąsiada należą w całości do Cloud i nie dotykają MVP.

### Non-goals — czego nie budujemy wcale w horyzoncie 12 miesięcy

| Nie budujemy | Powód |
|---|---|
| Silnika alertowania z routingiem, eskalacją, on-call | Przegrana z PagerDuty/Alertmanager/Grafaną. Robimy: detekcja + webhook |
| Systemu dashboardów budowanych przez użytkownika | To jest Grafana. Robimy: kilka doskonałych widoków opiniotwórczych + `/metrics` |
| Wsparcia dla Oracle, MySQL, MongoDB | Prosta droga do produktu szerokiego i płytkiego |
| Agenta (agent mode) | Agentless pokrywa ~95% przypadków. Zostaje jako możliwość architektoniczna, nie jako praca |
| Własnego silnika time-series | PostgreSQL + partycjonowanie albo TimescaleDB |
| Wizualizatora planów od zera | Bardzo kosztowny. W MVP: przechowywanie XML/JSON + eksport + odnośnik do istniejących wizualizatorów |
| **Automatycznego** wykonywania rekomendacji (auto-tuning bez człowieka, harmonogram akcji) | Akcję inicjuje człowiek — zawsze (§3.6). Zaufanie DBA do automatu jest zerowe, a zysk nad „jedno kliknięcie z podglądem SQL" znikomy. Wykonanie *z UI* jest w zakresie; wykonanie *bez decyzji człowieka* nie |
| Konsoli dowolnego SQL | Ścieżka zdalnego wykonania kodu do każdej monitorowanej bazy. Katalog akcji da się zaudytować, „execute" nie. Nie jesteśmy klientem SQL (§3.6) |
| Zapisu przez MCP / przez agenta AI | Prompt injection z tekstów zapytań do DDL na produkcji (§3.6). Nie podlega konfiguracji. Darling to ma; my świadomie nie — i czynimy z tego argument bezpieczeństwa |
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

**Multi-tenancy jest warunkiem koniecznym Cloud**, nie osobną funkcją — dlatego szew tenancy powstaje w MVP (§5), a reszta razem z chmurą.

### Rozważone i odrzucone: „klient otwiera dostęp na godzinę" ❌

Pomysł: zamiast stałego tunelu klient otwiera dostęp sieciowy do bazy ad hoc, na czas analizy.

**Nie działa jako model monitoringu** — i przegrywa z naszą własną przewagą, nie z bezpieczeństwem. Wartość PulseDB leży w **historii** (§3.3: „pokaż, co się działo w nocy z wtorku na środę"), a sampling 1 s ma sens wyłącznie jako ciągły. Godzina dostępu daje godzinę próbki. Dochodzi to, że ICP z §2 — sektor regulowany, on-prem — nie otworzy produkcyjnej bazy do internetu ani na godzinę.

### Tryb jednorazowego audytu ✅ zdecydowane: lokalnie tak, w chmurze nie

Pomysł „audyt jako pierwsza oferta chmurowa" został **odrzucony**. Powody:

1. **Hostowanie dokłada ryzyko i nie dokłada wartości.** Klient i tak musi otworzyć produkcyjną bazę na nasze IP. Sektor regulowany tego nie zrobi, a zespół, który *może*, umie też uruchomić `docker compose up` u siebie — wtedy nic nie wychodzi na zewnątrz i nie ma naszej infrastruktury w środku.
2. **Analogia rynkowa nie broni hostowania.** Edycja Lite PerformanceMonitor to narzędzie **desktopowe** (DuckDB + Parquet, lokalnie) ✅ — potwierdza sensowność *trybu ad-hoc*, nie *dostarczania go z chmury*.
3. **Koszt drugiego produktu.** Hosting, rozliczenia, tenancy, wsparcie — przy ryzyku zakresu z §7.2b i kapacji jednej osoby.

**Co zostaje przyjęte:** tryb audytu **lokalnie, jako jedna komenda CLI**. Przy API-first i CLI z wyjściem markdown raport z audytu jest zapytaniem nad danymi, które MVP i tak ma: `docker compose up` → zbieraj przez noc → `pulsedb report --since 8h --format markdown`. Koszt: dni, nie kwartał. Termin: **v0.2** (jedyny szablon raportu, który warto dowieźć — reszta raportowania zostaje poza zakresem, §5).

**Dlaczego to jest ważniejsze, niż wygląda:** to jest mechanika adopcji, której nam brakuje przy luce dystrybucyjnej z tej sekcji — *„uruchom na najgorszym serwerze na jedną noc, przynieś raport na jutrzejsze spotkanie"*. Tryb ewaluacyjny w jedno popołudnie, bez rozmowy handlowej i bez wdrożenia.

Dla **ciągłego** SaaS zostaje to, co wyżej: tylko bazy w chmurze (RDS, Azure SQL, Cloud SQL) z naszym IP na allowliście klienta. Dla on-prem ciągły SaaS wymagałby tunelu wychodzącego albo agenta — a agent jest non-goalem (§5).

*Nierozwiązane ❓:* model open-core wymaga zasobu, którego jeszcze nie mamy — **dystrybucji**. PMM ma za sobą Perconę, Darling osobistą markę, Grafana miała VC. Sam AGPLv3 nie generuje adopcji. Strategia dystrybucji jest luką w tej wizji i wymaga osobnej decyzji.

---

## 7. Ryzyka, które kształtują wizję

### 7.1 Konkurencyjne 🔴 wysokie

PerformanceMonitor rozwija się w tempie ~3 300 commitów w pół roku, jest darmowy, MIT, z dystrybucją opartą na osobistej marce autora ✅. **Jeśli doda PostgreSQL albo wersję kontenerową, przewaga PulseDB w segmencie SQL Server znika całkowicie.**

*Mitygacja wbudowana w wizję:* rdzeniem jest platforma, nie SQL Server (§5).

### 7.2 Zakresu 🔴 najwyższe

Research ocenia pierwotnie zadeklarowany zakres (2 silniki × 4 interfejsy × alerty × RBAC × baseline × plany × indeksy + cloud + enterprise) na **zespół 4–6 osób na 12 miesięcy**. Realna kapacja: **jedna osoba na pełnym zaangażowaniu.**

*Mitygacja:* lista non-goals z §5 i reguła egzekwowania zakresu. Roadmapa musi być **sekwencyjna, nie równoległa** — sampler przed alertami, API przed UI, adapter przed kolektorami. To jest najpoważniejsze ryzyko projektu i jedyne, na które mamy pełny wpływ.

### 7.2b Zakres MVP wzrósł w tej sesji — jawnie ⚠️

Względem zakresu MVP z [opportunities.md](research/opportunities.md) §8 doszło: rejestr rekomendacji · rama akcji naprawczych + 2 akcje · tryb głębokiego badania + 2 operacje · walidacja `hypopg` · baseline poziomy 1–2 · porównanie okresów · szew tenancy.

Każda pozycja ma uzasadnienie i większość jest tania **pod warunkiem, że fundament powstanie w właściwej kolejności** (rollupy przed baseline'ami, rama zgody przed akcjami i deep mode). Ale suma podnosi ryzyko z §7.2, a nie obniża.

**Kolejność cięcia, ustalona z góry** — jeśli harmonogram się nie domyka, wypada od dołu:

1. baseline poziom 2 (sezonowy percentylowy) → zostaje sam poziom 1
2. walidacja `hypopg` (poziom 2 rekomendacji)
3. operacje deep mode poza `DETAILED`
4. akcje naprawcze poza `KILL SESSION`
5. rejestr rekomendacji → do v0.2

**Nietykalne** — bez nich upada teza produktu z §1: warstwa adapterów · sampler 1 s dla dwóch silników · REST API pokrywające 100% funkcji · MCP po historii · szew zakresu/tenancy w modelu danych · **główny widok Waits z drill-inem** (§3.7 — bez niego nie jesteśmy alternatywą dla DPA, tylko innym rodzajem narzędzia).

**Jakość UI nie jest pozycją do cięcia.** Cięciu podlega liczba ekranów, nie ich dopracowanie (§5). Pięć ekranów przeciętnych przegrywa z trzema dobrymi — a w tym segmencie przeciętny UI jest tym, co już oferuje konkurencja.

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
- **Łańcuch diagnostyczny bez przerwania** (§3.7): od ostrzeżenia albo słupka na wykresie do konkretnego zapytania i jego planu, bez opuszczania UI i bez ręcznego szukania
- **Pierwsze uruchomienie bez dokumentacji**: nowy użytkownik znajduje najwolniejsze zapytanie ostatniej godziny w < 2 minuty. Słabością Redgate — lidera UX w kategorii — jest gęsty interfejs wymagający nauki 🟡; to jest kontra na to wprost

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
| Warstwa zakresu pod przyszły multi-tenancy — kształt szwu (§5) | ADR modelu danych (przed Fazą 0) |
| Kształt rollupów (1 min / 1 h) i retencji surowych próbek — warunek baseline'ów (§5) | ADR modelu danych (przed Fazą 0) |
| Licencja hyperfunkcji Timescale (TSL) wobec naszej dystrybucji AGPL 🟡 | ADR modelu danych — wymaga sprawdzenia prawnego |
| Zestaw typów alertów MVP (progi statyczne, przed poziomem 3 baseline'ów) | `docs/prd.md` |
| Granica time-boxa deep mode i budżet auto-abortu (§3.5) | `docs/prd.md` |
| ~~Tryb jednorazowego audytu jako pierwsza oferta chmurowa~~ | ✅ rozstrzygnięte w §6 — lokalnie (CLI, v0.2), nie w chmurze |
| Które akcje naprawcze faktycznie w MVP (propozycja: `KILL SESSION` + `ANALYZE`) | `docs/prd.md` |
| Split licencyjny rdzeń AGPL / integracje MIT | ADR licencyjny |
| Strategia dystrybucji i budowania adopcji | osobny dokument — luka w tej wizji (§6) |
| **Biblioteka wykresów** — interaktywny stacked bar na osi czasu z drill-inem to najtrudniejszy element frontendu (§3.7) | [ADR gotowy](research/2026-07-30-chart-library.md), rekomendacja warunkowa — rozstrzyga spike w Fazie 0a |
| Szczegółowy przepływ i stany 5 ekranów (§5) | `docs/prd.md` |
| Granica Cloud vs Enterprise | odłożone; osobny plan gdy pojawi się Cloud |

---

## Powiązane

- [../README.md](../README.md) — README projektu (wymaga aktualizacji do tego dokumentu)
- [research/opportunities.md](research/opportunities.md) — źródło rekomendacji produktowych
- [research/market-overview.md](research/market-overview.md) — krajobraz rynku, ceny, trendy 2026
- [research/current-project-analysis.md](research/current-project-analysis.md) — co przenieść z `sql-monitor`
- [plans/2026-07-30-boilerplate-from-family.md](plans/2026-07-30-boilerplate-from-family.md) — fundament techniczny w budowie
