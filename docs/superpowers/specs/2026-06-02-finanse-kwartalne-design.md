# Sprawozdania kwartalne SP500 + GPW — design

**Data:** 2026-06-02
**Status:** Draft — czeka na review użytkownika
**Cel:** Nowy tab "📈 Sprawozdania Q" w `pages/7_sp500.py` i `pages/8_gpw.py` z pełnymi sprawozdaniami finansowymi, beat/miss vs consensus analityków, forward consensus jako proxy guidance.

## Kontekst

GEM Dashboard ma już:
- Tab "Finanse spółki" (`7_sp500` + `8_gpw`) — ratios, forward consensus, recos (commit `a5924f0`, 2026-05-16)
- Tab "📊 Screening" — Screener Fundamentalny F12 dla 11 wskaźników (commit `8d20664` + `5241175`, 2026-05-18)
- `data/momentum.py` z `bulk_fetch_universe` (cache 24h)
- `GPW_BANKS` set do filtrowania bank-specific metryk

Nowa funkcjonalność rozszerza analizę o **pełne sprawozdania finansowe za 8 ostatnich kwartałów + 4 lata** plus **historię beat/miss vs consensus analityków** dla ~620 spółek.

## Scope MVP

**W MVP:**
- Nowy tab "📈 Sprawozdania Q" w `pages/7_sp500.py` + `pages/8_gpw.py` (3. tab w kolejności: Screening → Finanse → Sprawozdania Q)
- Screener bulk dla SP500 (full 500) + WIG20+mWIG40+sWIG80 (~620 total)
- Deep dive: 4 wewnętrzne taby (Beat/Miss historia, Income Statement, Balance Sheet, Cash Flow) za 8 Q kwartalne + 4 Y roczne
- Beat/miss vs consensus analityków (yfinance `earnings_history`)
- Forward consensus (`earnings_estimate`, `revenue_estimate`, `eps_trend`)
- Eksport CSV (screener + statements)
- Cache 24h, rate limiting, NaN handling
- Banki GPW edge case (reuse `GPW_BANKS`)

**Poza MVP (v2):**
- Guidance zarządu (transcripts SP500 / ESPI GPW / financial-datasets MCP)
- Cache warming background job (cron Streamlit Cloud)
- Comparison view 2 tickerów obok siebie
- Email alerts przed raportem
- Sentiment z newsów

---

## Architektura

### Data layer — nowy moduł `data/financials.py`

```python
bulk_fetch_earnings_history(universe, max_workers=8)
  -> DataFrame: ticker | last_q_date | eps_est | eps_act | eps_surprise_pct
                       | rev_est | rev_act | rev_surprise_pct
                       | beat_streak (kolejne Q gdzie EPS > est, 0-8)
                       | next_q_eps_est | next_q_eps_growth_yoy_pct
  -> cache: data/cache/earnings_history_{hash}.parquet, 24h TTL

fetch_quarterly_statements(ticker)
  -> dict {
      'income_stmt': DataFrame (8 ostatnich Q, indeks=metryka, kolumny=Q),
      'balance_sheet': DataFrame (8 Q),
      'cashflow': DataFrame (8 Q)
    }
  -> cache: data/cache/financials/{ticker}_q.parquet, 24h TTL

fetch_annual_statements(ticker)
  -> analogicznie, 4 ostatnie lata
  -> cache: data/cache/financials/{ticker}_a.parquet, 24h TTL

fetch_earnings_trend(ticker)
  -> DataFrame: 8 ostatnich Q + 4 forward Q
                 eps_est, eps_act, rev_est, rev_act, surprise_pct
                 + consensus revisions (eps_estimate_7d_ago, _30d_ago, _90d_ago)
  -> cache 24h
```

### yfinance endpointy używane

- `Ticker.earnings_history` — bulk: 4 ostatnie Q EPS estimate vs actual
- `Ticker.earnings_estimate` — forward consensus (1Q, 2Q, 1Y, 2Y EPS estimate + growth)
- `Ticker.revenue_estimate` — forward revenue consensus
- `Ticker.eps_trend` — revisions analityków w czasie
- `Ticker.income_stmt`, `.balance_sheet`, `.cashflow` (kwartalne i roczne)
- `Ticker.quarterly_income_stmt`, `.quarterly_balance_sheet`, `.quarterly_cashflow`

### UI integration

**Aktualna kolejność tabów (sprawdzona 2026-06-02):**

```
tab1: 📊 Ranking momentum
tab2: 📉 Wykresy
tab3: ⚖️ Porownanie
tab4: 🧪 Backtest momentum
tab5: 💪 Relative Strength
tab6: 📊 Screening
tab7: 💰 Finanse
```

**Nowy tab dodajemy jako tab8 na końcu** (naturalny progres "Finanse snapshot → Sprawozdania Q historia szczegółowa"):

```
... tab7: 💰 Finanse  →  tab8: 📈 Sprawozdania Q
```

Identyczna pozycja w `pages/7_sp500.py` i `pages/8_gpw.py`.

Tab "Sprawozdania Q" ma 2 wewnętrzne sekcje (radio button):
- **🔍 Screener** — bulk view ~620 spółek z filtrami beat/miss
- **🏢 Deep dive** — selectbox tickera + pełen widok dla jednej spółki

Selectbox tickera jest wspólny — klik "Pokaż szczegóły" w screenerze przełącza na deep dive z preselekcją.

### Universe

**Stan aktualny (sprawdzony 2026-06-02):**
- `data/sp500_universe.py` ma TYLKO `SP500_TOP100` (lista 100 tickerów) + `SP500_SECTORS`, `SP500_NAMES`, `SP500_SECTOR_MAP` jako puste dict (`= {}`). **Brak listy pełnego SP500.**
- `data/gpw_universe.py` ma 140 spółek (WIG20+mWIG40+sWIG80) jako **flat dict** `ticker -> indeks`, nie jako 3 osobne listy. Nazwy zmiennej do sprawdzenia w implementacji.

**Decyzja:** SP500 universe budujemy jako pierwszy krok implementacji.

**SP500 tab:** zbudować nową stałą `SP500_UNIVERSE` (full 500) w `data/sp500_universe.py`. Trzy opcje (zdecydować na początku implementacji):
1. Lista hardcoded z Wikipedia constituents (statyczna, wymaga update co kilka miesięcy)
2. Scrape Wikipedia tabeli `https://en.wikipedia.org/wiki/List_of_S%26P_500_companies` (dynamic, raz przy pierwszym uruchomieniu, cache do pliku)
3. Użyć `yfinance.tickers` lub zewnętrznego API listy SP500
**Rekomendacja:** opcja 2 (Wikipedia scrape) — najczystsze, jednorazowy bootstrap, lista trafia do pliku jako stała.

**GPW tab:** odczytać klucze z flat dict w `data/gpw_universe.py` (sprawdzić nazwę zmiennej w implementacji — najprawdopodobniej `GPW_UNIVERSE` lub `WIG_ALL`).

---

## UI — Screener (bulk view)

### Layout

```
┌─ FILTRY (expander, default expanded) ───────────────────────┐
│ Sektor [multiselect]   │  Beat status [Beat/Miss/Mixed]    │
│ Min EPS surprise %     │  Min Rev surprise %                │
│ Min beat streak (Q)    │  Sort by [9 metryk] ↑↓             │
│ Top N [10/25/50/100]   │  [🔄 Refresh cache]                │
└─────────────────────────────────────────────────────────────┘

┌─ SUMMARY CARDS (2×2) ───────────────────────────────────────┐
│ Beat EPS ostatni Q: X/620 │  Beat Rev ostatni Q: Y/620     │
│ Avg EPS surprise: +A%      │  Avg Rev surprise: +B%         │
└─────────────────────────────────────────────────────────────┘

┌─ TABELA (st.dataframe, paginated by Top N) ─────────────────┐
│ Ticker│Nazwa│Sektor│Q date│EPS est│EPS act│EPS Δ%│Rev est │
│ Rev act│Rev Δ%│Streak│Next Q EPS│YoY%│Sentiment              │
└─────────────────────────────────────────────────────────────┘

┌─ AKCJE ─────────────────────────────────────────────────────┐
│ Wybierz ticker: [selectbox] → [📈 Pokaż szczegóły]          │
│ [📥 Eksport CSV]                                             │
└─────────────────────────────────────────────────────────────┘
```

### Kolumny tabeli

| Kolumna | Typ | Źródło |
|---------|-----|--------|
| Ticker | str | universe |
| Nazwa | str | `Ticker.info['longName']` (z cache) |
| Sektor | str | `Ticker.info['sector']` (z cache) |
| Q date | str ("Q1'26") | `earnings_history` last row date → format |
| EPS est | float | `earnings_history.epsEstimate` |
| EPS act | float | `earnings_history.epsActual` |
| EPS Δ% | float (color-coded) | `(act-est)/abs(est)*100` |
| Rev est | float (B/M format) | `earnings_history.revenueEstimate` |
| Rev act | float (B/M format) | `earnings_history.revenueActual` |
| Rev Δ% | float (color-coded) | analogicznie |
| Streak | int (0-8, gold bar) | kolejne Q gdzie EPS act > est |
| Next Q EPS est | float | `earnings_estimate.iloc[0].avg` |
| YoY% | float | growth z `earnings_estimate.iloc[0].growth` |
| Sentiment | emoji | 🟢 oba beat / 🟡 mixed / 🔴 oba miss |

### Kolorystyka

- **EPS Δ% / Rev Δ%** — gold (`#C9A84C`) >+5%, green (`#10B981`) 0-5%, red (`#EF4444`) <0%
- **Streak** — gold bar fill 0-8 (wizualnie progress)
- Reuses `GOLD`/`GREEN`/`RED` z `components/formatting.py`

### Default state

Brak filtrów, sort by EPS Δ% desc, Top 50.

### Przykładowe presety w UI (sugestie tekstowe pod filtrami)

- "Najmocniejsze beats ostatniego Q": Beat status=Beat, sort by EPS Δ%, Top 25
- "Spółki konsystentne": Min streak=4, sort by streak desc
- "Defensywne sektory": Sektor=[Utilities, Cons. Staples], Beat status=Beat

---

## UI — Deep dive (per ticker)

### Header

```
🍎 Apple Inc. (AAPL) · Technology · Cap: $3.42T
Ostatni raport: Q2'26 (2026-04-30)  · Następny: 2026-07-30
```

### 4 karty metryk (2×2 grid)

```
Q2'26 EPS    │  Q2'26 Revenue
1.65 vs 1.50 │  $95.4B vs $94.1B
✅ +10.0%     │  ✅ +1.4%
─────────────┼─────────────────────
Beat streak  │  Forward Q3'26
4Q z rzędu   │  EPS 1.72 (+8.2% YoY)
```

### 4 wewnętrzne taby

#### Tab 1 — Beat/Miss historia (default)

- **Wykres 1:** EPS estimate vs actual (8 Q historyczne) + forward consensus 4 punkty z `earnings_estimate` (current Q, next Q, current FY, next FY — NIE 4 kolejne kwartały, yfinance taki układ udostępnia). Plotly bar chart, 2 grupy słupków per Q (estimate jasny, actual ciemny). Forward 4 punkty tylko estimate, przerywany wzór + tooltip wyjaśniający strukturę (Q/Q/Y/Y).
- **Wykres 2:** Revenue estimate vs actual (8 Q historyczne + 4 forward punkty z `revenue_estimate`), B/M format.
- **Tabela rewizje (eps_trend):**
  ```
  Q          | EPS now | EPS 30d ago | EPS 60d ago | Trend
  Q3'26 est  |  1.72   |    1.68     |    1.65     | ↗ +4.2%
  ```
  Pokazuje czy analitycy podnoszą/obniżają prognozy (lead indicator).

#### Tab 2 — Income Statement

Toggle: [Kwartalne 8Q] / [Roczne 4Y] (radio)

Tabela transposed (wiersze=metryki, kolumny=okresy):

```
Metryka         | Q1'26   | Q2'26   | Q3'26   | Q4'26   | ...
Revenue         | 89.5B   | 95.4B   | ...
Cost of Rev     | 52.2B   | 53.4B   | ...
Gross Profit    | 37.3B   | 42.0B   | ...
Gross Margin %  | 41.7%   | 44.0%   | ...
Op. Income      | 25.1B   | 28.9B   | ...
Op. Margin %    | 28.0%   | 30.3%   | ...
Net Income      | 21.4B   | 24.2B   | ...
Net Margin %    | 23.9%   | 25.4%   | ...
EPS Diluted     | 1.42    | 1.65    | ...
```

Wykres: trend Revenue + Net Income (8 Q), Plotly 2 linie. Annotacje YoY% nad ostatnimi 4 słupkami.

**Banki GPW:** alternatywne wiersze (Net Interest Income / Net Fee Income / Provisions / OpEx / Net Income).

#### Tab 3 — Balance Sheet

Wiersze: Total Assets / Current Assets / Cash / Long-term Debt / Short-term Debt / Total Equity / Goodwill. Plus liczone: Debt/Equity, Current Ratio, Quick Ratio.

Wykres: stacked bar Assets vs Liabilities + Equity (8 Q).

#### Tab 4 — Cash Flow

Wiersze: Operating CF / Investing CF / Financing CF / Free Cash Flow (= OCF − CapEx) / Dividends Paid / Stock Buybacks.

Wykres: waterfall lub 3 linie CF + FCF.

Banki: ukryte FCF (jak w F12 screener — niemiarodajne dla banków).

### Akcje pod widokiem

```
[🔄 Odśwież dane (skip cache)]   [📥 Eksport CSV statements]
[⬅ Powrót do screenera]
```

---

## Cache i performance

### Cache strategy

| Dane | Klucz | TTL | Lokalizacja |
|------|-------|-----|-------------|
| Bulk earnings history (per universe) | hash(universe) | 24h | `data/cache/earnings_history_{hash}.parquet` |
| Quarterly statements (per ticker) | ticker | 24h | `data/cache/financials/{ticker}_q.parquet` |
| Annual statements (per ticker) | ticker | 24h | `data/cache/financials/{ticker}_a.parquet` |
| Earnings trend (revisions) | ticker | 24h | `data/cache/financials/{ticker}_trend.parquet` |
| Ticker.info (sektor, nazwa) | reuse z `bulk_fetch_universe` | 24h | istniejące |

**Cache HIT path:** screener < 2 sek, deep dive < 0.5 sek (single ticker)
**Cache MISS path:** screener 15-30 min (bulk 620), deep dive 3-5 sek

### Rate limiting (yfinance)

yfinance free tier: realnie ~1-2 req/sec stabilnie. Bulk 620 spółek z `ThreadPoolExecutor(max_workers=8)`:
- ~2 sek per ticker × 620 / 8 workers = ~155 sek = 2.5 min teoretycznie
- realnie z retries 5-15 min

Implementacja:

```python
def _fetch_one(ticker, retries=3, backoff=2):
    for attempt in range(retries):
        try:
            return yf.Ticker(ticker).earnings_history
        except Exception as e:
            if attempt == retries - 1:
                return None  # NaN row
            time.sleep(backoff ** attempt)  # 1s, 2s, 4s
```

Throttle global: `time.sleep(0.1)` między batchami po 8 spółek.

### Performance budget

| Akcja | Budżet |
|-------|--------|
| Cold start (cache miss, 620 tickers) | <30 min |
| Warm start (cache HIT) | <2 sek |
| Deep dive cache HIT | <0.5 sek |
| Deep dive cache MISS | <5 sek |
| Filtr/sort w screenerze | <0.3 sek (client-side pandas) |

---

## Edge cases

### 1. Brak danych w yfinance (small caps GPW, niedawno IPO)
- `earnings_history` zwraca pusty DataFrame → NaN row w tabeli, sortowanie na koniec
- W deep dive: `st.warning("Brak danych yfinance dla tego tickera. Sprawdź źródło na stooq.pl/biznesradar.")`

### 2. Banki GPW vs banki SP500
- **Banki GPW** (PKO.WA, PEO.WA, MBK.WA, ALR.WA, ING.WA, SPL.WA, MIL.WA, BHW.WA, BNP.WA — pełna lista w `GPW_BANKS` w `data/momentum.py`):
  - Reuse `GPW_BANKS` set
  - Ukryta kolumna Revenue w screenerze (banki raportują Net Interest Income zamiast Revenue)
  - W deep dive Income Statement: alternatywne wiersze (NII, NFI, Provisions, OpEx, NI)
  - Ukryte FCF w Cash Flow (jak w F12 screener)
- **Banki SP500** (JPM, BAC, WFC, C, GS, MS, USB, PNC etc.):
  - Brak specjalnego handlingu — yfinance dla banków US zwraca tradycyjny IS z polem "Total Revenue" (= Net Interest Income + Total Noninterest Income), działa out-of-the-box
  - Wystarczy że yfinance daje sensowne dane — nie filtrujemy

### 3. Currency mismatch
- SP500 → USD (yfinance natural)
- GPW → PLN (yfinance dla `XXX.WA` tickerów)
- Format B/M per-tab: SP500 = "$XX.XB", GPW = "XX,X mld zł"

### 4. Q nieprzewidywalna data raportu
- Niektóre spółki publikują późno (np. polskie spółki Q4'25 w marcu/kwietniu 2026)
- "Q date" w tabeli pokazuje datę ostatniego dostępnego raportu, nie kalendarzowy Q
- Filter "tylko Q1'26" → mapowanie quarter date na nazwę kwartału fiskalnego (helper `_quarter_label(date)`)

### 5. Inf / NaN w surprise %
- Gdy `est = 0` → division by zero → `eps_surprise_pct = NaN` (nie inf)
- Helper: `safe_pct_change(act, est)` zwraca NaN gdy est jest 0 lub NaN

### 6. Forward consensus brakuje
- Niektóre spółki nie mają forward estimates (mało coverage analityków)
- Karta "Forward Q3'26" pokazuje "Brak konsensusu"

### 7. Initial bulk overload
- Pierwsze uruchomienie (zimny cache) = 15-30 min
- UX: `st.progress()` + tekst "Pobieram 1/620: AAPL…"
- Opcja "Pomiń bulk, pokaż tylko spółki z cache" dla użytkowników którzy nie chcą czekać

### 8. `@st.fragment` pułapka
- Helpery używane w `@st.fragment` muszą być na poziomie modułu PRZED `with tab:` blokiem (commit `d7c3407` — fix NameError)
- Stąd renderery jako importowane funkcje z `data/financials.py` (lub osobnego `components/financials_ui.py`)

---

## Testing strategy

- **Unit tests** (`tests/test_financials.py`):
  - `safe_pct_change(act, est)` — NaN/0 handling
  - `_quarter_label(date)` — mapowanie daty na "QX'YY"
  - `_compute_beat_streak(earnings_history)` — kolejne beat'y
  - Bank detection (`is_bank(ticker)`)

- **Integration tests:** mock yfinance, test bulk z 10 tickerami including 1 NaN row, 1 bank.

- **Manual QA checklist:**
  - AAPL — deep dive z forward consensus
  - JPM — bank USA, pokazuje Net Interest Income
  - PKO.WA — bank GPW, pokazuje NII, ukrywa Revenue+FCF
  - 11B.WA — small cap GPW, może mieć NaN
  - TSLA — forward consensus dostępny, mocne rewizje

---

## Pliki do utworzenia / zmiany

**Nowe pliki:**
- `data/financials.py` — data layer (~400-500 linii)
- `components/financials_ui.py` (opcjonalnie) — render helpery jeśli pages robią się za duże
- `tests/test_financials.py` — unit tests
- `data/cache/financials/` — katalog cache (utworzy się przy pierwszym fetch)

**Modyfikowane:**
- `pages/7_sp500.py` — dodanie 3-ciego taba "📈 Sprawozdania Q"
- `pages/8_gpw.py` — analogicznie
- `data/sp500_universe.py` — jeśli brak `SP500_UNIVERSE` (full 500), dodać
- `requirements.txt` — sprawdzić czy `pyarrow` jest dla parquet cache (powinno być z istniejących)
- `CLAUDE.md` — wpis o nowym tab w sekcji "Pages"

**Bez zmian:**
- `data/momentum.py` (`GPW_BANKS` reuse, nie ruszamy)
- `app.py` (PAGE_INFO bez zmian, to nie nowa strona)
- `auth.py` (bez zmian)

---

## Pre-implementation steps (krok 0)

Przed implementacją głównej funkcjonalności:

1. **Zbudować `SP500_UNIVERSE`** (full 500) w `data/sp500_universe.py` — rekomendowane przez Wikipedia scrape (`pandas.read_html` na constituents page), wynik wpisany jako stała.
2. **Sprawdzić nazwę zmiennej GPW universe** w `data/gpw_universe.py` (flat dict 140 tickerów) i wybrać access pattern (np. `list(GPW_UNIVERSE.keys())`).
3. **Zdecydować scope SP500 vs SP500_TOP100** w razie gdyby Wikipedia scrape był niepraktyczny — fallback na TOP100 jest akceptowalny dla pierwszej iteracji (zmiana scope MVP).

## Definition of Done

- [ ] `SP500_UNIVERSE` istnieje w `data/sp500_universe.py` (krok 0)
- [ ] `data/financials.py` z 4 funkcjami + cache + retry + ThreadPool
- [ ] Tab "📈 Sprawozdania Q" w `pages/7_sp500.py` i `pages/8_gpw.py`
- [ ] Screener z filtrami, kolorystyką, sortowaniem, eksportem CSV
- [ ] Deep dive z 4 wewnętrznymi tabami (Beat/Miss, IS, BS, CF) — 8 Q kwartalne + 4 Y roczne
- [ ] Edge cases: banki, GPW gaps, NaN, currency formatting, Q labeling
- [ ] Unit tests (5+ test cases) — `tests/test_financials.py` passes
- [ ] Manual QA — AAPL/JPM/PKO.WA/11B.WA/TSLA wszystkie renderują się bez błędów
- [ ] CLAUDE.md updated
- [ ] Commit + push do `m4x-dm/gem-dashboard` main
- [ ] Live na `gem-dashboard.streamlit.app` — sprawdzić auto-deploy
- [ ] MEMORY.md entry w `inwestowanie.edu.pl/MEMORY.md` o nowym feature (data, commit hash)
