# 002 — Zdjąć `continue-on-error` z czterech kroków CI

**Data:** 2026-07-30 · **Status:** `done` · **Waga:** średnia

## Wykonane 2026-07-30

Wszystkie cztery `continue-on-error` zdjęte — CI egzekwuje pełny zestaw 7 kroków.

| # | Naprawa |
|---|---|
| 1 | `black .` — przeformatowany `app/modules/settings/router.py` |
| 2 | Usunięty zbędny `# type: ignore[assignment]` w `cli/main.py:104` |
| 3 | **Nie był to błąd kodu produkcyjnego** — patrz niżej |
| 4 | Dodany `test.exclude` w `vitest.config.ts` (istniejący `exclude` dotyczył wyłącznie `coverage`) |

### Pozycja 3 — diagnoza

`ConvertEmptyStringsToNoneMiddleware` **poprawnie** łapie `json.JSONDecodeError` i przepuszcza nieparsowalne ciało dalej. Wywalał się **fixture testu**: endpointy `/test` w `tests/test_convert_empty_strings_middleware.py` robiły `json.loads(body)` bez obsługi wyjątku, więc to one rzucały przy ciele `"invalid json"` i przy `Content-Type: application/x-www-form-urlencoded`. Testy mierzyły odporność własnego fixture'u, nie zachowanie middleware'u.

Naprawa: wspólny helper `_echo_body` w fixture, parsujący defensywnie i zwracający 400 przy niepoprawnym JSON — zgodnie z tym, czego oba testy i tak oczekiwały (`assert response.status_code in (422, 400)`). Kod produkcyjny nietknięty.

### Uwaga metodologiczna ⚠️

`pytest` **nie jest** zainstalowany w tym środowisku ani globalnie, ani w venv w repo. Weryfikacja wymagała zbudowania środowiska tymczasowego (`uv venv --python 3.12` + `requirements.txt`).

Przy okazji: `mypy` uruchomiony **bez** zainstalowanych zależności zgłasza 29 fałszywych błędów w 14 plikach (typy z FastAPI/SQLAlchemy rozjeżdżają się do `Any`). Z zależnościami: `Success: no issues found in 126 source files`. Uruchamianie `mypy` poza środowiskiem z zależnościami nie jest miarodajne — CI instaluje `requirements.txt` przed krokiem `mypy`, więc jest poprawne.

## Kontekst

`.github/workflows/ci.yml` powstał w ramach Fazy 0 ([roadmap.md](../roadmap.md) §3, element 2). Cztery kroki są tymczasowo przepuszczane, bo repo ich dziś nie przechodzi. Każdy ma w workflow komentarz `# TODO`. Wszystkie przyczyny ✅ zweryfikowane lokalnym uruchomieniem 2026-07-30.

Dopóki te cztery pozycje wiszą, CI **wykrywa regresje tylko w połowie zakresu** — `ruff`, `pnpm lint` i `pnpm type-check` przechodzą i są egzekwowane.

## Do naprawy

| # | Krok | Przyczyna | Koszt 🟡 |
|---|---|---|---|
| 1 | `black --check .` (backend) | `app/modules/settings/router.py` wymaga reformatu | minuty — `black .` |
| 2 | `mypy .` (backend) | `cli/main.py:104` — „Unused type: ignore comment" | minuty |
| 3 | `pytest` (backend) | 2 z 170 testów failuje w `test_convert_empty_strings_middleware.py` | do zbadania — **jedyna pozycja, która może być realnym błędem, nie kosmetyką** |
| 4 | `pnpm test:run` (frontend) | `vitest.config.ts` **nie ma** `exclude` w discovery testów (istniejący `exclude` w linii 18 dotyczy wyłącznie `coverage`), więc vitest łapie specyfikacje Playwrighta z `tests/e2e/**` i `tests/integration/**` i crashuje. Z `--exclude` te same 31 testów przechodzi ✅ | minuty — dodać `test.exclude` |

## Kolejność

Pozycje 1, 2 i 4 to minuty pracy i warto je zrobić razem — po nich CI egzekwuje 6 z 7 kroków. Pozycja 3 wymaga diagnozy: dwa failujące testy middleware to albo błąd w skopiowanym kodzie, albo test zależny od środowiska. Do rozstrzygnięcia przed uznaniem platformy za fundament (kryterium wyjścia z Fazy 0).

## Uwaga

Playwright (`tests/e2e`, `tests/integration`) świadomie **nie jest** w CI — wymaga żywego stacku frontend + backend + baza. Osobna decyzja, nie ta.
