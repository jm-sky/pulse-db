# PulseDB — roadmapa do MVP

**Data:** 2026-07-30 · **Status:** `verification needed`
**Podstawa:** [vision.md](vision.md) (zakres, zasady, reguła cięcia §7.2b) · [research/opportunities.md](research/opportunities.md) §8–9
**Kapacja:** jedna osoba, pełne zaangażowanie
**Legenda pewności:** ✅ potwierdzone · 🟡 estymacja · ❓ otwarte

---

## 0. Zasady tej roadmapy

**Sekwencyjnie, nie równolegle.** Przy jednej osobie kolejność jest ważniejsza od zakresu. Każda faza kończy się **kryterium wyjścia** — dopóki nie jest spełnione, następna faza nie zaczyna się, nawet jeśli „prawie działa".

**Definition of done — reguły globalne, nie fazy:**

| Reguła | Dlaczego |
|---|---|
| Funkcja domenowa jest skończona dopiero z **endpointem API + wpisem w OpenAPI + testem** | API-first (§3.2) nie jest fazą. Gdyby API powstawało po UI, powstałoby API w kształcie UI — i test „czy zewnętrzny zespół napisze UI od nowa" przepadłby cicho |
| Każdy kolektor **mierzy własny narzut** | Warunek obietnicy z §3.5 i bezpiecznika auto-abort z deep mode |
| Każda funkcja ma **dwie implementacje adaptera** albo jawnie zadeklarowany brak wsparcia w jednym silniku | Zapobiega przeciekaniu abstrakcji (§3.1). „Dorobimy dla Postgresa później" = dwa produkty pod jednym logo |
| Każdy element UI ma **wyjście w łańcuchu §3.7** | Zasada braku ślepego zaułka |
| Dostęp do danych przechodzi przez **warstwę z obowiązkowym parametrem zakresu** | Szew tenancy (§5) — dokładany raz, na starcie |

**Reguła cięcia (§7.2b):** jeśli harmonogram się nie domyka, wypada od dołu — baseline poziom 2 → walidacja `hypopg` → operacje deep mode poza `DETAILED` → akcje poza `KILL SESSION` → rejestr rekomendacji. **Nietykalne:** adaptery · sampler 1 s dla dwóch silników · REST API 100% · MCP po historii · szew zakresu · główny widok Waits z drill-inem. **Jakość UI nie jest pozycją do cięcia** — cięciu podlega liczba ekranów.

---

## 1. Harmonogram — widok całości 🟡

T0 = 2026-07-30.

| Faza | Zakres | Czas 🟡 | Koniec 🟡 |
|---|---|---|---|
| **0a** | Walidacja założeń, spike'i, ADR-y, PRD | 3 tyg. | 2026-08-20 |
| **0** | Fundament: adapter, model danych, runtime kolektora (boilerplate ✅ gotowy) | ~~6~~ **4 tyg.** | 2026-09-17 |
| **1** | Rdzeń diagnostyczny: sampler, zapytania, plany, blokady, indeksy, baseline 1–2 | 14 tyg. | 2026-12-24 |
| **2** | Interfejsy: CLI, MCP, Web UI, alerty, `/metrics` | 12 tyg. | 2027-03-18 |
| **3** | Operacje podwyższonego ryzyka + rejestr rekomendacji | 5 tyg. | 2027-04-22 |
| **4** | Przygotowanie premiery | 3 tyg. | 2027-05-13 |

**Suma: ~41 tygodni ≈ 9,5 miesiąca.** Estymaty **nie zawierają rezerwy**. Przy typowym rozjeździe 30% MVP wypada na **wrzesień 2027**. Zastosowanie pełnej reguły cięcia z §7.2b zdejmuje ~8–10 tygodni → premiera ok. **marca 2027**.

⚠️ To jest dłużej niż wcześniejsze szacunki 6–9 miesięcy, bo zakres MVP wzrósł w sesji planistycznej (§7.2b vision). Liczba jest uczciwa, nie motywacyjna. Największa niepewność siedzi w Fazie 1 (sampler dla dwóch silników) i w UI Fazy 2 — obie mogą się rozjechać o ±30%.

---

## 2. Faza 0a — walidacja i rozstrzygnięcia (3 tyg.)

**Zanim powstanie pierwsza linia kodu domenowego.** Tu rozstrzygamy rzeczy, po których wszystko inne wygląda inaczej.

### Bramka krytyczna: weryfikacja tezy produktu

**5–10 rozmów z DBA/leadami** ([opportunities.md](research/opportunities.md) §9.2): czy naprawdę mają PostgreSQL i SQL Server obok siebie i czy przełączanie narzędzi naprawdę boli.

> **To jest bramka, nie zadanie.** Jeśli założenie upada, wracamy do [vision.md](vision.md) przed Fazą 1 — bo wtedy upada zasada 3.1, a z nią całe pozycjonowanie (§8 vision, kryterium wcześniejszego zatrzymania).

Rozmowy biegną w tle przez cały okres fazy — czekanie na kalendarz innych ludzi nie jest pracą i nie blokuje spike'ów.

### Spike'i techniczne

| Spike | Pytanie | Wynik |
|---|---|---|
| PostgreSQL sampling | `pg_wait_sampling` vs zewnętrzne próbkowanie `pg_stat_activity` co 1 s — różnica w jakości danych i narzut, na realnej bazie | liczby do ADR modelu danych; potwierdzenie lub obalenie domyślnej ścieżki z §4 vision |
| SQL Server sampling | narzut próbkowania `dm_exec_requests` + `dm_os_waiting_tasks` co 1 s | budżet narzutu do zadeklarowania w §3.5 |
| Poprzeczka jakości | instalacja **PerformanceMonitor Lite** i przejście jego workflow diagnostycznego (1 h) | świadomość, z czym się porównujemy — [opportunities.md](research/opportunities.md) §9.3 |
| Biblioteka wykresów (2–3 dni) | A: czy unovis synchronizuje kursor między osobnymi `XYContainer`? · B: tree-shaken bundle i wydajność ECharts przy kilkudziesięciu seriach × tysiącach punktów | rozstrzyga wybór: unovis (zostaje, zero migracji) vs ECharts — [2026-07-30-chart-library.md](research/2026-07-30-chart-library.md) §7.3 |

### ADR-y

| ADR | Rozstrzyga | Blokuje |
|---|---|---|
| **Model danych** | partycjonowanie deklaratywne vs TimescaleDB · kształt rollupów 1 min / 1 h · retencja surowych próbek · szew zakresu/tenancy · licencja TSL hyperfunkcji wobec dystrybucji AGPL 🟡 | całą Fazę 0 |
| **Biblioteka wykresów** | interaktywny stacked bar na osi czasu z drill-inem, licencja kompatybilna z AGPL | pierwszy ekran w Fazie 2 |
| **Split licencyjny** | rdzeń AGPLv3 · CLI, SDK, definicja MCP na MIT/Apache | publikację repo |

### PRD

`docs/prd.md` — persony, JTBD, wymagania per obszar, kryteria akceptacji, zestaw typów alertów, granica time-boxa deep mode, przepływy pięciu ekranów.

### Kryterium wyjścia z 0a

- teza o estate mieszanych **potwierdzona lub obalona** (nie „w toku")
- domyślna metoda samplingu dla PostgreSQL wybrana **na podstawie pomiaru**, nie założenia
- trzy ADR-y zamknięte
- PRD zaakceptowany

---

## 3. Faza 0 — fundament (6 tyg.)

Nakłada się częściowo z planem [2026-07-30-boilerplate-from-family.md](plans/2026-07-30-boilerplate-from-family.md) (`in progress`).

| # | Element | Uwaga |
|---|---|---|
| 1 | Domknięcie boilerplate'u: rebrand, smoke boot, inventory keep/drop | wg istniejącego planu |
| 2 | `LICENSE` AGPLv3 + **FAQ licencyjne** + CI (lint, typy, testy) | FAQ jest wymogiem z §6 vision, nie ozdobą |
| 3 | Auth: użytkownik + hasło + RBAC z `gear-stack`; OAuth/2FA env-off | bez inwestycji w SSO |
| 4 | Poświadczenia monitorowanych instancji w bazie PulseDB, **szyfrowane** | zero sekretów w plikach montowanych do kontenerów |
| 5 | **`EngineAdapter` z dwiema implementacjami** — połączenie, wykrywanie możliwości (wersja, rozszerzenia, uprawnienia), jeden trywialny kolektor | musi powstać **pierwszy**, nie „przy okazji drugiego silnika" |
| 6 | **Model danych**: wymiary `query`/`plan` + fakty time-series, `TIMESTAMPTZ`, partycjonowanie/Timescale, **szew zakresu** | projektowany pod sampling 1 s od pierwszej migracji (§4 vision) |
| 7 | **Warstwa rollupów** 1 min / 1 h + retencja | warunek baseline'ów i szybkiego UI; powstaje raz, na starcie |
| 8 | Runtime kolektora: harmonogram, **idempotencja, jawne oznaczanie luk**, pomiar własnego narzutu | higiena, nie HA (§5 vision) |
| 9 | Wykrywanie nadmiarowych uprawnień konta kolektora + dokumentacja minimalnych grantów | `pg_monitor` · `VIEW SERVER STATE` / `VIEW DATABASE STATE` (§3.6) |

### Kryterium wyjścia z 0

- `docker compose up` na czystym hoście → działająca aplikacja
- zarejestrowane **dwie instancje** (PostgreSQL + SQL Server), obie przez ten sam interfejs adaptera
- trywialny kolektor zapisuje fakty, rollupy się liczą, luki są oznaczone
- restart aplikacji nie psuje historii
- narzut kolektora jest **mierzony i widoczny**

### Stan na 2026-07-30

| Element | Stan |
|---|---|
| 1. Boilerplate: rebrand, inventory keep/drop | ✅ [plan zamknięty](plans/2026-07-30-boilerplate-from-family.md) |
| 2. `LICENSE` AGPLv3 | ✅ obecny; `pyproject.toml` poprawiony z `MIT` na `AGPL-3.0-or-later` |
| 2. CI (lint, typy, testy) | ✅ `.github/workflows/ci.yml` — 7 kroków, wszystkie egzekwowane ([issue 002](issues/2026-07-30--002--ci-continue-on-error.md)) |
| 2. FAQ licencyjne | ✅ [docs/licensing-faq.md](licensing-faq.md) |
| 3. Auth użytkownik + hasło + RBAC, OAuth/2FA env-off | ✅ z boilerplate'u |
| 4. Poświadczenia monitorowanych instancji szyfrowane | ✅ Fernet, klucz tylko w `CREDENTIALS_ENCRYPTION_KEY` — [`app/modules/monitoring/crypto.py`](../backend/app/modules/monitoring/crypto.py) |
| 5. `EngineAdapter` z dwiema implementacjami | ✅ interfejs + Postgres + SQL Server — zweryfikowane end-to-end (PG lokalnie; SQL Server 2022: **S2017 test only**; BSM-SQL13 prod — przypadkowo, od razu wyłączona) |
| 6. Model danych: wymiary + fakty + szew zakresu | ✅ migracje [`068`](../backend/migrations/068_create_monitoring_dimensions.py)/[`069`](../backend/migrations/069_create_monitoring_facts.py), partycjonowanie deklaratywne dzienne zweryfikowane na lokalnym PostgreSQL 16 |
| 7. Warstwa rollupów 1 min / 1 h | ✅ `ash_1m`/`ash_1h`/`query_stat_1h`, watermark + top-N+other, zweryfikowane end-to-end na lokalnym PostgreSQL 16 (self-monitoring) — [plan rollupów](plans/2026-07-31-rollups.md) |
| 8. Runtime kolektora: harmonogram, idempotencja, luki, narzut | ✅ pomiar narzutu + jawne oznaczanie luk (`collector_run`); **harmonogram** — `Scheduler` (`cli monitoring run-scheduler` + serwis Docker Compose), zweryfikowany end-to-end na lokalnym PostgreSQL 16 — [plan schedulera](plans/2026-07-31-scheduler.md) |
| 9. Wykrywanie nadmiarowych uprawnień + dokumentacja minimalnych grantów | ✅ wykrywanie (`pg_monitor`, `VIEW SERVER STATE`/`VIEW DATABASE STATE`) przez `cli monitoring detect-capabilities`; dokumentacja operatorska w [docs/grants.md](grants.md) |

Porządki po boilerplate ([issue 001](issues/2026-07-30--001--boilerplate-dead-code-cleanup.md)) usunęły pozostałości domen `billing` / `tenants` / `feature_limits` / gear. Migracja [`067`](../backend/migrations/067_drop_openrouter_api_token.py) czeka na uruchomienie na bazie deweloperskiej.

Szczegóły elementów 4–9: [plan Fazy 0 — fundament domenowy](plans/2026-07-30-phase0-foundation.md) (`done`). Przy okazji naprawiony martwy import, który wywalał `create_app()` i cały pytest w CI od commitu, który miał to CI wprowadzić ([issue 004](issues/2026-07-30--004--dead-logs-import-broke-ci-pytest.md)) — status „CI w pełni egzekwowane" w tabeli powyżej był nieaktualny do tej naprawy.

**Korekta estymaty:** elementy 1–3 były w praktyce gotowe przed startem fazy, więc **6 tygodni zostaje zredukowane do ~4** 🟡. **Faza 0 zamknięta** (w tym live SQL Server).

---

## 4. Faza 1 — rdzeń diagnostyczny (14 tyg.)

Kolejność nie jest dowolna: sampler pierwszy, bo to jest produkt; zapytania zaraz po nim, bo bez nich atrybucja samplera nie ma do czego się przypiąć.

| # | Element | Czas 🟡 | Uwaga |
|---|---|---|---|
| 1 | **Sampler aktywnych sesji 1 s, oba silniki, z atrybucją wait → sesja → zapytanie** | 6 tyg. | Rdzeń kategorii. PostgreSQL: `pg_stat_activity` domyślnie, `pg_wait_sampling` opcjonalnie gdy obecne, z komunikatem o różnicy jakości |
| 2 | Top queries z historią | 2 tyg. | SQL Server: DMV + Query Store · PostgreSQL: `pg_stat_statements` |
| 3 | Plany wykonania: pobieranie, przechowywanie, **detekcja zmiany planu** | 2 tyg. | Bez własnego wizualizatora — XML/JSON + eksport (§5 non-goals) |
| 4 | Blokady i deadlocki | 1,5 tyg. | |
| 5 | Analiza indeksów: brakujące, nieużywane, fragmentacja/bloat — **z dowodami i gotowym DDL** | 2 tyg. | Poziom 1 rekomendacji. Rekomendacja bez uzasadnienia nie jest skończona |
| 6 | **Porównanie okresów / regresja zapytania** (baseline poziom 1) | 0,5 tyg. | Tanie, bo rollupy już są |
| 7 | **Baseline sezonowy percentylowy** (poziom 2) | 2 tyg. | Pierwsza pozycja do cięcia |

### Kryterium wyjścia z 1

- sampler pracuje **7 dni bez przerwy** na obu silnikach, z narzutem w zadeklarowanym budżecie
- pytanie *„co czekało na co o 14:03 i które zapytanie to było"* ma odpowiedź — **przez API**, nie przez zapytanie do bazy repozytorium
- detekcja zmiany planu wyłapuje zmianę wywołaną ręcznie w teście
- rekomendacja indeksu zawiera dowody i DDL, nie samo „dodaj indeks"

### Stan na 2026-08-05

| Element | Stan |
|---|---|
| 1. Sampler aktywnych sesji, atrybucja wait → sesja → zapytanie | ✅ **PostgreSQL**: `pg_stat_activity` + opt-in `pg_wait_sampling_history`. ✅ **SQL Server**: `dm_exec_requests`/`dm_exec_sessions` (filtr `is_user_process = 1`), zweryfikowane na **S2017 (test)** |
| 2. Top queries z historią | ✅ **PostgreSQL**: `pg_stat_statements` + `query_stat_cursor`. ✅ **SQL Server**: `dm_exec_query_stats` + ten sam kursor/delta (Query Store wykrywany, nie jest jeszcze źródłem MVP) |
| 3. Plany wykonania + detekcja zmiany planu | ✅ Adapter + kolektor TOP-N (PG EXPLAIN JSON / SS dm_exec_query_plan), API list/export/plan-changes; [plan](plans/2026-08-05-query-plans.md) |
| 4. Blokady i deadlocki | ✅ Blocking PG+SS; deadlocks SS `system_health` + watermark; PG `deadlock_history: false`; [plan](plans/2026-08-05-blocking-deadlocks.md) |
| 5. Analiza indeksów z DDL | ✅ Inventory PG+SS → `index_snapshot`; unused DROP (oba); missing CREATE (SS); tick 24 h; [plan](plans/2026-08-05-index-analysis.md) |
| 6. Porównanie okresów / regresja zapytania (baseline poziom 1) | ✅ API: `GET .../queries/period-comparison` + `GET .../period-comparison/summary` nad rollupami `query_stat_1h`/`ash_1h`; testy jednostkowe; E2E potwierdzone live UI Queries (2026-08-06, m.in. S2017) |
| 7. Baseline sezonowy percentylowy | ❌ nie zaczęte |

Szczegóły: [plan Fazy 1 — rdzeń diagnostyczny](plans/2026-07-30-phase1-diagnostic-core.md).

---

## 5. Faza 2 — interfejsy (12 tyg.)

CLI i MCP **przed** UI. Nie z powodu wartości, a z powodu weryfikacji: jeśli pierwszym klientem API będzie własne UI, API po cichu przyjmie kształt tego UI. CLI i MCP są tanie (dni), gdy API jest dobre — i są testem, czy jest.

| # | Element | Czas 🟡 | Uwaga |
|---|---|---|---|
| 1 | **CLI**, w tym wyjście markdown | 1,5 tyg. | Format pod agenta AI; podstawa przyszłego raportu audytu |
| 2 | **Serwer MCP**: zdalny, read-only, zakresy tokenów per instancja, audit log każdego wywołania, opcjonalna redakcja tekstów zapytań | 2 tyg. | Bez zapisu — nie podlega konfiguracji (§3.6) |
| 3 | **Web UI — Waits** (główny widok, stacked bar na osi czasu, drill-in) | 2,5 tyg. | Nietykalny. Bez niego nie jesteśmy alternatywą dla DPA |
| 4 | Web UI — Queries, Instance detail | 2 tyg. | |
| 5 | Web UI — Overview floty, Indexes | 2 tyg. | Najbardziej odraczalne z pięciu |
| 6 | **Alerty**: 8–12 typów na progach statycznych, **warunek jako abstrakcja**, kanały webhook + Slack + e-mail | 1,5 tyg. | Musi być w zestawie **alert awarii kolektora** — monitoring, który po cichu przestał zbierać, jest gorszy od braku monitoringu |
| 7 | Endpoint `/metrics` (Prometheus) | 0,5 tyg. | |

### Kryterium wyjścia z 2

- **test API-first przechodzi:** każda funkcja widoczna w UI jest dostępna przez publiczne, udokumentowane API; brak endpointów „dla frontendu"
- agent AI (Claude Code / Cursor) odpowiada na *„co było wolne wczoraj w nocy"* wyłącznie przez MCP PulseDB
- **łańcuch §3.7 nieprzerwany**: od ostrzeżenia albo słupka do zapytania i planu, bez opuszczania UI
- **pierwsze uruchomienie bez dokumentacji**: nowy użytkownik znajduje najwolniejsze zapytanie ostatniej godziny w < 2 min

---

## 6. Faza 3 — operacje podwyższonego ryzyka (5 tyg.)

Rama zgody powstaje **raz** i obsługuje obie rodziny operacji (§3.6). Kolejność: rama → akcje → deep mode → rejestr.

| # | Element | Czas 🟡 |
|---|---|---|
| 1 | **Rama operacji podwyższonego ryzyka**: osobne uprawnienie RBAC · włączanie per instancja · podgląd dokładnego SQL + potwierdzenie · audit log · **bezpiecznik deploymentowy** (env wymuszający read-only, nieprzestawialny z UI) · osobne poświadczenia dla akcji | 2 tyg. |
| 2 | Akcje: **`KILL SESSION`** i **`ANALYZE` / `UPDATE STATISTICS`** | 1 tyg. |
| 3 | Deep mode: **`DETAILED`** fragmentacja + **podniesiona częstotliwość samplingu**, z time-boxem, auto-abortem po przekroczeniu budżetu narzutu i oznaczeniem okna w danych | 1 tyg. |
| 4 | **Rejestr rekomendacji ze zmierzonym skutkiem** | 1 tyg. |

### Kryterium wyjścia z 3

- bezpiecznik deploymentowy udowodniony testem: przy włączonej zmiennej **żadna akcja nie jest wykonalna z żadnego interfejsu**
- MCP nie ma dostępu do akcji — potwierdzone testem, nie konfiguracją
- deep mode wygasza się sam po upływie time-boxa i po przekroczeniu budżetu narzutu
- okno deep mode jest oznaczone w danych i nie zanieczyszcza porównań okresów

---

## 7. Faza 4 — przygotowanie premiery (3 tyg.)

| # | Element |
|---|---|
| 1 | Dokumentacja wdrożenia: `docker compose up` → działający monitoring w **< 15 minut** na czystym hoście (weryfikowane na czystej maszynie, nie „u mnie działa") |
| 2 | Dokumentacja minimalnych grantów per silnik + **opublikowany, zmierzony budżet narzutu** (§3.5) |
| 3 | FAQ licencyjne + `SECURITY.md` + model zagrożeń MCP |
| 4 | README zaktualizowany do [vision.md](vision.md) — dziś zawiera nieaktualne przewagi (open source + self-hosted + MCP) |
| 5 | Materiał wprowadzający: jeden przewodnik „od zera do znalezienia przyczyny" wzdłuż łańcucha §3.7 |

### Kryterium wyjścia z 4 = kryteria sukcesu MVP z §8 vision

---

## 8. Dystrybucja — biegnie równolegle od Fazy 1 ⚠️

Największa nierozwiązana luka projektu (§6 vision: *sam AGPLv3 nie generuje adopcji*). Kill criteria mówią o **3 zewnętrznych wdrożeniach produkcyjnych w 6 miesięcy od premiery** — a zbudowanie zasięgu zajmuje więcej niż 6 miesięcy.

**Rekomendacja: nie premiera po 10 miesiącach ciszy.** Publikacja repozytorium ok. **Fazy 1** (grudzień 2026 🟡), z jawnym statusem „w budowie, nie do produkcji", i **dziennik prac** — krótkie wpisy o rzeczach, które są ciekawe niezależnie od produktu: pomiary narzutu samplingu, różnice modeli wait events między silnikami, `pg_wait_sampling` vs `pg_stat_activity`.

*Za:* zasięg budowany przez 6 miesięcy przed premierą, wcześniejszy feedback, treść techniczna jest w tej niszy walutą.
*Przeciw:* konkurencja widzi kierunek. Ryzyko realne, ale niskie — Darling nie przejdzie na PostgreSQL z powodu naszego repo, a przewagą jest wykonanie, nie tajność planu.

❓ Do decyzji: czy publikować wcześnie. Reszta strategii dystrybucji wymaga osobnego dokumentu — roadmapa go nie zastępuje.

---

## 9. Po MVP

**v0.2** (kolejność wg §5 vision): SSO/SAML jako pierwsza funkcja enterprise · baseline poziom 3 + alerty względem baseline'u · akcja `CREATE INDEX` z rekomendacji · **raport audytu CLI** (§6 vision) · pozostałe operacje deep mode · walidacja `hypopg`.

**Później:** funkcje enterprise self-hosted (audyt, HA, rozszerzona retencja) · multi-tenancy + Cloud dla baz w chmurze · wsparcie i wdrożenia jako pierwszy strumień przychodu.

**Nie w horyzoncie 12 miesięcy:** non-goals z §5 vision.

---

## 10. Przeglądy i ryzyka do monitorowania

**Periodic review co 6 miesięcy** (README): pierwszy **2027-01-30** — aktualizacja researchu konkurencji, przegląd architektury i roadmapy.

**AI review** po każdej fazie (README). Priorytet: przegląd `vision.md` i tej roadmapy **przed Fazą 0**, bo oba dokumenty odeszły od rekomendacji researchu w trzech miejscach (zapis do bazy, deep mode, zakres baseline'ów).

| Ryzyko do obserwacji | Wyzwalacz | Reakcja |
|---|---|---|
| PerformanceMonitor dodaje PostgreSQL albo wersję kontenerową | ogłoszenie w repo/blogu autora | natychmiastowy przegląd pozycjonowania — przewaga w SQL Server znika (§7.1 vision) |
| Teza o estate mieszanych obalona w rozmowach | Faza 0a | powrót do `vision.md` przed Fazą 1 |
| Model danych nie udźwiga samplingu 1 s | Faza 1, koniec tygodnia 6 | przeprojektowanie **teraz**, przed zebraniem historii u użytkowników |
| Harmonogram rozjeżdża się > 6 tygodni | dowolna faza | reguła cięcia §7.2b, od dołu listy |

---

## 11. Stan na 2026-08-06 i rekomendacja kolejnych kroków

**Gotowe do przejęcia przez kolejną sesję.**

### Stan faktyczny

| Obszar | Stan |
|---|---|
| Faza 0 (fundament) | ✅ **Zamknięta** — w tym live SQL Server (walidacja na S2017 test). [plan Fazy 0](plans/2026-07-30-phase0-foundation.md) |
| Faza 0, element 7 (rollupy) | ✅ [plan rollupów](plans/2026-07-31-rollups.md) |
| Faza 0, element 8 (harmonogram) | ✅ [plan schedulera](plans/2026-07-31-scheduler.md) — obie silniki dostają pełny zestaw ticków |
| Faza 1, elementy 1–2 | ✅ **PostgreSQL + SQL Server** zaimplementowane i zweryfikowane end-to-end. [plan Fazy 1](plans/2026-07-30-phase1-diagnostic-core.md) |
| Faza 1, element 3 (plany) | ✅ Adapter + kolektor + API; live E2E — `verification needed`. [plan](plans/2026-08-05-query-plans.md) |
| Faza 1, element 4 (blokady/deadlocki) | ✅ Blocking + SS deadlocks; live E2E — `verification needed`. [plan](plans/2026-08-05-blocking-deadlocks.md) |
| Faza 1, element 5 (indeksy) | ✅ Inventory + unused/missing DDL; live E2E — `verification needed`. [plan](plans/2026-08-05-index-analysis.md) |
| Faza 1, element 6 (porównanie okresów) | ✅ API + testy + E2E via live UI Queries (2026-08-06). [plan Fazy 1](plans/2026-07-30-phase1-diagnostic-core.md) |
| Faza 1, element 7 | Nie zaczęte |
| Faza 0a (spike'e, wywiady, PRD) | Nie zaczęte — patrz §2; teza estate mieszanego nadal 🟡 |
| Desktop UI shell + Queries | ✅ Manual QA 2026-08-06; Settings w shellu; i18n chrome PL / terminy EN. [shell](plans/2026-08-04-desktop-ui-shell.md) · [Queries](plans/2026-08-05-queries-ui.md) |
| Dev monitoring targets | `pulse-db-local`, `sql-monitor-postgres`, `taxorder-ksef-local` — `cli monitoring register-dev-instances` / `scripts/monitoring/` |

### Rekomendacja — w tej kolejności

1. **Live E2E** indeksów + blocking/deadlocks + planów (lokalny PG + S2017) — domknięcie statusów planów 3–5.
2. **Faza 1, element 7** (baseline sezonowy percentylowy) — wymaga kilku tygodni historii w rollupach.
3. **Faza 2 follow-upy UI:** drill-in Waits→Queries, time picker, detail drawer zapytań / plan-changes; Profil/Admin na shellu.
4. **Faza 0a** (wywiady z DBA, PRD) — równolegle; ADR wykresów: ECharts już w shellu Waits ([research](research/2026-07-30-chart-library.md)).

### Co NIE jest zalecane teraz

- Automatyczne (nie opt-in) przełączenie na `pg_wait_sampling` jako domyślne źródło — wymaga decyzji o budżecie retencji/wolumenu.
- Query Store / parse logów PG pod historię deadlocków przed elementem 7.
- Tłumaczenie terminów diagnostycznych (`Waits`, `Queries`, `Estate`) na PL.

---

## Powiązane

- [vision.md](vision.md) — zakres, zasady, non-goals, kryteria sukcesu
- `prd.md` — wymagania i kryteria akceptacji (do napisania w Fazie 0a)
- [plans/2026-07-30-boilerplate-from-family.md](plans/2026-07-30-boilerplate-from-family.md) — fundament techniczny, `in progress`
- [plans/2026-07-30-phase0-foundation.md](plans/2026-07-30-phase0-foundation.md) — Faza 0 elementy 4–9, `done`
- [plans/2026-07-30-phase1-diagnostic-core.md](plans/2026-07-30-phase1-diagnostic-core.md) — Faza 1 elementy 1–2 (PostgreSQL + SQL Server), `in progress`
- [research/opportunities.md](research/opportunities.md) — źródło zakresu MVP i rekomendacji kolejnych kroków
