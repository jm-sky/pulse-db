# Idera SQL Diagnostic Manager · dbWatch Control Center

**Data:** 2026-07-30 · **Kategoria:** konkurencja bezpośrednia (segment A), drugi szereg

> Plik dodany poza szkielet zadany w zleceniu — oba produkty były wymienione do analizy, a nie miały przypisanego pliku.
> **Uwaga o jakości danych:** oba produkty publikują wyraźnie mniej informacji technicznych niż DPA i Redgate. Znaczna część poniższych ustaleń pochodzi z agregatorów recenzji, nie od producentów — oznaczone 🟡.

---

## 1. Idera SQL Diagnostic Manager (SQLdm)

### Pozycja
Weteran rynku SQL Server (rodowód sprzed 2010), sprzedawany głównie do organizacji, które już mają inne produkty Idery (SQL Safe, SQL Secure, SQL Compliance Manager). Typowy klient to średnia/duża firma z estate SQL Server i procesem zakupowym opartym na relacji z vendorem.

### Funkcje 🟡
- Monitoring w czasie rzeczywistym + historia; wsparcie on-prem, chmura, hybryda
- Wait statistics, analiza zapytań, plany wykonania
- Rozbudowane alertowanie z predykcją
- Query Monitor / analiza blokad i deadlocków
- Osobne produkty dla MySQL i innych silników (SQL Diagnostic Manager for MySQL) — **to nie jest jeden produkt wielosilnikowy, tylko rodzina osobnych narzędzi**
- Wersja mobilna/webowa konsoli

### Architektura 🟡
- Windows-centryczna: usługa kolektora + repozytorium na SQL Server + konsola desktopowa (+ web)
- Agentless względem monitorowanej instancji

### Model biznesowy
- Wyłącznie komercyjny, per instancja, **cena nieujawniana publicznie** ✅ (to jest potwierdzony fakt: producent nie publikuje cennika, dostępny jest tylko trial i kontakt handlowy)
- Kilka edycji (m.in. Pro), maintenance roczny

### Słabości wykorzystywalne przez PulseDB
| Słabość | Komentarz |
|---------|-----------|
| Brak przejrzystości cenowej | Każdy zakup wymaga rozmowy handlowej |
| Rozbicie na osobne produkty per silnik | Estate mieszany = kilka licencji i kilka konsol |
| Postrzegany jako produkt „legacy" 🟡 | Powtarzający się motyw w recenzjach: przestarzały interfejs, ciężka konsola |
| Windows-only | Brak ścieżki dla zespołów linuksowych |
| Brak API-first, brak MCP | ❌ |

---

## 2. dbWatch Control Center

### Pozycja
Nisza **database operations**, nie database performance analysis. Punktem ciężkości jest zarządzanie flotą i automatyzacja zadań administracyjnych, a nie diagnostyka pojedynczego zapytania. Silna obecność w Skandynawii.

### Funkcje 🟡
- Monitoring wielu silników z jednej konsoli: SQL Server, Oracle, PostgreSQL, MySQL, Sybase
- **Automatyzacja zadań** (maintenance jobs, backupy, reindeksacja) — to jest ich wyróżnik
- Dashboardy floty, raporty, alerty
- Analiza wydajności obecna, ale płytsza niż w DPA

### Architektura 🟡
- Java, model klient–serwer, agenty lub połączenia bezpośrednie
- Wsparcie wielu systemów operacyjnych

### Model biznesowy
- Komercyjny, od ~550–588 USD/rok 🟡 — **najtańszy z analizowanych produktów komercyjnych**
- Dostępny trial

### Znaczenie dla PulseDB — ważne rozróżnienie

dbWatch pokazuje, że **„wielosilnikowość" i „głęboka diagnostyka" to w praktyce trade-off**. Produkt obsługujący pięć silników robi to na najmniejszym wspólnym mianowniku: uptime, przestrzeń dyskowa, backupy, podstawowe metryki.

To jest bezpośrednie ostrzeżenie dla PulseDB: **plan „PostgreSQL + SQL Server, a potem MySQL, Oracle i inne przez adaptery" prowadzi wprost do pozycji dbWatch** — narzędzia szerokiego i płytkiego, z którego DBA korzysta do przeglądu floty, ale przy realnym problemie sięga po co innego.

**Wniosek:** PulseDB musi zdecydować, czy jest głęboki dla dwóch silników, czy płytki dla pięciu. Nie ma trzeciej opcji przy zasobach jednoosobowego zespołu. Rekomendacja w [opportunities.md](opportunities.md) §7.

---

## 3. Wspólne wnioski

1. **Drugi szereg segmentu A nie jest zagrożeniem konkurencyjnym dla PulseDB, ale jest źródłem klientów.** Użytkownicy niezadowoleni z „legacy" narzędzi Idery to naturalny target.
2. **Brak publicznych cenników w całym drugim szeregu** wzmacnia argument transparentności PulseDB.
3. **dbWatch jest ostrzeżeniem przed rozmyciem zakresu**, nie wzorem do naśladowania.
4. Żaden z nich nie ma API-first ani MCP — cała konkurencja komercyjna w segmencie A jest tu pusta.
