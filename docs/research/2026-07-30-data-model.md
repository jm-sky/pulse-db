# ADR: model danych repozytorium PulseDB

**Data:** 2026-07-30 · **Status:** `verification needed`
**Kontekst:** [vision.md](../vision.md) §3.1, §3.5, §3.6, §4, §5 · [roadmap.md](../roadmap.md) §3 (Faza 0, elementy 6–8)
**Blokuje:** całą Fazę 0 — pierwsza migracja domenowa nie powstaje bez tego dokumentu
**Legenda pewności:** ✅ potwierdzone · 🟡 estymacja · ❓ otwarte

> **Dlaczego to jest najdroższa decyzja projektu.** Vision §4: *„model danych musi być zaprojektowany pod sampling od pierwszej migracji — przeprojektowanie po zebraniu historii u pierwszych użytkowników będzie drogie"*. Wszystkie inne decyzje techniczne da się cofnąć; tę cofa się przez migrację danych produkcyjnych u obcych ludzi.

---

## 1. Wymagania, które ten model musi udźwignąć

Z wizji, nie z wyobraźni:

| Wymaganie | Źródło | Konsekwencja dla modelu |
|---|---|---|
| Sampling aktywnych sesji **1 s**, atrybucja wait → sesja → zapytanie | §4 | fakty append-only, partycjonowane po czasie; ~90 wierszy/s przy 30 instancjach 🟡 |
| **Jeden zestaw pojęć** dla PostgreSQL i SQL Server, z rozwinięciem do szczegółów | §3.1 | normalizowana taksonomia waitów + zachowanie nazw natywnych |
| Porównanie okresów i **baseline sezonowy percentylowy** | §5 | rollupy 1 min / 1 h są elementem modelu, nie optymalizacją |
| **Deep mode** zmienia częstotliwość próbkowania i musi być oznaczony w danych | §3.5 | interwał próbkowania jest atrybutem danych, nie stałą |
| **Rejestr rekomendacji ze skutkiem** | §5 | rekomendacje i akcje są encjami pierwszej klasy, nie logiem |
| Pomiar **własnego narzutu** kolektora, oznaczanie luk | §3.5, roadmap Faza 0 | tabela wykonań kolektora z metrykami |
| **Szew zakresu** pod przyszły multi-tenancy, niewidoczny w instalacji jednotenantowej | §5 | tenancy rozstrzygana na granicy instancji |
| Opcjonalna **redakcja tekstów zapytań** | §3.3 | tekst zapytania oddzielony od tożsamości zapytania |
| Skala docelowa **5–30 instancji** | §2 | nie projektujemy pod 200+ |

**Stan repo ✅:** PostgreSQL 17-alpine (`docker-compose.yml:53`), własny runner migracji (numerowane skrypty `backend/migrations/000`–`066`, **bez Alembica**), modele SQLAlchemy + `init_db()`.

---

## 2. Decyzja 1: czysty PostgreSQL 17 z partycjonowaniem deklaratywnym

**Odrzucone: TimescaleDB w MVP.**

### Uzasadnienie

1. **Licencja.** Funkcje, dla których warto brać Timescale — continuous aggregates, kompresja kolumnowa, hyperfunkcje percentylowe — są w edycji **Community na licencji TSL, nie Apache-2** 🟡 (do potwierdzenia w źródłach przed ewentualną adopcją). Produkt, którego cały przekaz to *„bez licencji per instancja, kod na GitHubie"* (§6 vision), wymagający do działania komponentu source-available bez zatwierdzenia OSI, kupuje sobie pytanie w dziale prawnym klienta — dokładnie ten koszt adopcji, przed którym wizja ostrzega przy AGPL.
2. **Tarcie wdrożenia.** §3.4 obiecuje `docker compose up` na dowolnym hoście. Timescale to konkretny obraz bazy; zespół, który chce wskazać PulseDB na **istniejący** PostgreSQL jako repozytorium, musiałby zainstalować rozszerzenie u siebie.
3. **Skala tego nie wymaga.** Przy 30 instancjach i średnio 3 aktywnych sesjach mówimy o ~90 wierszach/s 🟡. To nie jest reżim, w którym PostgreSQL 17 z partycjonowaniem deklaratywnym przestaje wystarczać.
4. **Prawdziwą dźwignią skalowania jest kardynalność, nie silnik** (§6 tego dokumentu). Zła kontrola kardynalności rollupów zabije też Timescale.

### Czego to nas pozbawia — jawnie

Kompresji. Przy realnym obciążeniu (10 aktywnych sesji × 30 instancji) surowe próbki to ~27 GB na 7 dni 🟡 zamiast ~8 GB. To jest jedyny mocny argument za Timescale i **dostaje mierzalny wyzwalacz rewizji** (§10).

### Ograniczenia projektowe, żeby adopcja Timescale została możliwa

Model musi być **kompatybilny z hypertable** od początku — koszt zerowy, zysk opcjonalny:

- kolumna czasu jest pierwszą częścią klucza partycjonowania i **wchodzi do każdego klucza unikalnego** na tabeli faktów (wymóg PostgreSQL dla tabel partycjonowanych, zbieżny z wymogiem Timescale),
- brak kluczy obcych **wskazujących na** tabele faktów (tylko fakt → wymiar),
- agregaty liczone jako zwykłe tabele zapisywane przyrostowo z watermarkiem — logika przenosi się 1:1 na continuous aggregate,
- brak `UPDATE` na faktach; wyłącznie `INSERT` i `DROP PARTITION`.

---

## 3. Decyzja 2: wymiary oddzielone od faktów

Wymiary są małe, deduplikowane po hashu, mutowalne w polach `last_seen`. Fakty są append-only i partycjonowane po czasie.

### Wymiary

| Tabela | Zawartość | Uwagi |
|---|---|---|
| `monitored_instance` | silnik, wersja, host, `capabilities jsonb`, `tenant_id` (nullable), referencja do poświadczeń | `capabilities` = wykryte rozszerzenia i uprawnienia (`pg_wait_sampling`, `hypopg`, Query Store, poziom grantów) — §3.6 i §4 wizji |
| `monitored_database` | bazy w obrębie instancji | |
| `query_text` | PK `norm_hash`, `normalized_text`, `raw_text` **nullable** | Oddzielenie tekstu od tożsamości czyni redakcję (§3.3) flagą konfiguracji, nie przebudową: nie zapisujemy `raw_text` |
| `query` | PK surogat, `engine`, `engine_query_key`, FK `norm_hash`, `first_seen`, `last_seen` | Dwupoziomowa tożsamość — patrz §5 |
| `plan_text` | PK `plan_hash`, `plan_format` (`xml`/`json`), `plan_body` | Plan przechowywany raz; bez własnego wizualizatora (§5 non-goals) |
| `query_plan` | `query_id` × `plan_hash`, `first_seen`, `last_seen` | Podstawa **detekcji zmiany planu** — nowy wiersz dla znanego `query_id` to zdarzenie |
| `wait_class` | ~10 wierszy, statyczne | Taksonomia normalizowana — §5 |
| `wait_event` | `engine`, `native_name`, FK `wait_class_id` | Nazwa natywna zachowana zawsze |
| `session_attr` | zdeduplikowana krotka (`db_user`, `program`, `host`) | Wymiary krojenia w stylu DPA (zapytanie × wait × użytkownik × program × host) |

### Fakty (partycjonowane dziennie, poza rollupami)

| Tabela | Kadencja | Rola |
|---|---|---|
| `session_sample` | **1 s** | Surowe ASH: jeden wiersz na aktywną sesję na próbkę. Rdzeń produktu |
| `query_stat_delta` | 1 min | Delty z `pg_stat_statements` / Query Store: wywołania, czas całkowity, wiersze, IO |
| `instance_metric` | 1 min | Metryki instancji (`metric_id`, `value`) — wąska, nie szeroka: adaptery dokładają metryki bez migracji |
| `index_snapshot` | 1× dziennie | Inwentarz indeksów + statystyki użycia. **Podstawa detekcji „ktoś wdrożył rekomendację"** (§5 wizji) |
| `blocking_event`, `deadlock_event` | zdarzeniowo | |
| `collector_run` | każde uruchomienie | Czas, status, **zmierzony narzut**, `interval_ms`, flaga luki. Realizuje obietnicę §3.5 i oznaczanie luk |
| `deep_mode_window` | zdarzeniowo | Okno deep mode: od–do, kto włączył, jakie operacje. **Wymóg §3.5**: okno musi być oznaczone, inaczej porównania okresów kłamią |
| `recommendation` | zdarzeniowo | Rekomendacja z dowodami i DDL |
| `recommendation_outcome` | zdarzeniowo | Wykryte wdrożenie + zmierzony skutek — rejestr z §5 |
| `action_audit` | zdarzeniowo | Wykonane akcje naprawcze: kto, kiedy, co, jaki SQL, wynik (§3.6) |

### Konsekwencja narzędziowa ⚠️

Tabele partycjonowane, klucze zawierające kolumnę czasu i zadanie utrzymania partycji **nie da się wyrazić przez `metadata.create_all()`**. Dlatego:

- **schemat domenowy powstaje jako surowe DDL** w migracjach, nie z modeli SQLAlchemy (modele mogą istnieć do odczytu, ale nie są źródłem prawdy o DDL),
- potrzebne jest **zadanie utrzymania partycji** (tworzenie z wyprzedzeniem, usuwanie po retencji) — własne, nie `pg_partman`, żeby nie dokładać rozszerzenia po argumentacji z §2,
- **zostajemy przy istniejącym runnerze migracji**, nie wprowadzamy Alembica teraz — refaktor działającej platformy nie jest zakresem Fazy 0. Wyzwalacz rewizji: gdy migracji domenowych przekroczy ~10 albo pojawi się potrzeba migracji danych, nie tylko schematu.

---

## 4. Decyzja 3: interwał próbkowania jest daną, nie stałą 🔴

**To jest najłatwiejszy do przeoczenia błąd poprawnościowy w całym modelu.**

Matematyka ASH: czas oczekiwania szacuje się jako `liczba_próbek × interwał_próbkowania`. Jeśli interwał zapiszemy w kodzie jako 1 s, to **deep mode z próbkowaniem 250 ms zawyży zmierzony czas oczekiwania czterokrotnie** — i to w oknie, w którym użytkownik świadomie diagnozuje incydent, czyli dokładnie wtedy, gdy liczby muszą być prawdziwe.

**Decyzja:** `interval_ms` jest kolumną denormalizowaną **na wierszu `session_sample`** (4 bajty). Rollupy liczą `SUM(interval_ms)/1000.0`, nigdy `COUNT(*) × 1`.

Alternatywa (join do `collector_run`) jest normalizacyjnie czystsza, ale dokłada join do najgorętszego zapytania w produkcie. Denormalizacja wygrywa.

---

## 5. Decyzja 4: normalizacja między silnikami

### Taksonomia waitów — dwie warstwy

§3.1 wizji wymaga jednego zestawu pojęć z rozwinięciem do szczegółów. Realizacja:

- `wait_class` — **nasza** taksonomia, ~10 klas: `CPU` · `Lock` · `Latch/Buffer` · `IO Read` · `IO Write` · `Log/Commit` · `Network/Client` · `Memory` · `Idle` · `Other`
- `wait_event` — nazwa natywna (`LCK_M_X`, `PAGEIOLATCH_SH`, `LWLock:WALWrite`, `Client:ClientRead`) z mapowaniem na klasę

Mapowanie jest **danymi, nie kodem** — wiersze w tabeli, uzupełniane migracją. Nowy, nieznany wait natywny wpada do `Other` z zachowaną nazwą i nie psuje zbierania.

### Reguła poprawności: co jest, a co nie jest oczekiwaniem 🔴

Klasyczny błąd tej kategorii narzędzi to wliczanie bezczynności do czasu oczekiwania.

- **PostgreSQL:** próbkujemy wyłącznie sesje ze `state = 'active'`. `Client:ClientRead` klasyfikujemy jako `Idle` — zapisujemy, ale **domyślnie wykluczamy z sum czasu oczekiwania**.
- **SQL Server:** źródłem są żądania z `dm_exec_requests`; typy z rodziny `*SLEEP*`, `BROKER_*`, `XE_*` i pokrewne trafiają do `Idle` i podlegają tej samej regule.

Bez tego główny wykres pokazuje, że baza „czeka" całą dobę na nic — i produkt traci wiarygodność w pierwszych pięciu minutach.

### Tożsamość zapytania — dwupoziomowa

Problem: `queryid` z `pg_stat_statements` jest lokalny dla klastra i **zmienia się przy zmianie wersji lub resecie statystyk**; `query_hash` SQL Servera to inna przestrzeń wartości. Żaden z nich nie pozwala porównać tego samego zapytania między instancjami.

Rozwiązanie:

- `query_text.norm_hash` — **nasz** hash tekstu po normalizacji. Wspólny dla instancji i silników, o ile tekst jest ten sam.
- `query.engine_query_key` — klucz natywny, per silnik. Służy do przypinania statystyk pochodzących z silnika.

Zysk: gdy klucz natywny się zmieni (upgrade, reset), historia nie pęka — łączymy przez `norm_hash`. I porównanie tego samego zapytania na dwóch instancjach jest wykonalne, co jest warunkiem obietnicy „jeden panel" z §3.1.

---

## 6. Decyzja 5: rollupy z kontrolą kardynalności

Rollupy nie są optymalizacją — są **warunkiem baseline'ów** (§5 wizji) i szybkiego UI nad tygodniami.

| Tabela | Ziarno | Klucz agregacji |
|---|---|---|
| `ash_1m` | 1 minuta | instancja × zapytanie × klasa waitu |
| `ash_1h` | 1 godzina | to samo |
| `query_stat_1h` | 1 godzina | instancja × zapytanie |
| `query_baseline` | (zapytanie, dzień-tygodnia × godzina) | p50/p95 z ostatnich N tygodni |

### Top-N + „other" — bez tego model puchnie 🔴

Rollup **nie** zapisuje wszystkich kombinacji. Dla każdego kubełka: **20 najcięższych** par (zapytanie, klasa waitu) plus jeden wiersz zbiorczy `other`. Domyślne N konfigurowalne.

Bez tego kardynalność rośnie z liczbą unikalnych zapytań (a aplikacje generują ich tysiące) i rollup staje się większy od danych surowych. Z tym — górna granica to `N+1` wierszy na instancję-kubełek, czyli przewidywalnie: 30 instancji × 1440 minut × 21 ≈ **907 tys. wierszy/dobę** 🟡.

Koszt jawny: analiza historyczna nie odpowie na pytanie o zapytanie, które w danej minucie było poza top 20. Uznajemy to za akceptowalne — diagnostyka dotyczy tego, co boli.

### Zapisywanie przyrostowe z watermarkiem

Rollup liczony jest zadaniem przesuwającym watermark, nie widokiem. Kubełek zamykany jest z opóźnieniem (domyślnie 2 minuty), żeby spóźnione próbki nie gubiły się. Logika przenosi się 1:1 na continuous aggregate, jeśli kiedyś przejdziemy na Timescale.

### Baseline — czego to jest percentyl

`query_baseline` liczy percentyle **z kubełków godzinowych**, nie z pojedynczych wykonań. Czyli odpowiada na *„czy ta godzina jest nietypowa dla tego zapytania w tym dniu tygodnia"*, a nie *„czy to jedno wykonanie było wolne"*. To jest właściwa semantyka dla poziomu 2 z §5 wizji i trzeba ją zapisać, żeby nikt później nie pomylił jej z percentylami per wykonanie.

**Rozdział źródeł, który łatwo pomylić:** czas trwania zapytania pochodzi z `query_stat_delta` (silnik podaje `total_time`/`calls`), a atrybucja oczekiwań z `session_sample`. Baseline „zapytanie wolniejsze niż zwykle" liczy się z pierwszego, nie z drugiego. Sampling mówi *na co* czekało, statystyki mówią *jak długo* trwało.

---

## 7. Decyzja 6: retencja

| Dane | Domyślnie | Uzasadnienie |
|---|---|---|
| `session_sample` (surowe) | **7 dni** | Diagnostyka incydentu z „nocy z wtorku na środę" (§3.3) mieści się w tygodniu |
| `ash_1m` | **30 dni** | Porównanie okresów tydzień-do-tygodnia |
| `ash_1h`, `query_stat_1h` | **13 miesięcy** | Baseline sezonowy potrzebuje 4–8 tygodni; 13 miesięcy daje porównanie rok-do-roku |
| `index_snapshot` | 13 miesięcy | Detekcja wdrożenia rekomendacji |
| `plan_text` | dopóki referencjonowany + 90 dni | Plany są duże |
| `recommendation*`, `action_audit`, `deep_mode_window` | **bez limitu** | Audyt i rejestr skutków tracą sens obcięte |

Wszystko konfigurowalne per instalacja. Usuwanie przez `DROP PARTITION`, nigdy `DELETE`.

---

## 8. Decyzja 7: szew zakresu — tenancy na granicy instancji

Wizja §5: przygotować szew, nie kolumnę; w instalacji jednotenantowej tenancy musi być niewidoczna.

**Decyzja:** `tenant_id` istnieje **wyłącznie na `monitored_instance`**. Żadna tabela faktów nie ma kolumny tenanta — wszystkie mają `instance_id`, więc tenant wynika z rozwiązania wymiaru.

- **MVP:** jeden domyślny tenant, `tenant_id` niewidoczny w API i UI.
- **Multi-tenancy później:** dochodzi filtr na wymiarze, nie migracja 12 tabel faktów o setkach milionów wierszy.
- **Warstwa dostępu wymaga jawnego zakresu** od pierwszego dnia — w MVP zakresem jest instancja lub zbiór instancji (potrzebny i tak dla tokenów MCP z §3.3). Zapytanie do faktów bez zakresu nie kompiluje się na poziomie API repozytorium.

Koszt: filtrowanie po tenancie wymaga joina do małego wymiaru zamiast pruningu partycji. Przy 5–30 instancjach nieistotne 🟡.

---

## 9. Decyzja 8: czas i zegary

- Wszystkie znaczniki `TIMESTAMPTZ`, przechowywane w UTC. Bez wyjątków.
- **Zegarem autorytatywnym jest zegar PulseDB**, nie monitorowanej bazy. Korelacja między instancjami wymaga jednego zegara.
- `collector_run` zapisuje **zmierzony offset zegara** monitorowanej instancji. Znaczniki pochodzące z bazy (czas deadlocku, czas pobrania planu) da się dzięki temu przetłumaczyć po fakcie, zamiast odkrywać po miesiącu, że korelacja jest przesunięta o 40 sekund.
- Kubełki rollupów wyrównane do UTC. Baseline sezonowy (dzień tygodnia × godzina) liczony w **strefie skonfigurowanej dla instancji** — „nocny batch" jest pojęciem lokalnym, nie UTC.

---

## 10. Ryzyka i wyzwalacze rewizji

| Ryzyko | Waga | Wyzwalacz / mitygacja |
|---|---|---|
| Brak kompresji — surowe próbki rosną szybciej niż szacunek | średnie | **Wyzwalacz rewizji Timescale:** średnio > 8 aktywnych sesji na instancję przy ≥ 20 instancjach, albo > 40 GB na 7 dni surowych. Wtedy rozstrzygnąć pytanie licencyjne TSL i rozważyć hypertable + kompresję |
| Estymaty wolumenu są 🟡, nieoparte na pomiarze | **wysokie** | Spike samplingu z Fazy 0a musi zwrócić **realną liczbę aktywnych sesji na próbkę**, nie tylko narzut. Bez tego cała §2 stoi na założeniu |
| Top-N gubi zapytania z ogona | średnie | Świadomy koszt (§6). Surowe próbki z 7 dni zawierają ogon — analiza „poza top 20" jest możliwa w oknie diagnostycznym, tylko nie w historii długiej |
| Normalizacja tekstu zapytania jest niebanalna (literały, `IN (...)`, komentarze) | średnie | Nie piszemy własnej od zera dla PostgreSQL — `pg_stat_statements` już normalizuje. Dla SQL Server bazujemy na tekście z Query Store. Nasz `norm_hash` liczony na tym, co silnik już znormalizował 🟡 |
| Mapowanie waitów jako dane oznacza rozjazd wersji silnika | niskie | Nieznany wait → `Other` z nazwą natywną, nigdy błąd zbierania |
| Własny runner migracji przy schemacie tej złożoności | niskie–średnie | Wyzwalacz: > 10 migracji domenowych albo pierwsza migracja **danych** → wtedy decyzja o Alembicu |
| `capabilities jsonb` staje się workiem na wszystko | niskie | Schemat walidowany w kodzie adaptera; jsonb tylko dla wyników wykrywania, nie dla konfiguracji |

---

## 11. Co ta decyzja odblokowuje

Faza 0 może startować w kolejności: migracje wymiarów → migracje faktów + zadanie utrzymania partycji → `EngineAdapter` z wykrywaniem `capabilities` → `collector_run` z pomiarem narzutu → trywialny kolektor → rollupy z watermarkiem.

**Kryterium wyjścia z Fazy 0 z roadmapy pozostaje bez zmian**, z jednym uzupełnieniem: rollup 1 min musi liczyć poprawnie przy **zmiennym `interval_ms`** — test z symulowanym oknem deep mode.

---

## 12. Uwaga o strukturze dokumentacji

To drugi ADR w `docs/research/` (po [2026-07-30-chart-library.md](2026-07-30-chart-library.md)). Katalog jest przeznaczony na analizy przed decyzją, a ADR-y to decyzje utrzymywane długo i często cytowane. **Sugestia:** przy trzecim ADR wydzielić `docs/adr/` z własnym indeksem. Nie robię tego jednostronnie — to zmiana konwencji z `docs/README.md`.

---

## Powiązane

- [../vision.md](../vision.md) — §3.1 wielosilnikowość, §3.5 load-safety i deep mode, §3.6 rozdział zbierania od działania, §4 sampling, §5 zakres
- [../roadmap.md](../roadmap.md) — Faza 0 (elementy 6–8), Faza 0a (spike samplingu)
- [2026-07-30-chart-library.md](2026-07-30-chart-library.md) — ADR frontendu
- [current-project-analysis.md](current-project-analysis.md) — model danych `sql-monitor` i dlaczego nie udźwignie samplingu 1 s
