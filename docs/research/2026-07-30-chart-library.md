# ADR: wybór biblioteki wykresów dla Web UI PulseDB

**Data:** 2026-07-30 · **Status:** verification needed
**Kontekst:** [vision.md](../vision.md) §3.7, §4, §5, §6, §7.2b · [research/competitors/solarwinds-dpa.md](competitors/solarwinds-dpa.md) §4, §8
**Legenda pewności:** ✅ potwierdzone źródłem (link) · 🟡 założenie/estymacja · ❓ otwarte, nie da się potwierdzić bez własnego spike'u

---

## 1. Kontekst i wymagania

Główny ekran produktu — **Waits** (§5 vision.md) — to **stacked bar chart czasu oczekiwania wg typu wait na osi czasu, klikalny w dół**, wzorowany wprost na SolarWinds DPA ([solarwinds-dpa.md](competitors/solarwinds-dpa.md) §4, §8.1). Vision.md nazywa ten widok **nietykalnym** (§7.2b): *„bez niego nie jesteśmy alternatywą dla DPA, tylko innym rodzajem narzędzia"*. Ta biblioteka jest więc wyborem o najwyższej stawce w warstwie frontendu — błąd tutaj nie jest naprawialny przez odłożenie funkcji, bo funkcja jest rdzeniem pozycjonowania.

**Twarde wymagania:**

1. **Vue 3** + Vite + Tailwind CSS 4, spójne z shadcn-vue / reka-ui (`components.json` ✅: style `new-york`, `reka-ui` jako baza).
2. **Licencja kompatybilna z redystrybucją w AGPLv3** — kryterium odrzucające, nie preferencja.
3. Interakcje: klik w segment słupka → drill-in, brush/zoom po osi czasu, wybór okna czasowego, tooltip wieloseryjny, **synchronizacja kursora między wykresami** (bo wzorzec DPA to `wykres → dzień → godzina → zapytanie`, §3.7 vision.md — kilka wykresów muszą reagować na ten sam kursor/okno).
4. Wydajność: dane z samplingu 1 s zagregowane do rollupów 1 min / 1 h (§4 vision.md) — realistyczny wykres to **tysiące punktów × kilkadziesiąt serii** (typy wait) bez zamarzania UI.
5. Tryb jasny/ciemny spójny z tokenami Tailwind.
6. Rozmiar bundle'a i możliwość importu selektywnego (tree-shaking).
7. Dostępność (klawiatura, czytniki ekranu) — w granicach realnych dla kategorii wykresów.
8. **Koszt utrzymania przy jednej osobie** (§7.2 vision.md: kapacja = 1 FTE) — aktywność projektu, jakość dokumentacji, dojrzałość integracji z Vue 3, bus factor.

**Fakt istotny dla tego ADR:** `package.json` już zawiera `@unovis/ts` i `@unovis/vue` (`^1.6.5`) ✅ — odziedziczone z boilerplate'u „family" ([2026-07-30-boilerplate-from-family.md](../plans/2026-07-30-boilerplate-from-family.md)), **nie jest to świadoma decyzja pod wymagania PulseDB**. Vision.md §3.7 wprost nazywa bibliotekę wykresów pozycją „do rozstrzygnięcia", a §9 — otwartą decyzją do ADR. Traktuję unovis jako jednego z kandydatów, nie jako fakt dokonany, ale odnotowuję, że koszt krańcowy jego użycia jest dziś zerowy (już w `package.json`, zero dodatkowej zależności), podczas gdy każdy inny wybór dokłada nową zależność.

---

## 2. Kandydaci odrzuceni na licencji

| Kandydat | Licencja | Werdykt | Źródło |
|---|---|---|---|
| **Highcharts** | Proprietary EULA. „Highcharts' license model is not compatible with any open source license like Apache 2 or any GPL." Darmowe wyłącznie dla użytku niekomercyjnego/edukacyjnego; użytek wewnętrzny w firmie (prototypowanie, R&D, narzędzia wewnętrzne) wymaga płatnej licencji komercyjnej od stycznia 2026 | ❌ **odrzucone** — wprost niekompatybilne z dystrybucją OSS | ✅ [highcharts.com/blog — EULA update 2026](https://www.highcharts.com/blog/news/our-new-eula-makes-free-usage-clearer/), [shop.highcharts.com/license](https://shop.highcharts.com/license) |
| **AG Charts Enterprise** | Community (`ag-charts-community`) jest MIT ✅, ale **zoom, synchronizacja (cursor sync) i navigator — czyli dokładnie wymagania #3 tego ADR — są funkcjami Enterprise**, płatnymi: od 499 USD/dewelopera/rok, licencja proprietary | ❌ **odrzucone funkcjonalnie** — Community nie pokrywa twardych wymagań, Enterprise wymaga płatnej licencji na redystrybucję | ✅ [ag-grid.com/charts/community-vs-enterprise](https://www.ag-grid.com/charts/javascript/community-vs-enterprise/), [ag-grid.com/charts/license-pricing](https://www.ag-grid.com/charts/license-pricing/) |

Reszta zbadanych bibliotek ma licencje permisywne kompatybilne z AGPLv3 (redystrybucja w produkcie OSS nie wymaga opłaty ani licencji komercyjnej) — patrz §3.

---

## 3. Macierz porównawcza realnych kandydatów

Wszystkie poniżej mają licencję kompatybilną z AGPLv3.

| Kryterium | **Apache ECharts** | **unovis** (`@unovis/vue`) | **Chart.js** + `chartjs-plugin-zoom` | **uPlot** | **D3** (własna implementacja) |
|---|---|---|---|---|---|
| Licencja | Apache-2.0 ✅ [LICENSE](https://github.com/apache/echarts/blob/master/LICENSE) | Apache-2.0 ✅ [LICENSE](https://github.com/f5/unovis/blob/main/LICENSE) | MIT ✅ [LICENSE](https://github.com/chartjs/Chart.js/blob/HEAD/LICENSE.md) + MIT (plugin) ✅ | MIT ✅ [LICENSE](https://github.com/leeoniya/uPlot/blob/master/LICENSE) | ISC ✅ [d3/d3 package.json](https://github.com/d3/d3/blob/main/package.json) |
| Rozmiar (min / gzip) | Pełny pakiet: 1,11 MB / **368 KB** gzip ✅ [bundlephobia](https://bundlephobia.com/package/echarts). Custom build (`echarts/core` + tylko potrzebne moduły) znacząco mniejszy — mechanizm tree-shakingu udokumentowany ✅ [echarts.apache.org/handbook — Import](https://echarts.apache.org/handbook/en/basics/import), ale konkretna liczba dla kombinacji bar+dataZoom+tooltip+canvas nie jest podana w dokumentacji — 🟡 szacunek własny: rząd wielkości 60–100 KB gzip, wymaga zmierzenia | `@unovis/ts` (main chunk) **186,8 KB** gzip + `@unovis/vue` **6 KB** gzip ✅ [bundlephobia ts](https://bundlephobia.com/package/@unovis/ts) [bundlephobia vue](https://bundlephobia.com/package/@unovis/vue). Paczka jest podzielona na chunki (widoczne w danych bundlephobia), co sugeruje częściowy code-splitting, ale rozmiar samego importu `StackedBar` w izolacji nie jest potwierdzony ❓ | Core: 200 KB / **68,4 KB** gzip ✅ [bundlephobia](https://bundlephobia.com/package/chart.js). Plugin zoom dokłada się osobno, rozmiar niezmierzony 🟡 | **50,8 KB** / **21,9 KB** gzip ✅ [bundlephobia](https://bundlephobia.com/package/uplot) — najmniejszy z kandydatów | Pełny pakiet 279 KB / **92 KB** gzip ✅ [bundlephobia](https://bundlephobia.com/package/d3), w praktyce importuje się tylko potrzebne moduły (d3-scale, d3-shape…), realny koszt niższy 🟡 |
| Stacked bar + drill-in | Natywny typ `bar` ze `stack`, `click` event z pełnym kontekstem serii/punktu ✅ | Natywny, dedykowany komponent `StackedBar` w `XYContainer` ✅ [unovis.dev/docs/xy-charts/StackedBar](https://unovis.dev/docs/xy-charts/StackedBar/) | Natywny stacked bar + `onClick` z indeksem datasetu/punktu ✅ | **Brak wbudowanego typu stacked bar** — trzeba zbudować własny renderer na prymitywach canvas ❌ dla tego wymagania | Trzeba zbudować od zera (skale, layout stack, hit-testing) ❌ jako gotowe, ✅ jako możliwość |
| Brush / zoom po osi czasu | Natywny komponent `dataZoom` (slider + inside/scroll) i `brush` ✅ [echarts.apache.org/feature](https://echarts.apache.org/en/feature.html) | Natywny komponent `Brush` wewnątrz `XYContainer` ✅ [unovis.dev/docs/auxiliary/Brush](https://unovis.dev/docs/auxiliary/Brush/); zoom kołem myszy nie jest jednoznacznie udokumentowany ❓ | Tylko przez zewnętrzny plugin `chartjs-plugin-zoom` (MIT) ✅ [github.com/chartjs/chartjs-plugin-zoom](https://github.com/chartjs/chartjs-plugin-zoom) — nie w rdzeniu | Wbudowany, to jest mocna strona uPlot (zaprojektowany pod duże serie czasowe) ✅ | Trzeba zbudować własny brush (d3-brush) i logikę zoom ✅ jako biblioteka pomocnicza, ale cała integracja własna |
| Tooltip wieloseryjny | Natywny `tooltip.trigger: 'axis'` z listą serii ✅ | Komponent `Tooltip`, działa w `XYContainer` i standalone ✅ [unovis.dev/docs/auxiliary/Tooltip](https://unovis.dev/docs/auxiliary/Tooltip/) | Natywny `interaction.mode: 'index'` ✅ | Wymaga własnej implementacji przez `cursor` API — nie ma gotowego bogatego tooltipu z automatycznym stylowaniem 🟡 | Własna implementacja od zera |
| Synchronizacja kursora między wykresami | Natywny mechanizm `echarts.connect()` — łączy `dataZoom`, `tooltip`, `axisPointer` między instancjami; wzorzec używany też w integracjach Grafana+ECharts ✅ [przykład CodePen](https://codepen.io/sjcobb/pen/zYRVpGK), [community.grafana.com](https://community.grafana.com/t/apache-echarts-syncing-datazoom-sliders/139468) | Komponent `Crosshair` + współdzielony `Tooltip` — ale **brak w dokumentacji jawnego mechanizmu łączenia niezależnych `XYContainer` między sobą** (odpowiednika `echarts.connect()`) ❓ | Brak wbudowanego mechanizmu, wymaga własnego kodu synchronizującego zdarzenia hover między instancjami ❓/🟡 | Wbudowany `cursor.sync` — bardzo dobre wsparcie, to jedna z flagowych funkcji uPlot ✅ | Własna implementacja (współdzielony event bus) |
| Wydajność (tys. punktów × kilkadziesiąt serii) | Canvas renderer + progressive rendering, sprawdzone w produkcji przy dużych zbiorach — powszechna praktyka branżowa, brak własnego benchmarku w tym repo ❓ | Brak niezależnych benchmarków dla tej konkretnej skali w dokumentacji ❓ | Canvas-based, dobra do umiarkowanych zbiorów; przy dziesiątkach serii × tysiącach punktów bywa zgłaszane jako wolniejsze niż ECharts/uPlot w dyskusjach community 🟡 | Zaprojektowany specjalnie pod wysoką gęstość punktów czasowych — najszybszy z kandydatów wg opisu autora („40 KB, brak WebGL/WASM, a mimo to szybszy") ✅ [github.com/leeoniya/uPlot](https://github.com/leeoniya/uPlot) | Zależy w 100% od jakości własnej implementacji |
| Theme jasny/ciemny (Tailwind) | Przekazywanie tokenów kolorów przez konfigurację serii/theme API — standardowe, ręczne 🟡 | Kolory jako propsy komponentów Vue — łatwa integracja z systemem tokenów 🟡 | Proste, ręczne przekazanie kolorów w opcjach ✅ | Pełna kontrola stylów, minimalne API ✅ | Pełna kontrola, zero narzutu na integrację |
| Dostępność | Auto-generowany `aria-label` po włączeniu `AriaComponent` ✅ [echarts.apache.org/handbook — ARIA](https://echarts.apache.org/handbook/en/best-practices/aria/), ale **potwierdzony otwarty bug**: „ECharts claims to be accessible, but is not keyboard accessible" ✅ [github.com/apache/echarts/issues/18585](https://github.com/apache/echarts/issues/18585) | Brak wzmianek o wsparciu ARIA w dokumentacji ❓ | Brak wbudowanego wsparcia ARIA, pluginy community niepełne ❓ | Minimalistyczna biblioteka, brak wsparcia ARIA/klawiatury z założenia ❓ | Zależy w 100% od własnej implementacji |
| Integracja z Vue 3 | Przez oficjalny community wrapper `vue-echarts` (MIT, ekosystem `ecomfe`, ten sam zespół co dokumentacja ECharts) ✅ [github.com/ecomfe/vue-echarts](https://github.com/ecomfe/vue-echarts) — **1,4 mln pobrań/mies.** ✅ [npm downloads API](https://api.npmjs.org/downloads/point/last-month/vue-echarts) — lub bezpośrednio `echarts.init(dom)` bez wrappera | **Natywne komponenty Vue** (`@unovis/vue`) — nie wrapper nad biblioteką React-first, tylko framework-agnostic core (`@unovis/ts`) z natywnymi bindingami do Vue, React, Angular, Svelte, Solid ✅ [github.com/f5/unovis](https://github.com/f5/unovis) — najlepsza architektura integracji z Vue 3 spośród kandydatów | Przez wrapper `vue-chartjs` (MIT), dojrzały, prosty ✅ | Brak oficjalnego wrappera Vue, wymaga własnego cienkiego adaptera (niski koszt, ale koszt) 🟡 | Brak, w pełni własna integracja |
| Aktywność / utrzymanie | **66,9k★, 19,8k forków** ✅ [github.com/apache/echarts](https://github.com/apache/echarts), top-level projekt Apache Software Foundation, **17 mln pobrań/mies.** ✅ [npm downloads API](https://api.npmjs.org/downloads/point/last-month/echarts) | **2,8k★, 66 forków, 73 kontrybutorów** ✅ [github.com/f5/unovis](https://github.com/f5/unovis), **647k pobrań/mies.** (`@unovis/vue`) ✅ [npm downloads API](https://api.npmjs.org/downloads/point/last-month/@unovis/vue) — silnik wizualizacji **F5 Distributed Cloud** (produkt sieciowy/observability F5) ✅ [community.f5.com](https://community.f5.com/kb/technicalarticles/announcing-unovis-1-5/339532), pojedynczy sponsor korporacyjny | Bardzo duża popularność ogólna biblioteki, ale funkcje kluczowe dla Waits (zoom) żyją w osobnym, mniejszym repo (dodatkowy punkt utrzymania i ryzyka) | Mały, ale aktywny — jeden główny maintainer (`leeoniya`), bus factor 1 🟡 | Ogromna społeczność, ale koszt utrzymania przenosi się w całości na własny kod produktu |

**Kandydaci rozważeni i odłożeni bez pełnej analizy w tabeli** (licencja OK, ale odpadają na kształt narzędzia lub rozmiar zanim dotarli do szczegółowej oceny):

- **Plotly.js** — MIT ✅ [LICENSE](https://github.com/plotly/plotly.js/blob/master/LICENSE), ale pełny bundle **4,65 MB / 1,39 MB gzip** ✅ [bundlephobia](https://bundlephobia.com/package/plotly.js) — nawet wariant „basic dist" jest rzędu kilkuset KB gzip; nieproporcjonalne do potrzeb jednego typu wykresu.
- **Vega-Lite** (BSD-3-Clause ✅) i **Observable Plot** (ISC ✅) — gramatyki deklaratywne zorientowane na eksplorację danych/raporty, nie na precyzyjnie zaprojektowaną, wysoce interaktywną produkcyjną konsolę z synchronizacją kursora między wieloma niezależnymi widgetami. Dopasowanie do wymagania #3 wymagałoby budowania własnej warstwy interakcji ponad gramatyką — podobny koszt inżynierski co D3, bez korzyści niskopoziomowej kontroli D3.

---

## 4. Rekomendacja

> **Apache ECharts, przez oficjalny wrapper `vue-echarts`, z importem selektywnym (`echarts/core` + tylko potrzebne moduły).**

**Licencja:** Apache-2.0 ✅ — bez zastrzeżeń wobec AGPLv3.

**Uzasadnienie (perspektywa: co się stanie, gdy utknę sam z tym wyborem za 6 miesięcy):**

1. **Interakcje z wymagania #3 są natywne, nie dobudowane.** `dataZoom` (brush/zoom), `tooltip.trigger: 'axis'` (wieloseryjny) i przede wszystkim `echarts.connect()` (synchronizacja kursora/zoomu między niezależnymi instancjami wykresów) to udokumentowane, pierwszoklasowe mechanizmy ECharts — dokładnie te, których wymaga łańcuch „wykres → okno czasu → wait → sesja → zapytanie" z §3.7 vision.md. To jedyny kandydat, u którego wszystkie cztery interakcje mają wprost potwierdzone wsparcie, bez znaków zapytania.
2. **Margines bezpieczeństwa utrzymaniowego jest nieproporcjonalnie większy.** 66,9k gwiazdek i 17 mln pobrań/mies. (✅ npm registry) vs 2,8k gwiazdek / 647k pobrań/mies. dla najbliższej alternatywy. Projekt jest top-level projektem Apache Software Foundation, nie zależy od jednej firmy. Przy kapacji jednej osoby (§7.2 vision.md) prawdopodobieństwo, że odpowiedź na trudny problem integracyjny już istnieje w Stack Overflow / issue trackerze / dokumentacji, jest krytycznym czynnikiem redukcji ryzyka — większym niż wygoda posiadania biblioteki już w `package.json`.
3. **Dostępność jest realnie lepsza niż u alternatyw**, mimo potwierdzonego ograniczenia (patrz ryzyka). ECharts ma udokumentowany, włączany mechanizm ARIA generujący opisy wykresów — żaden inny kandydat w matrycy nie ma nawet tego.
4. **Tree-shaking jest udokumentowanym, wspieranym wzorcem** (`echarts/core` + `echarts.use([...])`), więc rozmiar bundle'a jest kontrolowalny, choć dokładna liczba dla naszego zestawu modułów wymaga zmierzenia (patrz ryzyka).
5. **Jedna biblioteka wystarczy — podział nie jest uzasadniony.** Rozważyłem wariant „lekka biblioteka do sparkline'ów (np. uPlot) + ECharts do głównego widoku". uPlot jest szybszy i mniejszy dla samych sparkline'ów, ale przy kapacji jednej osoby (§7.2) koszt utrzymania **dwóch** zależności wykresowych — dwóch API, dwóch systemów theme'owania, dwóch ścieżek integracji z Vue — przewyższa korzyść z paru KB gzip zaoszczędzonych na kaflach Overview. Custom build ECharts (`BarChart`/`LineChart` + `CanvasRenderer`, bez `dataZoom`) dla małych multiples na ekranie Overview jest wystarczająco lekki po tree-shakingu, by nie uzasadniać drugiej zależności. Jeśli w praktyce po zmierzeniu bundle'a (ryzyko poniżej) okaże się to nieprawdą, uPlot jest jedynym kandydatem wartym rewizji tej decyzji dla samych sparkline'ów — nie dla głównego widoku.

---

## 5. Odrzucona alternatywa: unovis

**unovis** jest najbliższym konkurentem i jedynym kandydatem, który dziś nie kosztowałby ani jednego nowego wpisu w `package.json` — jest już zainstalowany (`@unovis/ts`, `@unovis/vue` ^1.6.5), ma natywne komponenty Vue 3 (lepsza architektura integracji niż wrapper `vue-echarts`), ma dedykowany komponent `StackedBar` i jest sprawdzony w produkcji jako silnik wizualizacji **F5 Distributed Cloud** — czyli w domenie zbliżonej do PulseDB (observability infrastruktury sieciowej). To poważny kandydat, nie słomiany.

**Dlaczego mimo to odrzucony na rzecz ECharts:**

- **Brak potwierdzonego mechanizmu synchronizacji kursora między niezależnymi `XYContainer`** — dokumentacja opisuje `Crosshair` i `Tooltip` w obrębie jednego kontenera, ale nie znalazłem odpowiednika `echarts.connect()` do łączenia oddzielnych instancji wykresów (wymaganie #3, kluczowe dla wzorca „wykres → dzień → godzina → zapytanie"). To ❓, nie ✅ — a decyzja o głównym, nietykalnym ekranie produktu (§7.2b vision.md) nie powinna stać na otwartym pytaniu.
- **Brak potwierdzonego wsparcia dostępności** (ARIA) w dokumentacji — kontrastuje z jawnie udokumentowanym (choć niedoskonałym) mechanizmem w ECharts.
- **Ekosystem 25× mniejszy** (2,8k★ / 647k pobrań-mies. vs 66,9k★ / 17 mln pobrań-mies.) i **pojedynczy sponsor korporacyjny** (F5) zamiast fundacji. Przy jednoosobowym zespole ryzyko „utknąłem i nikt tego nie rozwiązał" jest realnym kosztem, nie abstrakcją — mniejsza społeczność oznacza mniej odpowiedzi na trudne pytania i wolniejsze wsparcie przy niszowych bugach.
- Zaoszczędzone ~180 KB gzip (bo unovis już jest w `package.json`, a ECharts + vue-echarts to nowa zależność) jest realną korzyścią, ale **nie na tyle dużą, by przeważyć niepewność wokół wymagania #3** — to jest dokładnie ta funkcja, bez której cały ekran traci sens (§7.2b: *„bez niego nie jesteśmy alternatywą dla DPA"*).

**Werdykt:** jeśli spike (patrz ryzyka niżej) wykaże, że unovis jednak obsługuje cross-container sync w sposób nieudokumentowany wprost (np. przez współdzielony reaktywny stan Vue), warto go zrewidować dla ekranów pobocznych (Overview, Instance detail) — ale nie dla Waits, gdzie ryzyko nieudanego założenia jest nie do zaakceptowania przy jednej osobie w zespole.

---

## 6. Ryzyka wyboru

| Ryzyko | Waga | Mitygacja |
|---|---|---|
| Dokładny rozmiar tree-shaken buildu ECharts (bar + dataZoom + tooltip + canvas) nie jest zmierzony — 🟡 szacunek 60–100 KB gzip, nie potwierdzony | średnie | Pierwszy task po tym ADR: spike z realnym importem selektywnym + pomiar (`rollup-plugin-visualizer` / `vite-bundle-visualizer`), zanim powstanie drugi ekran |
| Potwierdzony bug: ECharts nie jest w pełni dostępny z klawiatury ([issue #18585](https://github.com/apache/echarts/issues/18585)) | średnie — koliduje z wymaganiem #7 | Zaplanować dodatkową ścieżkę dostępności: tabela danych jako alternatywa dla wykresu (spójne też z „braku ślepego zaułka" §3.7 — każdy wykres i tak musi mieć dojście do surowych danych) |
| Wydajność przy realnej skali (kilkadziesiąt typów wait × tygodnie rollupów 1 min) nie jest zmierzona w tym repo — ❓ oparta na reputacji branżowej, nie na benchmarku własnym | wysokie | Spike wydajnościowy z syntetycznymi danymi przed dopracowaniem ekranu Waits — nie po |
| `@unovis/ts` / `@unovis/vue` zostają w `package.json` jako martwa zależność odziedziczona z boilerplate'u, jeśli nikt ich nie usunie | niskie | Do decyzji przy pierwszym PR dotykającym wykresów: usunąć albo świadomie zostawić z komentarzem uzasadniającym (np. do przyszłej rewizji dla ekranów pobocznych z §5) |
| ECharts ma szeroki zakres (mapy, 3D, wykresy finansowe) — pokusa użycia „bo już jest" poza zakresem MVP | niskie, ale realne przy presji czasu | Restrykcja code-review: import tylko modułów bar/line/tooltip/dataZoom/aria; każdy nowy moduł wymaga uzasadnienia w PR |
| `vue-echarts` to community wrapper (`ecomfe`), nie oficjalny projekt Apache ECharts — teoretyczne ryzyko rozjazdu wersji | niskie | Duża popularność (1,4 mln pobrań/mies.) i długa historia sugerują niskie ryzyko w praktyce; alternatywnie można pominąć wrapper i wołać `echarts.init()` bezpośrednio w `onMounted`/`onUnmounted`, co eliminuje tę zależność kosztem nieco więcej kodu integracyjnego |
| Theme jasny/ciemny wymaga ręcznego mapowania tokenów Tailwind na opcje serii ECharts — brak gotowej integracji | niskie | Standardowy wzorzec: `computed` na motyw z Tailwind CSS variables, przekazywany do `option` przy każdej zmianie theme |

**Największe pojedyncze ryzyko wyboru:** brak własnego pomiaru wydajności przy docelowej skali (dziesiątki serii wait × tysiące punktów rollupów) — cała rekomendacja opiera się na reputacji ECharts z innych wdrożeń branżowych, nie na teście w tym repo, a to jest dokładnie ten wymiar, w którym nietykalny ekran Waits nie może zawieść.

---

## 7. Uwaga recenzenta (2026-07-30) — rekomendacja **warunkowa**, nie zamknięta

ADR jest dobrze udokumentowany i rekomendacja jest obronna, ale dwie rzeczy wymagają korekty przed przyjęciem.

### 7.1 Koszt zmiany jest zaniżony ✅ zweryfikowane w repo

ADR opisuje unovis jako „wpis w `package.json`" i wycenia korzyść na ~180 KB gzip. W repozytorium istnieje jednak **działająca warstwa integracyjna**:

- `src/components/ui/chart/index.ts` — lazy-loaded `VisCrosshair` i `VisTooltip` z `@unovis/vue` ✅
- `src/components/ui/chart/ChartStyle.vue` — generowanie zmiennych CSS (`--color-<key>`) z konfiguracji serii ✅
- `ChartTooltipContent.vue`, `ChartLegendContent.vue`, `ChartContainer.vue`, `utils.ts` ✅

To jest **komponent `Chart` z shadcn-vue**, spójny stylistycznie z resztą UI. Istotne: ADR wymienia jako słabość ECharts „ręczne mapowanie tokenów Tailwind na opcje serii" (§6) — a to jest dokładnie problem, który ta warstwa **już rozwiązuje** dla unovis. Wybór ECharts oznacza więc porzucenie działającej integracji theme'u, tooltipa i legendy, nie tylko dodanie zależności.

### 7.2 Argument rozstrzygający dotyczy innego ekranu niż ten, którym uzasadniono pilność

Decyzja stoi na `echarts.connect()` (synchronizacja kursora między niezależnymi wykresami), z uzasadnieniem przez krytyczność **nietykalnego ekranu Waits**. Ale wzorzec DPA na Waits to **nawigacja sekwencyjna** (`wykres → dzień → godzina → zapytanie`) — kolejne widoki, nie kilka wykresów jednocześnie ze wspólnym kursorem.

Synchronizacja kursora jest realnie potrzebna na **Instance detail**, gdzie ustawia się obok siebie kilka wykresów metryk (CPU, IO, waity) pod jednym crosshairem. To ekran ważny, ale **nie nietykalny** (§7.2b vision.md). Wymaganie jest prawdziwe — przypisano mu tylko nie tę wagę.

### 7.3 Wniosek: odwrócić kolejność spike'ów

ADR proponuje spike'i **po** przyjęciu rekomendacji. Skoro incumbent jest darmowy, a zmiana ma realny koszt (7.1), kolejność powinna być odwrotna — **spike rozstrzyga, nie potwierdza**:

| Spike | Pytanie | Kryterium decyzji |
|---|---|---|
| A. unovis cross-container sync | czy da się zsynchronizować kursor/okno między osobnymi `XYContainer` przez współdzielony stan reaktywny Vue? (dziś ❓) | jeśli **tak** → zostajemy przy unovis, zero migracji, warstwa shadcn zachowana |
| B. ECharts bundle + wydajność | tree-shaken rozmiar dla `bar + dataZoom + tooltip + canvas` oraz render kilkudziesięciu serii × tysiące punktów | jeśli A wypadnie **nie**, a B **tak** → migracja na ECharts wg tego ADR |

Budżet: **2–3 dni**, w Fazie 0a roadmapy. Oba spike'i odpowiadają na jedyne dwa ❓ w tej analizie — i oba są tanie względem kosztu pomyłki na głównym ekranie produktu.

**Status rekomendacji:** ECharts jest **domyślną ścieżką na wypadek, gdy spike A wypadnie negatywnie**, a nie decyzją przyjętą. Pozostałe ustalenia ADR — odrzucenie Highcharts i AG Charts Enterprise na licencji ✅, odrzucenie uPlot na braku stacked bar ✅, odrzucenie Plotly na rozmiarze ✅, oraz zasada „jedna biblioteka, nie dwie" ✅ — przyjmuję bez zastrzeżeń.

---

## 8. Źródła

- [highcharts.com/blog — Our new EULA makes free usage clearer](https://www.highcharts.com/blog/news/our-new-eula-makes-free-usage-clearer/)
- [shop.highcharts.com/license](https://shop.highcharts.com/license)
- [ag-grid.com/charts/javascript/community-vs-enterprise](https://www.ag-grid.com/charts/javascript/community-vs-enterprise/)
- [ag-grid.com/charts/license-pricing](https://www.ag-grid.com/charts/license-pricing/)
- [github.com/apache/echarts — LICENSE](https://github.com/apache/echarts/blob/master/LICENSE)
- [github.com/apache/echarts](https://github.com/apache/echarts) (gwiazdki, forki)
- [echarts.apache.org/handbook — Import (tree-shaking)](https://echarts.apache.org/handbook/en/basics/import)
- [echarts.apache.org/handbook — ARIA](https://echarts.apache.org/handbook/en/best-practices/aria/)
- [github.com/apache/echarts/issues/18585 — keyboard accessibility bug](https://github.com/apache/echarts/issues/18585)
- [echarts.apache.org/en/feature.html](https://echarts.apache.org/en/feature.html)
- [community.grafana.com — Apache ECharts syncing dataZoom sliders](https://community.grafana.com/t/apache-echarts-syncing-datazoom-sliders/139468)
- [codepen.io/sjcobb — ECharts connect example](https://codepen.io/sjcobb/pen/zYRVpGK)
- [bundlephobia.com — echarts](https://bundlephobia.com/package/echarts)
- [api.npmjs.org — downloads echarts](https://api.npmjs.org/downloads/point/last-month/echarts)
- [github.com/ecomfe/vue-echarts](https://github.com/ecomfe/vue-echarts)
- [api.npmjs.org — downloads vue-echarts](https://api.npmjs.org/downloads/point/last-month/vue-echarts)
- [github.com/f5/unovis](https://github.com/f5/unovis)
- [github.com/f5/unovis — LICENSE](https://github.com/f5/unovis/blob/main/LICENSE)
- [unovis.dev/docs/xy-charts/StackedBar](https://unovis.dev/docs/xy-charts/StackedBar/)
- [unovis.dev/docs/auxiliary/Brush](https://unovis.dev/docs/auxiliary/Brush/)
- [unovis.dev/docs/auxiliary/Tooltip](https://unovis.dev/docs/auxiliary/Tooltip/)
- [unovis.dev/docs/containers/XY_Container](https://unovis.dev/docs/containers/XY_Container/)
- [community.f5.com — Announcing Unovis 1.5 (F5 Distributed Cloud)](https://community.f5.com/kb/technicalarticles/announcing-unovis-1-5/339532)
- [bundlephobia.com — @unovis/ts](https://bundlephobia.com/package/@unovis/ts)
- [bundlephobia.com — @unovis/vue](https://bundlephobia.com/package/@unovis/vue)
- [api.npmjs.org — downloads @unovis/vue](https://api.npmjs.org/downloads/point/last-month/@unovis/vue)
- [github.com/chartjs/Chart.js — LICENSE](https://github.com/chartjs/Chart.js/blob/HEAD/LICENSE.md)
- [bundlephobia.com — chart.js](https://bundlephobia.com/package/chart.js)
- [github.com/chartjs/chartjs-plugin-zoom](https://github.com/chartjs/chartjs-plugin-zoom)
- [github.com/leeoniya/uPlot — LICENSE](https://github.com/leeoniya/uPlot/blob/master/LICENSE)
- [github.com/leeoniya/uPlot](https://github.com/leeoniya/uPlot)
- [bundlephobia.com — uplot](https://bundlephobia.com/package/uplot)
- [github.com/d3/d3 — package.json (ISC)](https://github.com/d3/d3/blob/main/package.json)
- [bundlephobia.com — d3](https://bundlephobia.com/package/d3)
- [github.com/plotly/plotly.js — LICENSE (MIT)](https://github.com/plotly/plotly.js/blob/master/LICENSE)
- [bundlephobia.com — plotly.js](https://bundlephobia.com/package/plotly.js)
- [github.com/vega/vega-lite — LICENSE (BSD-3-Clause)](https://github.com/vega/vega-lite/blob/main/LICENSE)
- [github.com/observablehq/plot — LICENSE (ISC)](https://github.com/observablehq/plot/blob/main/LICENSE)
- [components.json](../../components.json) — stack shadcn-vue / reka-ui potwierdzony w repo
- [package.json](../../package.json) — obecność `@unovis/ts` / `@unovis/vue` potwierdzona w repo

---

## Powiązane

- [../vision.md](../vision.md) §3.7, §4, §5, §6, §7.2b, §9
- [competitors/solarwinds-dpa.md](competitors/solarwinds-dpa.md) §4, §8
- [../plans/2026-07-30-boilerplate-from-family.md](../plans/2026-07-30-boilerplate-from-family.md) — pochodzenie `@unovis/*` w `package.json`
