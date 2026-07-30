# Idea: IDE-style / Desktop-style UI

## Opis

Jednym z kierunków projektowania PulseDB jest odejście od klasycznego wyglądu aplikacji SaaS na rzecz interfejsu inspirowanego profesjonalnymi narzędziami desktopowymi używanymi przez administratorów baz danych i programistów.

Celem nie jest kopiowanie istniejących aplikacji, lecz wykorzystanie sprawdzonych wzorców UX, które są dobrze znane grupie docelowej.

Przykładowe określenia tego stylu:

- IDE-style UI
- Desktop-style UI
- Professional desktop application
- Technical application UI

---

## Charakterystyczne elementy

Rozważyć wykorzystanie:

- Menu Bar (File, Edit, View, Tools, Help)
- Toolbar z ikonami
- Kaskadowe menu (dropdown)
- Context Menu (PPM)
- Tree View / Explorer
- Dockowalne panele
- Zakładki (Tabs)
- Split View
- Status Bar
- Breadcrumbs
- Command Palette
- Skróty klawiaturowe

Jednocześnie wykorzystać nowoczesne komponenty UI wewnątrz widoków, takie jak:

- tabele,
- wykresy,
- formularze,
- filtry,
- dashboardy,
- side panels.

---

# Research Task: UI / UX

Przeprowadzić research interfejsów użytkownika profesjonalnych narzędzi dla administratorów baz danych oraz developerów.

## Cel

Odpowiedzieć na pytania:

- Jak wygląda główna nawigacja?
- Jak organizowane są widoki?
- Jak użytkownik przechodzi od ogólnego dashboardu do szczegółowej diagnostyki?
- Jak wygląda analiza pojedynczego zapytania?
- Jak prezentowane są execution plans?
- Jak wygląda analiza wait statistics?
- Jak rozwiązano pracę z wieloma serwerami i bazami danych?
- Jakie elementy UX warto wykorzystać w PulseDB?

---

## Aplikacje do analizy

### Database tools

- SQL Server Management Studio (SSMS)
- Azure Data Studio
- DataGrip
- DBeaver
- pgAdmin
- Oracle SQL Developer

### Monitoring

- SolarWinds Database Performance Analyzer
- Redgate SQL Monitor
- Datadog Database Monitoring
- New Relic
- Dynatrace
- Grafana
- Kibana

---

## Efekt researchu

Przygotować dokument zawierający:

- najlepsze praktyki UX,
- elementy warte zaadaptowania,
- elementy, których należy unikać,
- propozycję ogólnego layoutu PulseDB,
- uzasadnienie wyboru stylu IDE-style / Desktop-style.
