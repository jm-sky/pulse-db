# Redgate Monitor (dawniej SQL Monitor)

**Data:** 2026-07-30 · **Kategoria:** konkurencja bezpośrednia (segment A) · **Rola:** benchmark UX i alertowania

---

## 1. Pozycja

Redgate Monitor to **domyślny wybór w świecie SQL Server**, kupowany zwykle nie przez zespół platformowy, lecz przez DBA. Redgate zbudował markę na narzędziach dla dewelopera SQL Server (SQL Prompt, SQL Compare) i Monitor sprzedaje się w tym ekosystemie.

W przeciwieństwie do DPA, Redgate Monitor to **narzędzie zdrowia estate**, nie narzędzie diagnostyki jednego zapytania. Odpowiada na pytanie „czy coś jest nie tak z moimi 60 serwerami", a nie „dlaczego ta procedura jest wolna".

---

## 2. Funkcje

| Obszar | Standard | Enterprise |
|--------|----------|------------|
| Monitoring zapytań, wait stats | ✅ | ✅ |
| Execution plans | ✅ | ✅ |
| Analiza indeksów | ✅ (podstawowa) | ✅ |
| Alerty (~60 typów, baseline'y) | ✅✅ **najmocniejsza strona produktu** | ✅ |
| Dashboardy estate (overview floty) | ✅ | ✅ |
| Raporty | ✅ | ✅ |
| Deployment tracking (korelacja wydajności z wdrożeniami) | ✅ | ✅ |
| **Security monitoring i audyt konfiguracji (CIS)** | ❌ | ✅ |
| **Wysoka dostępność (load balancer)** | ❌ | ✅ |
| **Comprehensive Data API** | ❌ | ✅ |
| **Sensitive action log** | ❌ | ✅ |
| AI features | 🟡 ograniczone, brak wyróżniającej się oferty | |
| MCP | ❌ | ❌ |

✅ Podział funkcji potwierdzony na [stronie edycji Enterprise](https://www.red-gate.com/products/redgate-monitor/enterprise/).

**Silniki:** SQL Server (pełne wsparcie), PostgreSQL (nowsze, węższe), Oracle (wymieniany w menu produktu, poziom wsparcia ❓), Azure SQL, AWS RDS.

---

## 3. Architektura

- **Agentless dla SQL Server** — Base Monitor łączy się przez T-SQL i WMI, brak instalacji na monitorowanym serwerze.
- **Storage:** własna baza repozytorium na SQL Server.
- **Deployment:** Windows (self-hosted) lub SaaS (Redgate hostuje; wtedy „install an agent in seconds" ✅).
- **Skalowanie:** Base Monitor obsługuje wiele instancji; Enterprise dodaje HA przez load balancer.

**Ograniczenie:** produkt jest głęboko Windows/SQL-Server-centryczny. Wsparcie dla PostgreSQL zostało dołożone później i nie ma tej samej głębi.

---

## 4. UX — tu Redgate jest najlepszy na rynku

**Estate overview** to prawdopodobnie najlepiej zaprojektowany widok floty w kategorii: kolorowe kafle serwerów, natychmiastowa identyfikacja problemu, spójny drill-down do wykresów metryk.

**Alerty są prawdziwym produktem, nie dodatkiem:**
- ~60 typów alertów z sensownymi domyślnymi progami
- baseline'y — próg może być relatywny wobec typowego zachowania serwera
- konfiguracja per serwer / per grupa / globalnie, z dziedziczeniem
- eskalacja, wyciszanie, okna serwisowe

**To jest wzorzec do skopiowania.** Alertowanie w narzędziach OSS jest z reguły albo nieobecne, albo sprowadzone do „PromQL i radź sobie sam". Redgate pokazuje, że wartość leży w **domyślnych progach opartych na wiedzy domenowej** — użytkownik nie chce pisać reguł, chce dostać zestaw, który działa od razu.

**Słabości UX 🟡:**
- Diagnostyka „dlaczego to zapytanie jest wolne" jest wyraźnie płytsza niż w DPA — brak atrybucji czasu oczekiwania do zapytania na poziomie DPA.
- Interfejs jest gęsty; nowy użytkownik potrzebuje czasu na nauczenie się nawigacji.

---

## 5. Model biznesowy

- **Wyłącznie komercyjny**, licencja **per monitorowany serwer/rok**, z progami wolumenowymi (1–4, 5–9, 10–19, 20+).
- Cena Standard: od ~1 164–1 220 USD/serwer/rok 🟡 (Redgate **nie publikuje kwot** — tabela cenowa na stronie ładowana jest dynamicznie i nie zwraca wartości; dane pochodzą z ComponentSource i G2).
- Enterprise: cena na zapytanie ✅.
- Dostępny przez AWS Marketplace i Azure Marketplace.
- Wariant SaaS obok self-hosted.

**Obserwacja:** brak publicznej ceny to sygnał, że sprzedaż jest prowadzona przez kontakt z handlowcem. Dla zespołu, który chce „po prostu zacząć monitorować", to tarcie — i to jest punkt wejścia dla produktu OSS.

---

## 6. Najważniejszy wniosek: **API jest funkcją Enterprise**

To jest, wraz z zajęciem niszy przez Darling Data (patrz [opensource.md](opensource.md)), najistotniejsze odkrycie tego researchu.

Redgate — lider UX w segmencie SQL Server — **traktuje dostęp programistyczny do własnych danych monitoringowych jako funkcję premium**, sprzedawaną z najdroższą edycją i bez publicznej ceny.

Oznacza to, że dla zespołu, który chce:
- zbudować własny dashboard,
- podpiąć monitoring pod CI/CD,
- pozwolić agentowi AI czytać dane wydajnościowe,
- wyeksportować historię do własnej hurtowni,

ścieżka u lidera rynku prowadzi przez rozmowę handlową i najwyższy tier cenowy.

**PulseDB może uczynić z tego swoją tożsamość: pełne API domenowe jako funkcja darmowa i pierwszorzędna — to nie dodatek, to jest interfejs produktu.**

---

## 7. Słabości wykorzystywalne przez PulseDB

| Słabość | Jak wykorzystać |
|---------|-----------------|
| API tylko w Enterprise | API-first, za darmo, z dokumentacją OpenAPI |
| Windows-only self-hosted | Docker/Linux native |
| Brak ceny publicznej | Transparentność: „0 zł, kod na GitHubie, żadnego handlowca" |
| Płytsza diagnostyka niż DPA | Postawić na głębię diagnostyki (jeśli będzie sampling) |
| Brak MCP | Natywne wsparcie dla agentów |
| Postgres jako obywatel drugiej kategorii | PostgreSQL i SQL Server równorzędnie od dnia pierwszego |

## 8. Czego NIE warto podrabiać

- **Nie próbuj dorównać zakresowi alertowania Redgate w MVP.** ~60 typów alertów z baseline'ami to lata dopracowywania. Zrób 8–12 alertów, które faktycznie mają znaczenie, z dobrymi domyślnymi progami.
- **Nie buduj deployment trackingu w MVP** — wymaga integracji z pipeline'ami klienta, wysoki koszt, wąska grupa odbiorców.
- **Nie kopiuj estate overview dla 200 serwerów.** PulseDB w wersji 1.0 obsłuży 5–30 instancji; widok floty projektowany pod tę skalę jest zupełnie inny (i prostszy).
