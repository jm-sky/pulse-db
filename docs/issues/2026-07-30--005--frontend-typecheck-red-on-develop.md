# Frontend `Type check` czerwony na `develop`

**Data:** 2026-07-30 · **Status:** `todo`

## Opis

CI job `Frontend (lint, typy, testy)` → krok `Type check` kończy się
`failure` na `develop` HEAD (commit `9b10ab0937b`, workflow run
`30549183351`) — `Lint` przechodzi, `Type check` nie, `Unit tests` jest
pomijany w efekcie. Znalezione przy okazji weryfikacji stanu CI podczas
pracy nad [2026-07-30-phase0-foundation.md](../plans/2026-07-30-phase0-foundation.md)
(backend), nie zdiagnozowane — poza zakresem tamtej pracy.

## Do zrobienia

- Uruchomić `pnpm type-check` lokalnie na `develop`, zidentyfikować błąd(y)
- Naprawić lub, jeśli błąd wynika z niedokończonej pracy na innej gałęzi, ustalić czy to regresja z ostatniego mergowanego PR (`ide-style-design-issue`)

## Powiązane

- [2026-07-30-phase0-foundation.md](../plans/2026-07-30-phase0-foundation.md)
- [issue 002](2026-07-30--002--ci-continue-on-error.md) — CI miało być w pełni egzekwowane
