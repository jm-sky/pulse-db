# Dokumentacja PulseDB

Ten katalog zawiera dokumentację robocza projektu PulseDB — patrz też [README.md](../README.md) (wizja, model biznesowy, roadmapa wysokopoziomowa).

## Dokumenty produktowe

| Plik | Przeznaczenie | Status |
|------|---------------|--------|
| [vision.md](./vision.md) | Pozycjonowanie, ICP, zasady produktu, non-goals, licencja, kill criteria | `verification needed` |
| [roadmap.md](./roadmap.md) | Fazy 0a–4, kryteria wyjścia, harmonogram, reguła cięcia | `verification needed` |
| `prd.md` | Persony, JTBD, wymagania funkcjonalne, kryteria akceptacji | *do napisania (Faza 0a)* |
| [grants.md](./grants.md) | Minimalne uprawnienia konta kolektora per silnik (PostgreSQL/SQL Server) | `verification needed` |
| [licensing-faq.md](./licensing-faq.md) | FAQ licencyjne AGPLv3 — użycie wewnętrzne vs klauzula sieciowa | `verification needed` |

Te dokumenty są **nadrzędne** wobec `plans/` — plan sprzeczny z `vision.md` wymaga najpierw zmiany wizji.

## ADR — decyzje architektoniczne

Trzymane na razie w [`research/`](./research/README.md), bo katalog jest przeznaczony na analizy przed decyzją:

| ADR | Rozstrzyga | Status |
|-----|------------|--------|
| [2026-07-30-data-model.md](./research/2026-07-30-data-model.md) | Model danych repozytorium — PostgreSQL 17 z partycjonowaniem, wymiary/fakty, rollupy, retencja, szew tenancy | `verification needed` |
| [2026-07-30-chart-library.md](./research/2026-07-30-chart-library.md) | Biblioteka wykresów Web UI — rekomendacja **warunkowa**, rozstrzyga spike w Fazie 0a | `verification needed` |

Przy trzecim ADR warto wydzielić `docs/adr/` z własnym indeksem.

## Workflow (issues, reviews, research, plans)

| Katalog | Przeznaczenie |
|---------|---------------|
| [issues/](./issues/README.md) | Błędy, usprawnienia, dług techniczny |
| [reviews/](./reviews/README.md) | Sesje przeglądu (security, code quality, UX, performance) |
| [research/](./research/README.md) | Analizy, spike'i, porównania przed decyzją |
| [plans/](./plans/README.md) | Plany implementacji większych zmian |

Statusy: `todo` · `planned` · `in progress` · `done` · `verification needed`

**Nie używamy** GitHub Issues do śledzenia tych elementów — tylko pliki w `docs/`.

## Konwencja nazw plików

**Tylko `docs/issues/`** używa numeru ID w nazwie pliku:

```
YYYY-MM-DD--NNN--kebab-tytul.md
```

Pozostałe katalogi (`reviews/`, `research/`, `plans/`) — sama data + slug:

```
YYYY-MM-DD-kebab-tytul.md
```

Każdy katalog ma `README.md` jako indeks (tabela wszystkich plików + legenda statusów).

---

**Ostatnia aktualizacja:** 2026-07-30
