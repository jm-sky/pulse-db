# FAQ licencyjne (AGPLv3)

**Data:** 2026-07-30 · **Status:** `verification needed`
**Kontekst:** [vision.md](vision.md) §6 · [roadmap.md](roadmap.md) §3 (Faza 0, element 2)

> To nie jest porada prawna. To krótkie, jednoznaczne wyjaśnienie praktycznych
> konsekwencji AGPLv3 dla najczęstszego scenariusza użycia PulseDB — self-hosted,
> wewnętrzne narzędzie diagnostyczne. Przy wątpliwościach w konkretnym
> przypadku skonsultuj się z działem prawnym.

## W skrócie

**Używanie PulseDB wewnątrz własnej organizacji — nawet zmodyfikowanego —
nie rodzi żadnego obowiązku publikacji kodu.** Klauzula sieciowa AGPLv3
uruchamia się dopiero, gdy **osoby spoza Twojej organizacji** wchodzą w
interakcję z (Twoją, ewentualnie zmodyfikowaną) instancją przez sieć.

## Pytania

### Instalujemy PulseDB na własnym serwerze i używa go nasz zespół DBA. Czy musimy coś publikować?

Nie. To jest dokładnie przypadek, dla którego AGPLv3 nie różni się w praktyce
od MIT/Apache: kod działa u Ciebie, dla Ciebie, obsługiwany przez Twoich
pracowników. Nikt zewnętrzny nie "korzysta z usługi przez sieć" w rozumieniu
klauzuli AGPL §13.

### Zmodyfikowaliśmy kod PulseDB pod swoje potrzeby (np. własny typ alertu). Czy to coś zmienia?

Nie, dopóki modyfikacja zostaje wewnątrz organizacji. AGPL §13 mówi o
**udostępnianiu zmodyfikowanej wersji użytkownikom przez sieć** — jeśli
jedynymi "użytkownikami przez sieć" są Twoi pracownicy logujący się do
wewnętrznego narzędzia, obowiązek publikacji się nie aktywuje.

### Jesteśmy MSP/integratorem i chcemy hostować PulseDB dla naszych klientów, żeby monitorowali swoje bazy przez nasz panel.

Tu klauzula sieciowa **prawdopodobnie się aktywuje** — klienci są
"użytkownikami przez sieć" spoza Twojej organizacji, korzystającymi z
(ewentualnie zmodyfikowanej) instancji. Jeśli modyfikujesz kod, musisz
udostępnić im (użytkownikom tej instancji) źródło zmodyfikowanej wersji.
Jeśli **nie modyfikujesz** kodu (uruchamiasz PulseDB "as-is" z tego repo),
obowiązek dostępu do źródła jest spełniony samym faktem, że kod jest
publiczny na tej licencji — i tak nie musisz nic dodatkowo publikować.
To jest scenariusz, w którym warto się skonsultować z prawnikiem przed
uruchomieniem produkcyjnym.

### Czy możemy sprzedawać wsparcie/wdrożenia PulseDB, nie łamiąc licencji?

Tak — AGPLv3 nie zabrania sprzedaży usług (wsparcia, wdrożenia, hostingu dla
klienta na jego infrastrukturze). To jest zresztą przewidywany kierunek
monetyzacji projektu (§6 vision, wzorem Percona/Darling).

### Czy CLI / SDK / definicja serwera MCP mają tę samą licencję co rdzeń?

**Dziś: tak, całe repo jest na AGPLv3** — jedna licencja, jeden `LICENSE` w
korzeniu. **Rozdzielenie integracji (CLI/SDK/MCP) na licencję permisywną
(MIT/Apache), wzorem Grafany, jest rozważane, ale nierozstrzygnięte** ❓ —
patrz [vision.md](vision.md) §6 "Liberalna licencja dla integracji — do ADR".
Nie zakładaj podziału, dopóki ten ADR nie zostanie zamknięty i `LICENSE` się
nie zmieni.

### Nasza firma ma politykę zakazującą AGPL. Co teraz?

To świadomie przyjęte ryzyko projektu (§6 vision) — AGPL wycina fragment
segmentu enterprise self-hosted z restrykcyjnymi politykami licencyjnymi.
Alternatywy: (a) poczekać na ewentualny split licencyjny integracji, jeśli
Twój przypadek dotyczy tylko klienta/CLI/MCP, nie rdzenia; (b) rozmowa z
własnym działem prawnym o wyjątku dla wewnętrznego self-hostingu (najczęstszy
powód polityk anty-AGPL — obawa przed obowiązkiem publikacji przy dystrybucji
zewnętrznej — nie dotyczy czystego użycia wewnętrznego, patrz pytanie pierwsze
wyżej).

## Powiązane

- [LICENSE](../LICENSE) — pełny tekst AGPLv3
- [vision.md](vision.md) §6 — decyzja licencyjna i uzasadnienie
- [roadmap.md](roadmap.md) §3 (Faza 0, element 2)
