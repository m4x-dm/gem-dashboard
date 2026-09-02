# Top Picks — czwarta strategia (Niska zmienność)

**Data:** 2026-09-02
**Status:** Draft — czeka na review użytkownika
**Cel:** Dodać do `pages/9_top_picks.py` czwartą zakładkę **Niska zmienność** — piątkę defensywną wybieraną wyłącznie z szeregów cenowych, z symulacją wstecz i własnym append-only logiem.

## Kontekst

Strona 9 ma dziś trzy strategie: **Momentum** (co zrobił kurs), **Earnings Momentum** (co zrobił biznes), **Jakość biznesu** (jaki ten biznes jest). Wszystkie trzy odpowiadają na wariant pytania „co jest dobre". Żadna nie mierzy **ryzyka** — to nieobsadzony wymiar.

Druga luka jest architektoniczna. `MOMENTUM_SCORER` jest jedynym scorerem z `supports_asof=True`; earnings i quality mają `False`, bo yfinance oddaje stan na dziś niezależnie od żądanej daty, więc `simulate_rule()` słusznie odmawia im symulacji. Efekt: jedna strategia z historią i dwie, które muszą dopiero zapracować na track record. Reguła czysto cenowa jest **drugą z symulacją od pierwszego dnia**.

Trzecia przesłanka: reguła oparta wyłącznie na szeregu ceny samej spółki nie ma żadnej zależności od benchmarku ani od danych fundamentalnych. Awaria źródła indeksów WIG (naprawiona 2026-08-31, commit `86421f5`) ani braki pokrycia yfinance nigdy jej nie dotkną.

## Podstawa merytoryczna

Anomalia low-volatility: spółki o niskiej zmienności historycznie dają lepszy zwrot skorygowany o ryzyko niż te o wysokiej — wbrew CAPM. Blitz & van Vliet (2007), Baker/Bradley/Wurgler (2011).

Konsekwencja, którą strona ma powiedzieć wprost: **w silnej hossie ta reguła zostanie za Momentum.** To cecha, nie wada. Bez tego zdania czwarta zakładka wygląda jak słabsza wersja pierwszej.

## Odrzucone alternatywy

| Kandydat | Powód odrzucenia |
|---|---|
| **Risk-adjusted momentum** (Sharpe ranking) | Skład silnie skorelowany z zakładką Momentum — czwarta zakładka pokazywałaby w połowie miesięcy te same tickery. Psuje to, co dziś działa: dziś tylko MU powtarza się między trzema regułami. |
| **Trend + bliskość 52-week high** (George & Hwang 2004) | Konceptualnie prawie to samo co momentum; bliskość szczytu i wysoki zwrot 12M mocno się pokrywają. Ten sam problem duplikacji, mniej oczywisty. |
| **Beta względem indeksu** jako piąty komponent | Wymaga benchmarku. Wpięcie nowej strategii w źródło indeksów WIG oznaczałoby cichą degradację przy każdej jego awarii. Wszystkie wybrane komponenty liczą się z szeregu samej spółki. |
| **Hybryda: ranking cenowy + filtr fundamentalny** | Filtr fundamentalny nie jest as-of, więc symulacja albo znika, albo staje się świadomym przybliżeniem. Rezygnacja z symulacji przekreśla główny powód wyboru reguły cenowej. |

## Pomiar, który przesądził o zakresie GPW

Wątpliwość z sesji: czy filtr płynności nie zostawia zbyt małego universe na GPW, i czy nie potrzeba nowego źródła danych o spółkach. Zmierzone 2026-08-31 na pełnym universe 140 spółek:

| Przyczyna odpadnięcia z filtra | Spółek |
|---|---:|
| Za niski obrót (< 5 mln zł mediany 60d) | **103** |
| Przechodzi filtr | 33 |
| Za krótka historia (debiuty) | 3 |
| Brak danych | 1 |

**136 ze 140 spółek ma komplet danych z yfinance.** Nowe źródło dołożyłoby cztery tickery. Problemem nie jest dostawca danych, tylko realna płynność polskiego rynku — mediana obrotu wśród odrzuconych to 0,43 mln zł dziennie, maksimum 4,73 mln, cały sWIG80 poniżej progu.

Sufit pozycji przy 11 sektorach i `max_per_group=2` wynosi **21** przy pięciu potrzebnych. Filtr nie jest wąskim gardłem. Obniżanie progu do 2 mln dokłada 14 niepłynnych spółek za jeden punkt sufitu.

**Wniosek: universe, próg płynności i `MIN_TURNOVER` zostają bez zmian.** Strategia działa na obu rynkach.

Znalezione przy okazji, poza zakresem tego specu: `ARH.WA` nie zwraca żadnych danych (kandydat do usunięcia z universe), a `CRQ.WA`/`REX.WA`/`ROB.WA` mają 40–94 sesji historii i tak czy inaczej nie przejdą progu `MIN_HISTORY`.

## Reguła

`make_lowvol_scorer()` → `LOWVOL_SCORER`, `supports_asof=True`, okno **252 sesji**.

| Komponent | Miara | Kierunek | Waga |
|---|---|---|---:|
| `vol` | zmienność zrealizowana 12M (annualizowane odchylenie dziennych zwrotów) | mniej = lepiej | 0,35 |
| `drawdown` | najgłębszy drawdown w oknie 12M | płycej = lepiej | 0,25 |
| `downside` | downside deviation (odchylenie wyłącznie ujemnych zwrotów) | mniej = lepiej | 0,20 |
| `stability` | R² regresji log-ceny względem czasu, ze znakiem nachylenia | więcej = lepiej | 0,20 |

Punktacja przez istniejące `_weighted_percentiles()` — ta sama mechanika co `earnings` i `quality`, z renormalizacją wag do dostępnych komponentów. Komponenty „im mniej, tym lepiej" wchodzą ze znakiem minus, wzorem `debt_to_equity` w `make_quality_scorer()`.

### Dlaczego R² musi być podpisane znakiem nachylenia

Samo R² nagradza każdy równy trend, także równy zjazd. Spółka osuwająca się gładko w dół miałaby świetną „stabilność". Dlatego:

```
stability = R² * sign(nachylenia regresji)
```

Bez tego reguła zbierałaby najspokojniej umierające spółki — czyli dokładnie odwrotność zamierzonego efektu.

### Redundancja komponentów jest świadoma

`vol`, `drawdown` i `downside` są mocno skorelowane — mierzą warianty tego samego zjawiska. Realnie ryzyko waży więc ~0,80, a `stability` jest jedynym niezależnym wymiarem i stąd jej 0,20 mimo pozornie pomocniczej roli.

To jest wybór, nie przeoczenie: celem jest **piątka defensywna**, nie zbalansowana. Gdyby ważyć te trzy komponenty równo z czwartym, reguła przestałaby mierzyć ryzyko, a zaczęła mierzyć „ładny wykres".

### Okno 252 jest zawsze dostępne

`_eligible()` wymaga `MIN_HISTORY = 273` sesji, więc okno 252 ma komplet danych dla każdej spółki, która w ogóle przeszła filtr. Nie potrzeba osobnej gałęzi na krótkie szeregi.

### Brak lookahead bias jest strukturalny

`select_picks()` przekazuje scorerowi `px = prices.loc[:asof]` — dane po `asof` są odcięte, zanim scorer je zobaczy. Scorer czytający wyłącznie ceny nie ma żadnego innego wejścia, więc `supports_asof=True` jest tu prawdziwe, a nie deklarowane. To odróżnia tę regułę od `earnings` i `quality`, które sięgają po `get_ratios_snapshot()` zwracający stan na dziś.

## Kolizja w pliku symulacji — do rozwiązania w implementacji

`scripts/update_top_picks.py` zapisuje wynik jako `sim[market]`, kluczując **wyłącznie po rynku**:

```python
sim[market] = {"dates": ..., "equity": ..., "benchmark": ...}
```

Dziś to działa, bo tylko `momentum` ma `simulate: True`. Low-vol jest drugą taką strategią i **nadpisałaby wyniki momentum** w `top_picks_sim.json`.

**Wybór: `SIM_PATHS` odwzorowujące istniejące `HISTORY_PATHS`** — osobny plik `data/top_picks_lowvol_sim.json`.

| Kryterium | Osobny plik (wybrane) | Zagnieżdżenie po strategii |
|---|---|---|
| Migracja | brak | trzeba przepisać plik i czytnik |
| Ryzyko dla momentum | zero, plik nietknięty | ruszamy jedyny prawdziwy track record |
| Spójność z kodem | identyczny wzorzec jak `HISTORY_PATHS` | nowy, osobny wzorzec |
| Decyzja projektowa nr 3 z F18 | zachowana | zachowana |

## Zakres zmian

| Plik | Zmiana |
|---|---|
| `data/top_picks.py` | `LOWVOL_WEIGHTS`, `LOWVOL_WINDOW = 252`, `make_lowvol_scorer()`, `LOWVOL_SCORER`; wpisy w `RULE_VERSIONS`, `STRATEGY_MARKETS`, `HISTORY_PATHS`; nowe `SIM_PATHS` |
| `scripts/update_top_picks.py` | wpis w `STRATEGIES` (`simulate: True`, `critical: False`), obsługa `_scorer_for("lowvol")`, zapis symulacji pod `SIM_PATHS[strategy]` zamiast wspólnego `SIM_PATH` |
| `pages/9_top_picks.py` | czwarta zakładka; reużycie `top_pick_cards()`, `picks_return_bar()`, `category_pie()`, `kpi_card()`, `section_band()`; opis reguły i zdanie o zachowaniu w hossie |
| `.github/workflows/*.yml` | **`git add` musi objąć `top_picks_lowvol_history.json` i `top_picks_lowvol_sim.json`** |
| `tests/test_top_picks.py` lub nowy plik | testy komponentów i integracji z `select_picks` |
| `CLAUDE.md` | sekcja Top Picks (F18) — czwarta strategia |

### Krok `git add` w CI jest krytyczny

Przy poprzednim rozszerzeniu (2026-08-07) workflow liczył nowe strategie co miesiąc i **nie commitował ich**, bo `git add` wymieniał tylko dwa stare pliki — logi nigdy by nie narosły. Błąd wyłapany poza planem. Ten spec wymienia ten krok jawnie, żeby nie powtórzyć.

## Testy

| Obszar | Test |
|---|---|
| `vol` | szereg spokojny dostaje wyższy score niż piłokształtny o tym samym zwrocie końcowym |
| `drawdown` | szereg z głębokim dołkiem przegrywa z płaskim o tej samej zmienności dziennej |
| `downside` | szereg z asymetrią w dół przegrywa z symetrycznym o tej samej zmienności całkowitej |
| `stability` znak | **równy trend spadkowy dostaje ujemny wkład**, nie wysoki — test na pułapkę R² |
| renormalizacja | spółka z częścią komponentów dostaje średnią z dostępnych, bez `NaN` |
| kontrakt `eligible` | scorer zwraca wyłącznie tickery z `eligible` |
| brak lookaheadu | ranking na `asof` nie zmienia się po dołożeniu danych po `asof` |
| spójność rejestrów | `RULE_VERSIONS`, `STRATEGY_MARKETS`, `HISTORY_PATHS`, `SIM_PATHS` mają identyczne zbiory kluczy |
| kolizja symulacji | zapis symulacji `lowvol` nie modyfikuje `top_picks_sim.json` |

## Świadomie poza zakresem

- **Zmiana progu płynności lub universe GPW** — pomiar wykazał, że nie jest to wąskie gardło.
- **Usunięcie `ARH.WA`** i przegląd debiutów — osobna robota (`gem-dashboard-ticker-audit`).
- **`use_container_width` deprecated** — 174 użycia w repo, osobna migracja.
- **`beat_streak` deklaruje 0–8 przy faktycznych 4** — dług z F18, nie dotyczy tej reguły.

## Ryzyka

| Ryzyko | Mitygacja |
|---|---|
| Symulacja pokaże atrakcyjny CAGR obarczony survivorship bias (universe jest dzisiejsze) | Ten sam czerwony `st.error` co przy momentum; liczb nie cytować jako wyniku strategii |
| Reguła wygląda na słabszą w hossie | Zakładka mówi wprost, czego się spodziewać i dlaczego to cecha |
| Czwarta zakładka zwiększa czas runu CI | Reguła jest czysto cenowa — korzysta z cen pobranych raz na rynek, bez dodatkowych zapytań do yfinance |
