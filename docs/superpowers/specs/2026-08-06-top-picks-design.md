# Top Picks — design

**Data:** 2026-08-06
**Status:** Draft — czeka na review użytkownika
**Cel:** Nowa strona `pages/24_top_picks.py` — comiesięcznie aktualizowana piątka spółek z S&P 500 i z GPW, wybierana deterministyczną regułą momentum, wraz z narastającym track recordem i osobną symulacją reguły wstecz.

## Kontekst

GEM Dashboard ma już wszystkie klocki, ale rozrzucone po stronach analitycznych:

- **`data/momentum.py`** — `latest_returns()` (12-1 skip-month dla akcji), `rank_based_score()` (percentyle per okres, `anti_1m` flip), `backtest_rotation()` (rotacja top N z kosztami i Belką)
- **`data/sp500_universe.py`** — `SP500_TOP100`, `SP500_SECTOR_MAP` (11 sektorów GICS), `SP500_NAMES`
- **`data/gpw_universe.py`** — `ALL_GPW_TICKERS` (140), `GPW_CATEGORY_MAP` (WIG20/mWIG40/sWIG80), `GPW_BANKS`
- **`data/financials.py`** — `bulk_fetch_universe()` (ratios snapshot, cache 24h)
- **F12 Screener Fundamentalny** (2026-05-18) — wzorzec tabeli z filtrami
- **F16 Bulk Insider Screener** (2026-06-05) — wzorzec strony premium z bulk danymi

Czego brakuje: strony, która **podejmuje decyzję i zapisuje ją w czasie**. Wszystkie istniejące screenery pokazują stan „na teraz" i znikają po odświeżeniu cache. Nie da się dziś odpowiedzieć na pytanie „co ten dashboard typował pół roku temu i ile na tym było".

Bezpośrednia geneza: sesja 2026-08-06, ręczna analiza 99 spółek SP500_TOP100 + 136 GPW (momentum + fundamenty), z której wyszła piątka US (MU, NVDA, GOOGL, UNH, C) i piątka GPW (SNT, XTB, BFT, PKN, PKO). Ta strona ma zautomatyzować **powtarzalną część** tamtej analizy.

## Decyzje projektowe (potwierdzone z użytkownikiem)

| Pytanie | Wybór | Odrzucone alternatywy |
|---|---|---|
| Model aktualizacji | Log w repo (`data/top_picks_history.json`) + GitHub Action co miesiąc | Liczenie na żywo bez stanu (brak track recordu); log aktualizowany ręcznie (zapomniany miesiąc = dziura) |
| Reguła selekcji | Momentum + limit sektorowy + filtr płynności | Tilt fundamentalny (nieodtwarzalny wstecz — yfinance nie ma historycznych P/E ani konsensusu); shortlist + ręczna decyzja (brak reguły = brak backtestu) |
| Źródło historii | Log realny (forward-only) + **osobna** symulacja reguły | Backfill loga symulacją (miesza dane symulowane z realnymi w jednej liczbie); tylko log (pusty wykres przez pół roku) |

## Scope MVP

**W MVP:**

- `data/top_picks.py` (~220 LOC) — silnik reguły, czysty Python, **zero importu Streamlita**
- `scripts/update_top_picks.py` (~150 LOC) — CLI dla Action i do odpalenia lokalnie
- `pages/24_top_picks.py` (~260 LOC) — UI, 3 sekcje, tylko odczyt artefaktów
- `.github/workflows/top-picks.yml` — cron `0 6 1 * *`
- `data/top_picks_history.json` — append-only log realnych typów
- `data/top_picks_sim.json` — pochodna symulacja (nadpisywana przy każdym uruchomieniu)
- `components/auth.py` — `PAGE_INFO[24]`, strona premium
- `app.py` — karta nawigacyjna
- `tests/test_top_picks.py` — ~10 testów na syntetycznych ramkach
- `CLAUDE.md` — sekcja F18

**Poza MVP (v2):**

- Konfigurowalne wagi scoringu w UI (psułoby powtarzalność loga)
- Alerty e-mail/Telegram przy zmianie składu
- Krypto i ETF jako dodatkowe rynki
- Przeliczanie obu portfeli na wspólną walutę (wymaga modelu FX)
- Wagi inne niż równe (risk parity, vol targeting)
- Eksport składu do Portfolio Buildera (page 10)

## Architektura

```
scripts/update_top_picks.py          [CI, raz w miesiacu]
    │
    ├── yf.download(Close + Volume, 12y)     ← jedyne miejsce, gdzie leci siec
    │
    ├── data/top_picks.py::select_picks(prices, volumes, meta, asof)
    │       └── append → data/top_picks_history.json   (idempotentnie)
    │
    └── data/top_picks.py::simulate_rule(prices, volumes, meta, od 2016)
            └── overwrite → data/top_picks_sim.json

pages/24_top_picks.py                [runtime, tylko odczyt]
    ├── load_history()  → sekcja 1 (aktualna piatka) + sekcja 2 (wyniki live)
    ├── download_prices(~10 tickerow, "1y")  → biezace ceny do wyceny pozycji
    ├── bulk_fetch_universe(~10 tickerow)    → kolumny fundamentalne (kontekst)
    └── load_sim()      → sekcja 3 (symulacja)
```

Zasada nadrzędna: **strona nic nie liczy**. Przy każdym wejściu pobiera ceny dla ~10 tickerów zamiast 240, więc otwiera się natychmiast. Reguła ma jedno źródło prawdy (`select_picks`), używane identycznie przez log i przez symulację.

## Reguła selekcji

`select_picks(prices, volumes, meta, asof, top_n=5, max_per_group=2, min_turnover)` → `list[dict]`

Wykonywana **osobno dla każdego rynku**, zawsze na zadaną datę `asof` (nigdy „na dziś"):

1. Przytnij dane do `prices.loc[:asof]` — jedyna bariera przed look-ahead, testowana wprost
2. Odrzuć tickery z < 273 sesji historii (wymóg okna 12-1)
3. **Filtr płynności:** mediana z 60 sesji `close × volume` ≥ `min_turnover`
   - S&P 500: **50 000 000 USD**
   - GPW: **5 000 000 PLN**
4. `latest_returns()` → `rank_based_score(weights={12M:0.40, 6M:0.30, 3M:0.20, 1M:0.10}, anti_1m=True)`
5. Sortuj malejąco, idź od góry i bierz ticker tylko jeśli jego grupa ma < `max_per_group` reprezentantów
   - S&P 500: grupa = sektor GICS z `SP500_SECTOR_MAP`
   - GPW: grupa = indeks z `GPW_CATEGORY_MAP` (WIG20/mWIG40/sWIG80)
6. Zatrzymaj się na `top_n`. Wagi równe (20% każda). Cena wejścia = `close` z `asof`

Punkty 3 i 5 nie są ozdobnikiem — na danych z 2026-08-06 filtr sektorowy odrzuca portfel złożony z pięciu producentów półprzewodników (MU, AMAT, AMD, KLAC, LRCX zajmowały 5 z 8 pierwszych miejsc), a filtr płynności odcina Archicom (141 tys. zł obrotu dziennie) i Echo Investment (498 tys.).

Wszystkie trzy składniki reguły są odtwarzalne wstecz: mapy sektorów są statyczne w repo, obrót liczy się z ceny i wolumenu, momentum z samych cen.

### Format `top_picks_history.json`

```json
{
  "2026-08-01": {
    "generated_at": "2026-09-01T06:04:11Z",
    "asof": "2026-08-31",
    "rule_version": 1,
    "sp500": [
      {"ticker": "MU", "name": "Micron Technology", "sector": "Information Technology",
       "score": 0.975, "entry_price": 893.19, "weight": 0.2}
    ],
    "gpw": [ … ]
  }
}
```

`rule_version` rośnie przy każdej zmianie parametrów reguły — bez tego porównywanie starych wpisów z nowymi jest bez sensu. UI pokazuje ostrzeżenie, gdy log zawiera mieszane wersje.

Klucz = pierwszy dzień miesiąca, w którym snapshot obowiązuje. `asof` = ostatnia sesja miesiąca poprzedniego, z której policzono skład.

## Trzy sekcje strony

### Sekcja 1 — Aktualna piątka

Dwie tabele (S&P 500 / GPW) ze składem z najnowszego snapshotu:

`Ticker · Nazwa · Sektor/Indeks · Score · Cena wejścia · Cena teraz · Zwrot od rebalansu`

plus dociągane na żywo kolumny fundamentalne z `bulk_fetch_universe()`: `P/E · fwd P/E · ROE · Dyw. · Konsensus (n) · Do celu`.

Nad tabelą jawnie: **„Kolumny fundamentalne są kontekstem do samodzielnej oceny — nie biorą udziału w wyborze."** Bez tego zdania strona sugeruje, że system waży P/E, czego nie robi.

Nagłówek: data snapshotu, `asof`, dni do następnego rebalansu.

### Sekcja 2 — Wyniki live

Krzywa kapitału z realnego logu: equal-weight, rebalans w dniu każdego snapshotu, kapitał startowy 10 000, benchmark **SPY** (S&P) / **WIG20** (GPW, ze stooq + fallback CSV).

Pod wykresem tabela per miesiąc: `Miesiąc · Skład · Zwrot portfela · Zwrot benchmarku · Różnica`.

Karty: zwrot od startu, liczba rebalansów, trafność (% miesięcy powyżej benchmarku), najlepszy i najgorszy typ.

Gdy log ma < 2 snapshoty: zamiast wykresu komunikat **„Track record narasta od pierwszego snapshotu (2026-08-01). Wróć po pierwszym rebalansie."** — nie rysujemy krzywej z jednego punktu.

### Sekcja 3 — Symulacja reguły

Osobna sekcja, otwierana `st.expander`, z czerwonym boxem na samej górze:

> **To nie jest track record.** Skład historyczny liczony z dzisiejszego universe (SP500_TOP100 i dzisiejsze WIG-i). Spółki, które wypadły z indeksów, w danych nie istnieją — survivorship bias zawyża wynik. Traktuj to jako test spójności reguły, nie jako obietnicę zwrotu.

Zawartość: krzywa kapitału 10 lat vs benchmark, statystyki (CAGR, MaxDD, Sharpe, Calmar, trafność), rozkład zwrotów miesięcznych. Liczone offline przez `simulate_rule()`, które w pętli po końcach miesięcy woła **to samo `select_picks()`** co log — jeśli reguła się zmieni, symulacja zmienia się razem z nią, automatycznie.

Koszty w symulacji: transakcyjne 0,1% od obrotu, Belka 19% od zysków realizowanych przy rotacji (parametry jak w `backtest_rotation()`).

Format `top_picks_sim.json` (plik pochodny, nadpisywany):

```json
{
  "generated_at": "2026-09-01T06:07:44Z",
  "rule_version": 1,
  "params": {"top_n": 5, "max_per_group": 2, "transaction_cost": 0.001, "tax_belka": 0.19},
  "sp500": {
    "dates":     ["2016-09-30", "2016-10-31", …],
    "equity":    [10000.0, 10240.5, …],
    "benchmark": [10000.0, 10105.2, …],
    "stats": {"cagr": 0.0, "max_dd": 0.0, "sharpe": 0.0, "calmar": 0.0, "hit_rate": 0.0}
  },
  "gpw": { … }
}
```

Punkty miesięczne, nie dzienne — plik zostaje mały, a strona rysuje go bez żadnych obliczeń.

## Skrypt CI i workflow

`scripts/update_top_picks.py`:

```
--asof YYYY-MM-DD   nadpisz date (do backfillu i testów)
--dry-run           policz i wypisz, nie zapisuj
--skip-sim          pomiń przeliczanie symulacji (szybkie odpalenie)
```

Zachowanie:

1. Pobiera Close + Volume dla obu universe, `period="12y"`, w porcjach po 40 tickerów, z retry 3× (backoff 2s/6s/18s)
2. **Walidacja twarda przed zapisem** — jeśli którykolwiek warunek nie przejdzie, skrypt kończy się `sys.exit(1)` i nic nie zapisuje:
   - dane dostępne dla ≥ 80% tickerów w danym rynku
   - ostatnia sesja nie starsza niż 5 dni od `asof`
   - `select_picks()` zwróciło dokładnie `top_n` pozycji
3. Zapis idempotentny: jeśli klucz miesiąca już istnieje w logu — **nie nadpisuje**, loguje i wychodzi z kodem 0
4. Przelicza `top_picks_sim.json` (chyba że `--skip-sim`)

Pusty lub częściowy snapshot jest gorszy niż brak snapshotu, bo kłamie w sekcji 2 na zawsze. Stąd bezwarunkowe `exit(1)` zamiast zapisu „co się dało".

`.github/workflows/top-picks.yml`: cron `0 6 1 * *` + `workflow_dispatch`, `permissions: contents: write` (wystarczy wbudowany `GITHUB_TOKEN`, bez zewnętrznego sekretu), setup Python 3.12, `pip install -r requirements.txt`, run, commit tylko gdy `git diff --quiet` zwróci zmianę, push na `main`. Streamlit Cloud podchwytuje push auto-redeployem.

Uwaga operacyjna: runnery GitHuba bywają rate-limitowane przez Yahoo. Retry to łagodzi, ale nieudany miesiąc jest możliwy — wtedy Action pada głośno (widoczne w zakładce Actions), a brakujący snapshot uzupełnia się ręcznie przez `--asof`.

## Waluty

Dwa niezależne portfele: S&P w USD, GPW w PLN. Bez przeliczania i bez wspólnej krzywej. Połączenie ich wymagałoby modelu FX (jest `USDPLN=X` na stronie 14), co dokłada zmienną nieistotną dla oceny samej reguły selekcji.

## Testy (`tests/test_top_picks.py`)

Na syntetycznych ramkach cen, bez sieci:

1. `select_picks` zwraca dokładnie `top_n` pozycji przy wystarczającym universe
2. Limit sektorowy: universe z 5 spółkami jednego sektora na szczycie → w wyniku maks. 2
3. Filtr płynności odrzuca ticker poniżej progu, mimo najwyższego score
4. Filtr historii odrzuca ticker z < 273 sesjami
5. **Brak look-ahead:** `select_picks(asof=T)` daje ten sam wynik, gdy ramka zawiera dane po T i gdy jest do T przycięta
6. Wagi sumują się do 1,0
7. `append_snapshot` nie nadpisuje istniejącego klucza miesiąca
8. `append_snapshot` na pustym pliku tworzy poprawną strukturę
9. `portfolio_equity` na 2 snapshotach i znanych cenach daje policzalny ręcznie wynik
10. `portfolio_equity` z jednym snapshotem zwraca pojedynczy punkt bez wyjątku

Test 5 jest najważniejszy — to on pilnuje, żeby symulacja z sekcji 3 nie oszukiwała.

## Ryzyka

| Ryzyko | Skutek | Mitygacja |
|---|---|---|
| Yahoo rate-limit na runnerze | Brak snapshotu za dany miesiąc | Retry 3×, głośny `exit(1)`, ręczne `--asof` |
| Zmiana universe (jak GPW 122→140 z lipca) | Symulacja po cichu zmienia „historię" | Symulacja oznaczona jako niehistoryczna; log realny nietykalny |
| Zmiana wag scoringu | Stare wpisy nieporównywalne z nowymi | `rule_version` w każdym snapshocie + ostrzeżenie w UI |
| Odbiór strony jako rekomendacji inwestycyjnej | Ryzyko prawne i realna szkoda użytkownika | Disclaimer w sekcji 1 i w stopce, ten sam ton co `render_footer()` |
| Norton TLS interception przy lokalnym odpaleniu | `CERTIFICATE_VERIFY_FAILED` udające `TypeError` | Skrypt czyta opcjonalny `GEM_CA_BUNDLE` i ustawia `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`/`CURL_CA_BUNDLE`; problem wyłącznie lokalny, CI go nie ma |

## Definicja ukończenia

- [ ] `data/top_picks.py` + 10 testów przechodzi
- [ ] `scripts/update_top_picks.py --dry-run` daje sensowną piątkę dla obu rynków
- [ ] Pierwszy realny snapshot w `top_picks_history.json`
- [ ] `top_picks_sim.json` z 10 latami symulacji
- [ ] `pages/24_top_picks.py` renderuje 3 sekcje, w tym stan „jeden snapshot"
- [ ] `app.py` + `auth.py` + `CLAUDE.md` zaktualizowane
- [ ] Workflow odpalony ręcznie przez `workflow_dispatch` i zakończony sukcesem
- [ ] Cały pakiet testów repo przechodzi (52 istniejące + nowe)
