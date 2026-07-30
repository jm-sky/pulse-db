# 001 — Usunąć pozostałości domen wykluczonych z boilerplate'u

**Data:** 2026-07-30 · **Status:** `done` · **Waga:** średnia (jedna pozycja: bezpieczeństwo)

## Wykonane 2026-07-30

Wszystkie pozycje 1–5 usunięte. Zakres okazał się **szerszy niż pierwotnie opisany** — dodatkowo znalezione i usunięte:

- **i18n `containers`, `items`, `reports`** (`src/modules/admin/i18n/locales/{en,pl}.ts`) — domena gear-stacka, nieujęta w pierwotnym issue. Moduł `admin` ma tylko `AdminDashboardPage` i `AdminUsersPage`; wszystkie pięć sekcji (`limits`, `subscriptions`, `containers`, `items`, `reports`) było martwe, zero użyć poza plikami tłumaczeń. Pliki 259 → 63 linii.
- **`backend/pyproject.toml`: `license = {text = "MIT"}`** — niezgodne z `LICENSE` (AGPLv3) i z §6 wizji. Poprawione na `AGPL-3.0-or-later`.
- **`backend/pyproject.toml`: `requires-python = ">=3.11"`** — kod używa składni PEP 695 (`type X = ...`), która wymaga 3.12. Zweryfikowane empirycznie: na 3.11 aplikacja nie importuje się (`SyntaxError` w `app/core/csrf.py:36`). Poprawione na `>=3.12`, zgodnie z `python-version: '3.12'` w CI.
- **Komentarze o Stripe** w `app/core/csrf.py` i `app/core/middleware.py` — kod (fallback na pusty `WEBHOOK_PATHS`) zostawiony zgodnie z sekcją „Poza zakresem", ale komentarze przepisane, bo opisywały nieistniejącą integrację płatności w kodzie związanym z CSRF.

Usunięcie `openrouter_api_token` objęło migrację [`067_drop_openrouter_api_token.py`](../../backend/migrations/067_drop_openrouter_api_token.py).

Usunięcie `tid`/`trol` sięgnęło głębiej, niż zakładało issue: poza typami także `auth_utils.py` (roszczenia w `create_access_token`) oraz dwa testy w `test_auth_utils.py`. Testy zastąpione jednym, który sprawdza **odwrotną** własność — że żaden token nie niesie roszczeń tenantowych — z odsyłaczem do [ADR modelu danych](../research/2026-07-30-data-model.md) §8.

**Weryfikacja:** `ruff` ✅ · `black --check` ✅ · `mypy` (126 plików) ✅ · `pytest` 169 passed ✅ · `pnpm lint` ✅ · `pnpm type-check` ✅ · `pnpm test:run` 31 passed ✅

## Kontekst

Plan [2026-07-30-boilerplate-from-family.md](../plans/2026-07-30-boilerplate-from-family.md) deklarował `tenants, billing, AI, feature_limits` jako **„nie w repo"**. Inventory Fazy 3 wykazał, że częściowo zostały. Wszystkie pozycje ✅ potwierdzone w repo.

## To nie jest odrzucenie billingu, tenancy ani gatingu ⚠️

Wszystkie trzy są w planach ([vision.md](../vision.md) §5 i §6): multi-tenancy jako warunek konieczny Cloud, billing jako **krok 3** monetyzacji, gating jako mechanika funkcji enterprise. Usuwamy **implementację innego produktu**, nie funkcjonalność PulseDB:

- `openrouter_api_token` to token dostawcy AI — billing rodziny gear-stack za wywołania modelu. PulseDB ma zasadę odwrotną (§5 vision, „Miejsce AI"): użytkownik podłącza własny model, zero zależności od dostawcy. Ta kolumna nie ma zastosowania w **żadnym** scenariuszu PulseDB, także płatnym.
- `tid` / `trol` to tenancy przez roszczenia w tokenie. [ADR modelu danych](../research/2026-07-30-data-model.md) §8 wybrał inny mechanizm — tenant wyłącznie na `monitored_instance`, fakty dziedziczą przez `instance_id`.
- `/feature-limits` nie ma backendu; jednostka rozliczeniowa PulseDB (per instancja? per tenant?) jest **nierozstrzygnięta**, bo Cloud jest krokiem 3 i nieprojektowanym.

Kod zawierający cudzą odpowiedź na nasze nierozstrzygnięte pytanie będzie sugerował decyzję, której nie podjęliśmy. Koszt ponownego dodania po zaprojektowaniu Cloud: godziny.

## Do usunięcia

| # | Ścieżka | Co to jest |
|---|---|---|
| 1 | `backend/app/modules/auth/db_models.py:67` | Kolumna `openrouter_api_token` (`# Billing fields`), zerowana w `repositories.py:354`, nigdzie nie wystawiona w API |
| 2 | `backend/app/modules/auth/types/jwt.py` · `src/shared/types/jwt.type.ts` · `src/shared/utils/jwtDecoder.ts` | Martwe pola `tid` / `trol` (Tenant ID / Tenant Role) |
| 3 | `src/modules/admin/services/limitsApiService.ts` · `src/modules/admin/types/limits.types.ts` | Martwy frontend wołający nieistniejący endpoint `/feature-limits` |
| 4 | `src/modules/admin/i18n/locales/{en,pl}.ts` | Martwe sekcje „Feature Limits", „Subscriptions", „Billing" (wzmianka o Stripe) |
| 5 | `backend/migrations/README.md` | Opisuje nieistniejące migracje `001.5` / `002_add_gear_tables` / `003` z `GearContainerDB` / `GearItemDB`. Stan faktyczny: `000`, `001`, `002_create_users_table.py`, `066_add_token_version_to_users.py` |

## Uzasadnienie priorytetu

**Pozycja 1 jest kwestią bezpieczeństwa, nie porządku.** Martwa kolumna w kształcie tokenu API w tabeli użytkowników to dokładnie to, co wychodzi w przeglądzie bezpieczeństwa produktu, którego przekazem jest minimalizacja uprawnień i audytowalność ([vision.md](../vision.md) §3.6). Usunięcie wymaga migracji `DROP COLUMN`.

**Pozycja 2** — decyzja świadoma: [ADR modelu danych](../research/2026-07-30-data-model.md) §8 rozstrzyga, że tenancy rozwiązywana jest **na granicy instancji** (`tenant_id` wyłącznie na `monitored_instance`), a **nie** przez roszczenia w JWT. Te pola nie zostaną wykorzystane w planowanej architekturze — dodanie roszczenia do tokenu w przyszłości, jeśli będzie potrzebne, jest trywialne. Martwe pola w warstwie auth zostawiać nie warto.

**Pozycja 5** blokuje pracę: pierwsze migracje domenowe pisze się właśnie teraz, a `README.md` w tym katalogu wprowadza w błąd co do konwencji i stanu.

## Poza zakresem

`backend/app/core/csrf.py:26-29` — fallback na nieistniejący `app.modules.billing.constants` jest **świadomy i przetestowany**. Zostawić, ewentualnie dopisać komentarz wyjaśniający, że domena billing nie istnieje w PulseDB.
