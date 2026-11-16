# Top Picks — strategie analityczne (Polecane + Potencjał do ceny docelowej)

Data: 2026-11-16 · Status: zaakceptowany projekt, przed planem

## Cel

Trzy obecne strategie Top Picks (Momentum, Earnings Momentum, Jakość biznesu) dają
przeciętne wyniki. Dodajemy dwie strategie oparte na konsensusie analityków, żeby
po kilku miesiącach móc porównać je z obecnymi na prawdziwym track recordzie:

1. **Polecane przez analityków** — 5 spółek z najlepszą średnią rekomendacją.
2. **Potencjał do ceny docelowej** — 5 spółek o największym potencjale do średniej
   ceny docelowej, ale tylko spośród tych, które analitycy polecają kupić.

Obie działają na S&P 500 i GPW, w istniejącym mechanizmie Top Picks (append-only log
+ comiesięczny GitHub Action).

## Pomiar pokrycia danych (2026-11-16, yfinance `Ticker.info`)

| Pole | S&P 500 (próbka 30) | GPW (próbka 40) |
|---|---|---|
| `recommendationMean` | 29/30 | 14/40 |
| `targetMeanPrice` | 30/30 | 30/40 |
| `numberOfAnalystOpinions` ≥ 3 | 30/30 | 20/40 |
| ≥ 5 | 30/30 | 15/40 |
| mediana liczby analityków | 18 | 3 |

Wniosek: S&P 500 — pełne pokrycie. GPW — pula kandydatów ok. 1/3 indeksu
(warunkiem jest `recommendationMean`), stąd niższy próg analityków i obsługa
składu krótszego niż 5.

## Reguły

Wspólne dla obu strategii:

- Kandydaci = `eligible` z istniejącego `_eligible()` (filtr płynności i historii
  bez zmian).
- Próg analityków: `num_analysts >= MIN_ANALYSTS[market]`, gdzie
  `MIN_ANALYSTS = {"sp500": 5, "gpw": 3}`.
- Spółka bez wymaganego pola (`recommendation_mean`, a dla Potencjału także
  `target_mean` lub `current_price`) nie jest kandydatem (score = NaN).

**Polecane przez analityków (`analyst`)**

- Ranking: `recommendation_mean` rosnąco (1 = Strong Buy, 5 = Sell).
- Remis: większa `num_analysts` wyżej, potem ticker alfabetycznie (determinizm).
- Limit dywersyfikacji jak w obecnych strategiach: maks. 2 spółki z sektora.

**Potencjał do ceny docelowej (`upside`)**

- Warunek konsensusu: `recommendation_mean <= 2.5` (co najmniej „Buy”).
- `upside = target_mean / current_price - 1`; wymagane `current_price > 0`.
- Ranking: `upside` malejąco; remis jak wyżej.

Jeżeli kandydatów jest mniej niż 5, skład ma tyle pozycji, ilu jest kandydatów
(0–4), a UI pokazuje dopisek z przyczyną. Nie dobieramy spółek poniżej progów.

## Architektura i zmiany w kodzie

**`data/financials.py` — `bulk_fetch_universe`**
- Nowe pole `recommendation_mean` ← `info.get("recommendationMean")`.
  Pozostałe potrzebne pola (`num_analysts`, `target_mean`, `current_price`)
  już są.

**`data/top_picks.py`**
- `RULE_VERSIONS`: `"analyst": 1`, `"upside": 1`.
- `STRATEGY_MARKETS`: `"analyst": ("sp500", "gpw")`, `"upside": ("sp500", "gpw")`.
- `HISTORY_PATHS`: `top_picks_analyst_history.json`, `top_picks_upside_history.json`.
- `MIN_ANALYSTS`, `UPSIDE_MAX_RECOMMENDATION = 2.5`.
- `make_analyst_scorer(bulk_fn=None, market=...)` i `make_upside_scorer(...)` —
  wzorzec jak `make_quality_scorer`: `bulk_fn` wstrzykiwalny (testy), import
  `data.financials` wewnątrz funkcji (moduł importowalny bez streamlita),
  `supports_asof=False` (yfinance zna tylko stan na dziś → brak symulacji;
  `simulate_rule` i tak odrzuca takie scorery).
- Score zwracany tak, by `select_picks` (sortowanie malejąco) dał właściwą
  kolejność, z tie-breakiem po liczbie analityków zakodowanym w score:
  `analyst`: `score = -recommendation_mean + min(num_analysts, 99) * 1e-5`;
  `upside`: `score = upside + min(num_analysts, 99) * 1e-7`.
  (`recommendationMean` ma krok 0,01, więc składnik ≤ 0,001 nie zmienia
  kolejności między różnymi średnimi.)
- `select_picks`: sortowanie `scores.sort_index().sort_values(ascending=False,
  kind="mergesort")` — stabilne, więc pełne remisy rozstrzyga ticker
  alfabetycznie. Dla istniejących strategii zmienia to wynik tylko przy
  idealnie równych score'ach (praktycznie nie występuje); `RULE_VERSIONS`
  istniejących strategii bez zmian.
- Nowe strategie dziedziczą z `select_picks` limit `max_per_group=2` (maks.
  2 spółki z jednego sektora) — tak jak obecne.
- Kontekst analityków do kart (`recommendation_mean`, `num_analysts`,
  `target_mean`, `upside`) dopisuje do każdej pozycji `scripts/update_top_picks.py`
  po `select_picks` (z tego samego wyniku `bulk_fetch_universe`), zanim
  snapshot trafi do logu. Log nadal append-only.

**`scripts/update_top_picks.py`**
- Pętla po strategiach obejmuje `analyst` i `upside` (bez symulacji).

**`.github/workflows/<top picks>.yml`**
- `git add` rozszerzone o oba nowe logi (lekcja z 2026-08-07: bez tego CI liczy,
  ale nie commituje).

**`views/spolki/top_picks.py`**
- `st.tabs` rozszerzone do 5 zakładek: Momentum · Earnings Momentum · Jakość
  biznesu · Polecane przez analityków · Potencjał do ceny docelowej.
- Nowe zakładki używają istniejącego renderera zakładki forward-only (jak
  Jakość biznesu), karty `top_pick_cards` z dodatkową linią: konsensus
  (etykieta + liczba, np. „Strong Buy 1,4”), liczba analityków, cena docelowa,
  potencjał w %.
- Notka metodologiczna: źródło (konsensus z Yahoo Finance), progi, brak
  symulacji wstecz, to nie jest rekomendacja inwestycyjna.
- Teksty UI zgodne z konwencją danego pliku (sprawdzić przed edycją, czy
  `top_picks.py` używa polskich znaków, i trzymać się tego samego).

## Start logu

Pierwszy snapshot obu strategii zapisujemy od razu (data 2026-11-16, klucz
miesiąca 2026-11), z prawdziwą datą wyboru. Wynik live liczy się od tej daty;
UI opisuje start w połowie miesiąca. Kolejne snapshoty robi CI 1. dnia miesiąca.

## Obsługa błędów

- Brak danych z yfinance dla całego rynku → pusty skład + komunikat „dane
  chwilowo niedostępne”; brak wpisu do logu dla tego rynku (nie zapisujemy
  pustego składu jako wyniku).
- Pojedyncze braki pól → spółka odpada z rankingu, reszta działa.
- `current_price` ≤ 0 lub `target_mean` brak → spółka odpada z `upside`.

## Testy (offline, dane syntetyczne)

- `analyst`: kolejność po `recommendation_mean`, tie-break po liczbie analityków,
  próg `MIN_ANALYSTS` per rynek, pominięcie braków.
- `upside`: filtr konsensusu ≤ 2,5, kolejność po potencjale, odrzucenie
  `current_price` ≤ 0 / braku `target_mean`.
- Mniej niż 5 kandydatów → krótszy skład, bez wyjątku.
- `supports_asof=False` → `simulate_rule` podnosi `ValueError`.
- `data.top_picks` importowalny bez streamlita.
- AppTest: strona Top Picks renderuje 5 zakładek bez wyjątku (Premium).
- Workflow: test/asercja, że `git add` w workflow obejmuje wszystkie
  `HISTORY_PATHS`.

## Poza zakresem

- Historia rewizji rekomendacji / cen docelowych (yfinance jej nie daje wstecz).
- Łączenie strategii (np. momentum + konsensus) — do rozważenia po kilku
  miesiącach track recordu.
- Zmiany w trzech istniejących strategiach.
