# Platformy observability: Datadog, New Relic, Dynatrace, Grafana

**Data:** 2026-07-30 · **Kategoria:** konkurencja pośrednia (segment B) · **Rola:** definiują oczekiwania wobec integracji i UX

---

## 1. Dlaczego to jest inny rynek

Platformy observability **nie sprzedają diagnostyki bazy danych**. Sprzedają *jeden panel dla całego stacku* — i moduł bazodanowy jest w tej ofercie sposobem domknięcia śladu transakcji, a nie produktem samym w sobie.

Konsekwencja: **PulseDB nie wygra z Datadogiem u klienta, który już płaci Datadogowi.** Dołożenie DBM to u nich zmiana pozycji w fakturze, a nie wdrożenie nowego narzędzia. Za to PulseDB może wygrać wszędzie tam, gdzie:
- dane produkcyjne nie mogą opuścić infrastruktury,
- nie ma budżetu na per-host SaaS,
- baza danych jest problemem samym w sobie, a nie elementem śladu APM.

---

## 2. Datadog Database Monitoring

### Funkcje ✅ ([dokumentacja](https://docs.datadoghq.com/database_monitoring/))

| Obszar | Zakres |
|--------|--------|
| Query Metrics | historia znormalizowanych zapytań, filtrowalna po zespole, użytkowniku, hoście |
| Query Samples | próbki wykonań w czasie rzeczywistym — wyłapują rzadkie wolne zapytania i outliery |
| Explain Plans | wizualizacja planu + **śledzenie zmian planu w czasie** |
| Host Monitoring | zdrowie i konfiguracja hosta bazy |
| Optimization Recommendations | automatyczne sugestie |
| Custom Metrics | własne zapytania (`custom_queries`) jako metryki |
| Alerty, dashboardy, raporty | pełne, na poziomie platformy |
| API | ✅ platformy (nie domenowe API bazy) |
| MCP | 🟡 Datadog ma integracje AI; brak dedykowanego MCP dla DBM |

**Silniki:** PostgreSQL (self-hosted, RDS, Aurora, Cloud SQL, AlloyDB, Azure, Heroku, Supabase), MySQL, Oracle (self-hosted, RDS, RAC, Exadata, Autonomous), SQL Server (self-hosted, RDS, Azure, Cloud SQL), MongoDB + Atlas, DocumentDB, ClickHouse ✅.

To jest **najszersze pokrycie silników na rynku** i PulseDB nie ma szans go dogonić — ani nie powinien próbować.

### Architektura

- **Agent-based.** Wymaga Datadog Agent na hoście (lub konfiguracji dla managed cloud).
- Wymaga przygotowania bazy: dedykowany użytkownik, rozszerzenia (`pg_stat_statements` dla Postgres), schemat funkcji pomocniczych.
- Dane wychodzą do chmury Datadoga.

### Model biznesowy i cena

- **~70 USD/host/miesiąc** za Database Monitoring 🟡, **ponad** kosztem Infrastructure Monitoring (15–18 USD/host/mies.).
- Rozliczenie per host, nie per instancja.
- Realny koszt monitorowania 10 baz: **~10 000 USD/rok** tylko za DBM.

### Słabości

| Słabość | Znaczenie dla PulseDB |
|---------|----------------------|
| **Dane opuszczają infrastrukturę** — łącznie z tekstami zapytań i planami | 🔴 blocker w sektorze finansowym, publicznym, medycznym, w środowiskach on-prem. **To jest główny rynek PulseDB.** |
| **Koszt i jego nieprzewidywalność** | Datadog ma reputację faktur rosnących szybciej niż infrastruktura |
| **Wymaga agenta i modyfikacji bazy** | PulseDB agentless = przewaga we wdrożeniu |
| **Brak własności danych** | Po zakończeniu subskrypcji historia znika |
| **Wymaga, żeby zespół już był w Datadogu** | Samodzielny zakup DBM jest rzadki |

---

## 3. New Relic

- Traktuje bazę danych **jako część APM**, nie jako osobny byt: wywołania SQL są powiązane z konkretnymi transakcjami w kodzie ✅.
- Mocna strona: dla developera pytającego „które moje endpointy są wolne przez bazę" — najlepsza odpowiedź na rynku.
- Słaba strona: dla DBA pytającego „co się dzieje na tej instancji" — perspektywa jest niekompletna. Brak głębokiej analityki wait events na poziomie instancji.
- Model: konsumpcyjny (per GB + per użytkownik), reputacja „uczciwej ceny" wśród platform 🟡.
- Dostęp do baz spoza kontekstu aplikacji jest ograniczony.

**Wniosek:** New Relic i PulseDB odpowiadają na różne pytania. Ryzyko konkurencyjne — niskie.

---

## 4. Dynatrace

- **Davis AI** — automatyczna analiza przyczyn źródłowych, auto-discovery ograniczające konfigurację ręczną; **Grail** jako lakehouse danych ✅.
- Najsilniejszy w dużych, złożonych środowiskach enterprise.
- Najdroższy i najbardziej złożony w kategorii 🟡.
- Baza danych jest tu jednym z wielu źródeł sygnału; brak dedykowanej głębi klasy DPA.

**Wniosek:** Dynatrace kupuje CIO dużej organizacji dla całego stacku. PulseDB nie spotka się z nim w tym samym procesie zakupowym.

---

## 5. Grafana + eksportery bazodanowe

To nie jest produkt, to jest **złożenie z klocków** — i najczęstsza dziś alternatywa dla płatnego monitoringu.

**Typowy stack:** `postgres_exporter` / `sql_exporter` → Prometheus lub VictoriaMetrics → Grafana + gotowe dashboardy.

| Zalety | Wady |
|--------|------|
| Darmowe, self-hosted | **Metryki, nie diagnostyka** |
| Ogromny ekosystem eksporterów | Brak tekstów zapytań, brak planów wykonania |
| Zespół zwykle już ma Grafanę | Brak korelacji wait → zapytanie |
| Pełna kontrola nad danymi | Konieczne samodzielne pisanie alertów (PromQL) |
| | Utrzymanie stacku to osobna praca |

**Kluczowe rozróżnienie, które PulseDB musi umieć wyartykułować:**

> Prometheus odpowiada na pytanie *„czy baza ma się dobrze"*.
> PulseDB ma odpowiadać na pytanie *„które zapytanie i dlaczego psuje wydajność"*.

To są różne modele danych. Metryki numeryczne w TSDB nie przechowują tekstu zapytania, planu XML ani atrybucji wait → query. Zespół, który ma Grafanę i wciąż nie wie, co spowalnia bazę, jest **idealnym pierwszym użytkownikiem PulseDB**.

**Ryzyko:** ktoś powie „przecież mam już Grafanę". Odpowiedzią nie jest walka z Grafaną, tylko **eksport metryk PulseDB w formacie Prometheus** — koegzystencja zamiast zastępowania. Tani feature, duży efekt w adopcji.

---

## 6. Wnioski dla PulseDB

1. **Nie konkuruj funkcjonalnie z Datadogiem.** Konkuruj modelem: *dane zostają u Ciebie, koszt jest zerowy, wdrożenie to jeden `docker compose up`*.
2. **Sovereignty jest najlepszym argumentem sprzedażowym PulseDB w segmencie B.** Teksty zapytań i plany wykonania to dane produkcyjne — dla wielu organizacji ich wysyłka do SaaS jest wykluczona regulacyjnie.
3. **Skopiuj z Datadoga dwie rzeczy:** *query samples* (próbki wykonań, nie tylko agregaty) i *plan change tracking* (regresja planu to najczęstsza przyczyna nagłego spowolnienia).
4. **Zaimplementuj endpoint `/metrics` w formacie Prometheus.** Pozwala wejść do organizacji, które mają już Grafanę, bez konfrontacji.
5. **Nie buduj własnego pełnego stosu alertowego z routingiem, eskalacją i on-call.** Integruj się: webhook, Alertmanager, Slack, e-mail. Tu przegrana z platformami jest pewna i kosztowna.
