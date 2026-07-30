# Martwy import `app.modules.logs` wywalał `create_app()` i cały pytest w CI

**Data:** 2026-07-30 · **Status:** `done`

## Opis

`backend/app/api/router.py` importował `app.modules.logs.router`, moduł
którego **nigdy nie było** w tym repo (`git log --all -- backend/app/modules/logs`
nie zwraca nic) — boilerplate skopiował referencję do routera bez samego
modułu, ten sam rodzaj długu co
[issue 001](2026-07-30--001--boilerplate-dead-code-cleanup.md).

`register_routers()` w `app_factory.py` łapie `ImportError` tylko po to, żeby
go zalogować i **przerzucić dalej** (`raise`), więc `create_app()` zawsze
rzucał na starcie. `tests/conftest.py` importuje `main.app` na poziomie
modułu, więc **cały `pytest` był czerwony** — potwierdzone na `develop`
(commit `9b10ab0937b`, workflow run `30549183351`, job `Pytest (testy)` =
`failure`), mimo że [roadmap.md](../roadmap.md) i historia commitów zakładały
zielone CI po `6c40bfc` ("wszystkie 7 kroków egzekwowane"). Ten sam commit też
był w praktyce czerwony na `Pytest` — status nie odzwierciedlał rzeczywistości.

Drugie, nieszkodliwe wystąpienie: `cli/commands/db.py` → `MODEL_MODULES`
listował `app.modules.logs.db_models`, ale ta ścieżka ma już
`try/except ModuleNotFoundError` z ostrzeżeniem, więc nie psuła niczego —
usunięta przy okazji dla porządku.

## Wpływ

Blokował całą pracę wymagającą uruchomienia pytest (w tym walidację tej
iteracji Fazy 0) i oznaczał, że CI na `develop` nie chroniło niczego od
commitu `6c40bfc` mimo deklaracji w commit message.

## Naprawa

Usunięto martwy import i rejestrację route'a z `app/api/router.py`, oraz
wpis z `MODEL_MODULES` w `cli/commands/db.py`. Bez zmian funkcjonalnych —
`/api/logs` nigdy nie działało (import padał wcześniej), więc nic nie traci
działania.

## Powiązane

- [2026-07-30-phase0-foundation.md](../plans/2026-07-30-phase0-foundation.md)
- [issue 001](2026-07-30--001--boilerplate-dead-code-cleanup.md) — ten sam rodzaj długu z boilerplate'u
- [issue 002](2026-07-30--002--ci-continue-on-error.md) — CI miało być w pełni egzekwowane od tego commitu
