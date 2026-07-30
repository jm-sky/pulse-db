# PulseDB

## Vision

PulseDB to nowoczesne narzędzie do diagnostyki, monitorowania i optymalizacji wydajności baz danych.

Celem projektu jest stworzenie alternatywy dla rozwiązań klasy Database Performance Analyzer, z naciskiem na:

- self-hosted deployment,
- otwartość,
- rozszerzalność,
- API-first architecture,
- integrację z narzędziami AI.

---

# Cel produktu

Główne założenie:

> Narzędzie do diagnostyki i optymalizacji baz danych, darmowe przy self-hosted.

PulseDB pomaga administratorom, developerom i zespołom IT:

- wykrywać problemy wydajnościowe,
- analizować wolne zapytania,
- rozumieć przyczyny problemów,
- optymalizować strukturę baz danych.

---

# Licencja i model biznesowy

## Licencja

Projekt będzie rozwijany jako:

**AGPLv3**

Założenia:

- otwarty kod źródłowy,
- możliwość samodzielnego hostowania,
- budowanie zaufania społeczności.

Praktyczne konsekwencje klauzuli sieciowej AGPL dla self-hosted użycia:
[docs/licensing-faq.md](docs/licensing-faq.md).

---

## Model biznesowy

### Self-hosted

Darmowa wersja:

- pełny monitoring,
- własne wdrożenie,
- własna infrastruktura,
- własna baza danych.

Możliwe dodatkowe funkcje płatne:

- funkcje enterprise,
- dodatkowe integracje,
- rozszerzenia.

---

### Cloud

Płatna usługa SaaS:

Możliwe elementy:

- hosting,
- storage,
- backupy,
- zespoły,
- enterprise features,
- AI features.

---

# Fundament techniczny

Backend będzie oparty o istniejący projekt:

**gear-stack**

Stack bazowy:

- FastAPI
- PostgreSQL
- Users
- Authentication
- Roles / Permissions
- OAuth
- Two-Factor Authentication

PulseDB będzie rozwijany jako aplikacja bazująca na tym fundamencie.

---

# Obsługiwane bazy danych

## MVP

Pierwsze wspierane silniki:

- PostgreSQL
- Microsoft SQL Server

Architektura powinna umożliwiać dodanie kolejnych:

- MySQL / MariaDB
- Oracle
- inne silniki

Poprzez warstwę adapterów / connectorów.

---

# Architektura komunikacji

## API-first

API jest podstawowym interfejsem systemu.

Klienci:

- Web UI
- REST API
- CLI
- MCP Server

Każda funkcjonalność powinna być dostępna przez API.

---

# AI

AI jest dodatkiem, nie fundamentem produktu.

PulseDB musi działać w pełni bez AI.

## Integracja AI

Użytkownik może używać własnego AI poprzez:

- CLI
- MCP
- API

Przykładowe integracje:

- Claude Code
- Cursor
- ChatGPT
- Gemini
- OpenRouter
- własne modele

PulseDB nie jest zależny od jednego dostawcy AI.

---

# MVP - zbierane dane

Pierwsza wersja skupia się na diagnostyce wydajności.

Zakres:

## Query Performance

- historia zapytań SQL,
- czas wykonania,
- statystyki wykonania.

## Wait Analysis

- wait events,
- wait statistics.

## Execution Plans

- pobieranie planów wykonania,
- analiza planów.

## Index Analysis

- analiza indeksów,
- potencjalne problemy.

---

# Architektura zbierania danych

## Agentless

Pierwsza wersja działa bez agentów.

PulseDB łączy się bezpośrednio z monitorowanymi bazami danych.

Zalety:

- prostsze wdrożenie,
- mniej komponentów,
- łatwiejszy self-hosting.

---

## Możliwość przyszłego Agent Mode

Architektura powinna umożliwiać dodanie agentów w przyszłości.

Przykładowe zastosowania:

- środowiska enterprise,
- ograniczenia sieciowe,
- wymagania bezpieczeństwa.

---

# Storage danych

PulseDB przechowuje własną historię danych.

System posiada własną bazę danych do przechowywania:

- historii zapytań,
- metryk,
- planów wykonania,
- statystyk.

Celem jest umożliwienie:

- analizy trendów,
- wykrywania regresji,
- porównywania okresów,
- analizy zmian wydajności.

---

# Metodyka rozwoju

Projekt rozwijany etapami:

```
Research
   ↓
Planning
   ↓
Architecture Review
   ↓
Implementation
   ↓
Code Review
   ↓
Post-Implementation Review
   ↓
Periodic Review
```

---

# Research

Analiza konkurencji:

Przykładowe produkty:

- SolarWinds Database Performance Analyzer
- Redgate SQL Monitor
- dbWatch
- Datadog Database Monitoring
- New Relic
- Dynatrace

Analizowane obszary:

- funkcje,
- UX,
- architektura,
- mocne strony,
- słabe strony,
- przewagi konkurencyjne.

---

# AI Review Process

Każdy większy etap powinien być oceniany przez niezależny model AI.

Review obejmuje:

- research,
- architekturę,
- roadmapę,
- decyzje techniczne,
- UX,
- backlog,
- implementację.

Cel:

- wykrywanie braków,
- identyfikacja ryzyk,
- alternatywne rozwiązania,
- poprawa jakości.

---

# Periodic Review

Cykliczny przegląd projektu.

Domyślnie:

**co 6 miesięcy**

Zakres:

- aktualizacja researchu konkurencji,
- przegląd architektury,
- przegląd technologii,
- ocena roadmapy,
- ocena UX,
- identyfikacja długu technicznego.

---

# Aktualne decyzje otwarte

Do późniejszego ustalenia:

- szczegółowa architektura deploymentu,
- podział usług Docker,
- frontend stack,
- model pluginów,
- szczegóły Cloud vs Enterprise,
- roadmapa MVP.
