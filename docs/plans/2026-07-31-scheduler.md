# Plan: Scheduler dla kolektora i rollupów (Faza 0, element 8)

**Data:** 2026-07-31 · **Status:** `done`
**Kontekst:** [roadmap.md](../roadmap.md) §3 (Faza 0, element 8) · [ADR modelu danych](../research/2026-07-30-data-model.md)
**Poprzednik:** [plan rollupów](2026-07-31-rollups.md) (`done`) — roadmap §11 rekomendował harmonogram jako kolejny krok zaraz po rollupach, bo bez pętli ciągłe zbieranie jest tylko ręcznym powtarzaniem CLI

## Dlaczego ten zakres teraz

Roadmap §11 (rekomendacja z poprzedniej sesji), pozycja 1: wszystko dotąd —
trywialny kolektor, sampler sesji, kolektor statystyk zapytań, rollupy — to
pojedyncze ticki wywoływane ręcznie przez CLI. Kryterium wyjścia z Fazy 1
("sampler pracuje 7 dni bez przerwy") wymaga pętli, nie tylko poprawnej
logiki pojedynczego ticku.

## Co zrobiono

| # | Element | Gdzie |
|---|---|---|
| 8 | `Scheduler`: harmonogram per instancja (własna pętla per rodzaj ticku, różne kadencje współbieżnie) + globalna pętla utrzymania partycji | `backend/app/modules/monitoring/scheduler.py` |
| 8 | CLI: `cli monitoring run-scheduler` — proces pierwszoplanowy, czysty shutdown na SIGINT/SIGTERM | `backend/cli/commands/monitoring.py` |
| 8 | `docker-compose.yml`: serwis `scheduler` (ten sam obraz co `app`, komenda `python cli.py monitoring run-scheduler`) | `docker-compose.yml` |

### Decyzje projektowe

**Członkostwo instancji odpytywane, nie push.** `Scheduler` co
`instance_refresh_interval_seconds` (domyślnie 5 min) woła
`repository.list_instances()` i startuje/zatrzymuje pętle dla
zarejestrowanych/dezaktywowanych instancji. Odpytywanie zamiast zdarzeń jest
uzasadnione: rejestracja instancji nie jest operacją czasowo wrażliwą tak
jak sampling — 5 minut opóźnienia w podjęciu nowej instancji jest
akceptowalne, a event bus na to byłby przedwczesną złożonością.

**SQL Server dostaje tylko tick `trivial`.** `collect_active_sessions`/
`collect_query_stats` na `SqlServerEngineAdapter` rzucają
`NotImplementedError` (Faza 1, [plan Fazy 1](2026-07-30-phase1-diagnostic-core.md)).
Zaplanowanie tych ticków dla SQL Servera zamieniłoby harmonogram w pętlę
"złap i zaloguj ten sam wyjątek co sekundę" zamiast zgłosić brak wsparcia
raz. `_ticks_for_engine` filtruje po silniku.

**`asyncio.Event` + `asyncio.wait_for(event.wait(), timeout=interval)`
zamiast `asyncio.sleep` + `Task.cancel()`.** Ustawienie zdarzenia przerywa
oczekiwanie natychmiast, więc zatrzymanie schedulera nie czeka na
dokończenie bieżącego interwału (istotne dla ticku 1 s — zamknięcie nie
powinno czekać nawet potencjalnie minutę na tick rollupu). `Task.cancel()`
ścigałby się z własnym `try/except Exception` każdego ticku zamiast czysto
zakończyć pętlę między iteracjami.

**Rollupy nie mają własnego try/except na poziomie `rollups.py`** (w
przeciwieństwie do ticków kolektora, które nigdy nie propagują wyjątku).
Scheduler owija *każdy* tick (kolektor i rollup jednakowo) w ten sam
`try/except Exception` w `_run_periodic_tick` — jedna warstwa
bezpieczeństwa wystarcza, bo scheduler i tak jest jedynym wywołującym w
produkcji; dublowanie tej logiki w `rollups.py` byłoby przedwczesną
abstrakcją bez odrębnego konsumenta.

**Utrzymanie partycji jako osobna, globalna pętla**, nie per-instancja —
`ensure_daily_partitions`/`drop_expired_partitions` operują na wspólnych
tabelach faktów, niezależnie od tego, które instancje istnieją.

## Walidacja

Testy jednostkowe (`backend/tests/modules/monitoring/test_scheduler.py`, 7
testów: dobór ticków per silnik, generyczna pętla ticku z zamockowanymi
funkcjami — w tym przeżycie wyjątku bez przerwania pętli — synchronizacja
członkostwa instancji, pełny cykl życia `Scheduler.run()`/`stop()`) plus
**walidacja ręczna end-to-end na lokalnym PostgreSQL 16** (self-monitoring):

- `cli monitoring run-scheduler --instance-refresh-seconds 10
  --partitions-interval-seconds 20` uruchomiony w tle na 8 s, zatrzymany
  `SIGINT`: wystartował pętlę dla zarejestrowanej instancji, uruchomił
  utrzymanie partycji (25 partycji utworzonych z wyprzedzeniem), poprawnie
  wykrył i zalogował lukę na `session_sample`/`query_stats` (od poprzedniej
  ręcznej sesji CLI), po czym **6 realnych ticków `session_sample`** w ~8 s
  (kadencja ~1 s potwierdzona), plus po jednym ticku `trivial`/`query_stats`
  — wszystko potwierdzone w `collector_run`/`session_sample` po fakcie
- proces zakończył się kodem wyjścia `0` i wydrukował "Scheduler stopped" —
  czysty shutdown, żadnych wiszących tasków/ostrzeżeń asyncio

## Co zostaje

- **Rollupy nie mierzą własnego narzutu** — ta sama luka co odnotowana w
  [planie rollupów](2026-07-31-rollups.md) "Co zostaje"; teraz działają w
  pętli, więc widoczność ich czasu trwania zyskałaby na wartości.
  Nie zaimplementowane.
- **Jeden proces scheduler = jeden punkt awarii** dla wszystkich
  monitorowanych instancji. `restart: unless-stopped` w Docker Compose
  daje podstawową odporność; nic bardziej wyrafinowanego (wiele replik,
  koordynacja) nie jest w zakresie skali 5–30 instancji z wizji.
- **SQL Server nadal tylko `trivial`** — niezmienione względem Fazy 1,
  czeka na dostęp do żywej instancji.
- **Roadmap kryterium wyjścia z Fazy 1** ("sampler pracuje 7 dni bez
  przerwy") wymaga teraz tylko czasu, nie brakującego kodu — harmonogram
  istnieje i jest zweryfikowany, ale 7-dniowy przebieg ciągły nie był (i
  nie mógł być) uruchomiony w efemerycznym środowisku tej sesji.

## Powiązane

- [roadmap.md](../roadmap.md) §3 (Faza 0) — tabela stanu zaktualizowana
- [plan rollupów](2026-07-31-rollups.md) — poprzednia pozycja w kolejności rekomendacji
- [plan Fazy 1 — rdzeń diagnostyczny](2026-07-30-phase1-diagnostic-core.md) — źródło ograniczenia "SQL Server tylko trivial"
