# Dokumentacja PulseDB

Ten katalog zawiera dokumentację robocza projektu PulseDB — patrz też [README.md](../README.md) (wizja, model biznesowy, roadmapa wysokopoziomowa).

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
