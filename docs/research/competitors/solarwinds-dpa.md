# SolarWinds Database Performance Analyzer (DPA)

**Data:** 2026-07-30 · **Kategoria:** konkurencja bezpośrednia (segment A) · **Rola:** benchmark kategorii

---

## 1. Pozycja

DPA jest **produktem definiującym kategorię** „database performance analysis". Kiedy ktoś mówi „chcę coś jak DPA", ma na myśli jedną konkretną rzecz: *wykres słupkowy czasu odpowiedzi w podziale na typy oczekiwań, klikalny w dół do zapytania*.

Jeśli PulseDB pozycjonuje się jako „alternatywa dla DPA", to jest to **jedyna funkcja, którą musi mieć**. Reszta to dodatki.

---

## 2. Funkcje

| Obszar | Zakres | Uwaga |
|--------|--------|-------|
| Monitoring zapytań | ✅ pełny — historia, ranking, drill-down | Rdzeń produktu |
| Wait statistics | ✅✅ **Response Time Analysis** — czas oczekiwania przypisany do zapytania, sesji, użytkownika, maszyny, programu | Największa przewaga |
| Execution plans | ✅ historia planów, wykrywanie zmian planu | |
| Index analysis | ✅ Index Advisor + Query Advisor | Rekomendacje z uzasadnieniem |
| Alerty | ✅ rozbudowane, z anomaly detection opartym na ML | |
| Dashboardy | ✅ własne + integracja z SolarWinds Platform (dawniej Orion) | |
| Raporty | ✅ harmonogramowane, eksport | |
| AI features | ✅ „AI-powered analysis" do root cause i rekomendacji 🟡 (marketing, brak szczegółów technicznych) | |
| MCP / API dla agentów | ❌ brak | **Luka** |

**Wspierane silniki:** SQL Server, Oracle (w tym RAC, Exadata), MySQL, PostgreSQL, MariaDB, SAP HANA, Azure SQL, Amazon RDS/Aurora.

---

## 3. Architektura

✅ [Dokumentacja producenta](https://documentation.solarwinds.com/en/success_center/dpa/content/dpa-architecture.htm):

- **Agentless.** Serwer DPA łączy się zdalnie z każdą instancją przez **JDBC**. Na monitorowanym serwerze nie instaluje się nic.
- **Quickpoll — próbkowanie raz na sekundę.** To jest mechanizm, na którym stoi cały produkt. Zapytanie „quickpoll" odpytuje aktywne sesje i ich stan oczekiwania co 1 s, a wynik jest agregowany w wymiarach: zapytanie × wait × użytkownik × program × host × czas.
- **Deklarowany narzut: <1%** na monitorowanej instancji.
- **Repozytorium:** własna baza danych (SQL Server, Oracle, MySQL, PostgreSQL — do wyboru).
- **Wdrożenie:** aplikacja Java na Windows lub Linux, lub appliance.

### Dlaczego 1 s ma znaczenie

Snapshot skumulowanych `dm_os_wait_stats` co 10 minut mówi: *„w ostatnich 10 minutach serwer spędził 40 s na `LCK_M_X`"*.
Próbkowanie aktywnych sesji co 1 s mówi: *„zapytanie X, uruchamiane przez użytkownika Y z hosta Z, czekało 40 s na `LCK_M_X` między 14:02:11 a 14:02:51"*.

Pierwsza informacja pozwala postawić hipotezę. Druga zamyka sprawę. **To jest cała różnica między monitoringiem a diagnostyką** — i to jest to, co klienci kupują za 2–4 tys. USD za instancję.

---

## 4. UX

**Mocne strony:**
- Główny widok (stacked bar chart czasu odpowiedzi wg wait type, oś czasu) jest **wzorcem branżowym**. Odpowiada na pytanie „co się dzieje" w mniej niż sekundę.
- Drill-down jest spójny: wykres → dzień → godzina → zapytanie → plan.
- Advisors podają rekomendację z uzasadnieniem, nie samo „dodaj indeks".

**Słabe strony (powtarzalne w recenzjach 🟡):**
- Interfejs wygląda i działa jak aplikacja z 2015 roku; ciężki UI oparty o Javę.
- Wdrożenie i konfiguracja uprawnień w środowiskach wieloinstancyjnych jest pracochłonna.
- Integracja z SolarWinds Platform bywa wymuszana architektonicznie — trudno używać DPA jako narzędzia w pełni samodzielnego w większej organizacji.
- Licencjonowanie per instancja mocno karze środowiska z wieloma małymi instancjami (dev/test/QA). Zespoły de facto rezygnują z monitorowania nieprodukcyjnych baz — co jest dokładnie tam, gdzie problemy powstają.

---

## 5. Model biznesowy

- **Wyłącznie komercyjny.** Brak wersji darmowej, brak open source.
- Licencja **per monitorowana instancja bazy danych**, wieczysta (+18–20% maintenance rocznie) lub subskrypcyjna.
- Cennik orientacyjny 🟡: ~1 195 USD/rok (SQL Server, edycja bazowa) → ~4 695 USD/rok (Oracle RAC). Typowa subskrypcja 2 500–4 000 USD/instancję/rok. Estate 10–25 instancji: 20–50 tys. USD/rok.
- Rabaty 20–30% standardowe przy umowach wieloletnich lub bundlach.
- **Właściciel:** od 2025-04-17 SolarWinds należy do **Turn/River Capital** (transakcja 4,4 mld USD, all-cash) ✅.

---

## 6. Słabości wykorzystywalne przez PulseDB

| Słabość | Jak wykorzystać |
|---------|-----------------|
| **Cena per instancja** | Self-hosted za darmo. Najsilniejszy argument dla estate dev/test/QA, które dziś jest niemonitorowane. |
| **Brak API dla agentów AI / MCP** | PulseDB jako narzędzie natywne dla workflow „DBA + Claude Code / Cursor". |
| **Zamknięte repozytorium danych** | PulseDB trzyma dane w PostgreSQL użytkownika — można je dowolnie odpytywać, eksportować, łączyć z własnymi danymi. |
| **Ciężkie wdrożenie (Java, appliance)** | `docker compose up`. |
| **Właściciel private equity** | Ryzyko wzrostu cen i spowolnienia rozwoju → argument „exit strategy" w rozmowie z klientem. 🟡 hipoteza oparta na wzorcu branżowym, nie na potwierdzonych działaniach Turn/River. |

## 7. Czego NIE da się podrobić

- **Response Time Analysis z próbkowaniem 1 s wymaga stałego, taniego połączenia z instancją i przemyślanego modelu agregacji.** To nie jest funkcja do zrobienia „przy okazji" — to jest architektura produktu. Jeśli PulseDB tego nie ma, nie jest alternatywą dla DPA, tylko innym rodzajem narzędzia (i powinien się tak nazywać).
- Wsparcie dla Oracle/SAP HANA — nie warto próbować.
- Anomaly detection oparte na latach danych z tysięcy instalacji.

---

## 8. Wnioski dla PulseDB

1. **Skopiuj główny widok.** Stacked bar chart „czas oczekiwania w czasie, kolorowany typem wait, klikalny do zapytania" to sprawdzony wzorzec UX. Nie wymyślaj nowego.
2. **Zdecyduj świadomie o częstotliwości próbkowania — to decyzja produktowa, nie techniczna.** 1 s = konkurent DPA. 10 min = narzędzie do analizy trendów. Nie ma nic pośrodku, co byłoby uczciwe wobec użytkownika.
3. **Nie obiecuj „alternatywy dla DPA" dopóki nie ma sesyjnego samplingu.** Ta obietnica jest weryfikowana w pierwszych 10 minutach użycia.
4. **Licencjonowanie per instancja to najboleśniejszy punkt klientów DPA.** Cały przekaz marketingowy PulseDB może stać na jednym zdaniu: *„monitoruj całe estate, także dev i test, bez liczenia instancji"*.
