# Frontend `Type check` czerwony na `develop`

**Data:** 2026-07-30 · **Status:** `done`

## Opis

CI job `Frontend (lint, typy, testy)` → krok `Type check` kończył się
`failure` na `develop` HEAD (commit `9b10ab0937b`, workflow run
`30549183351`) — `Lint` przechodził, `Type check` nie, `Unit tests` był
pomijany w efekcie. Znalezione przy okazji weryfikacji stanu CI podczas
pracy nad [2026-07-30-phase0-foundation.md](../plans/2026-07-30-phase0-foundation.md)
(backend).

## Przyczyna

Dwie niezależne przyczyny:

1. **Prawdziwy root cause: `.gitignore` po cichu ignorował `src/lib/`.** Sekcja
   "Python" w korzeniowym `.gitignore` miała `lib/` i `lib64/` bez zakotwiczenia
   do `backend/` — standardowe wzorce artefaktów `venv`, ale bez slasha na
   początku dopasowują się na **dowolnej głębokości**, więc `src/lib/` też
   wpadał w ignorowanie. Katalog istniał lokalnie u kogoś (albo nigdy — nie da
   się odróżnić), ale nigdy nie trafił do repo, więc `git status` nigdy go nie
   pokazywał jako brakujący. Naprawiono zawężając wzorce do `backend/lib/` /
   `backend/lib64/`.
2. Efekt: kilkadziesiąt komponentów (`src/components/ui/**`, `DataTable*.vue`,
   layouty) importowało `cn`/`valueUpdater` z `@/lib/utils` i `copyToClipboard`
   z `@/lib/copyToClipboard` — realny, brakujący kod, nie tylko martwa
   referencja. `src/modules/auth/guards/twoFactorGuard.ts` dodatkowo importował
   `requiresTwoFactorVerification` z `@/modules/auth/lib/jwtDecoder` — ścieżka
   i funkcja, które nigdy nie istniały (dekoder JWT jest pod
   `src/shared/utils/jwtDecoder.ts`, ale bez tej funkcji) — to już ten sam
   rodzaj długu co [issue 004](2026-07-30--004--dead-logs-import-broke-ci-pytest.md).

## Naprawa

- Zawężono `.gitignore` (`lib/`/`lib64/` → `backend/lib/`/`backend/lib64/`).
- Dodano `src/lib/utils.ts` (`cn` — standardowy helper shadcn-vue: `clsx` + `tailwind-merge`; `valueUpdater` — standardowy helper `@tanstack/vue-table`) i `src/lib/copyToClipboard.ts` (Clipboard API z fallbackiem `document.execCommand` dla kontekstów niebezpiecznych).
- Dodano `requiresTwoFactorVerification(token)` do `src/shared/utils/jwtDecoder.ts` (sprawdza `tfaPending === true && tfaVerified !== true` z już istniejącego `JWTPayload`) i poprawiono import w `twoFactorGuard.ts` na `@/shared/utils/jwtDecoder`.
- `pnpm type-check`, `pnpm lint`, `pnpm test:run` przechodzą czysto po naprawie.

## Powiązane

- [2026-07-30-phase0-foundation.md](../plans/2026-07-30-phase0-foundation.md)
- [issue 002](2026-07-30--002--ci-continue-on-error.md) — CI miało być w pełni egzekwowane
- [issue 004](2026-07-30--004--dead-logs-import-broke-ci-pytest.md) — analogiczny dług po stronie backendu
