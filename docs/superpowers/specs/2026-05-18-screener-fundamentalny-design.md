# Design: Screening fundamentalny — tab "📊 Screening" w SP500 + GPW

**Data:** 2026-05-18
**Status:** Zaakceptowany — gotowy do implementacji
**Autor:** Damian + Claude
**Powiązany feature:** [Finanse spółki](2026-05-14-finanse-spolki-design.md) (commit a5924f0) — reużywa `data/financials.py`.

## Overview

Dodanie tabu "📊 Screening" do istniejących stron `pages/7_sp500.py` i `pages/8_gpw.py` (jako 7-my tab, przed obecnym "💰 Finanse"). User wybiera dowolny filtr/sort z 12+ wskaźników finansowych i widzi top N spółek z całego universe (subset najlikwidniejszych).

Cel: ułatwić znalezienie konkretnych spółek wg kryteriów fundamentalnych — np. *"wszystkie spółki z P/E 10-15 i ROE>15%"*, *"top 10 GPW dywidendowych"*, *"tech spółki z EV/EBITDA<15 i rev growth>20%"*.

## Problem

Aktualnie GEM dashboard pokazuje wskaźniki finansowe TYLKO dla pojedynczej spółki (tab "Finanse" wybrana z selectboxa). Brak możliwości **przeglądania całego universe i sortowania po fundamentals**. Cross-asset screener (`11_screener.py`) pokazuje tylko **momentum**, nie fundamentals.

## Goals

- Pokazać pełną tabelę z 11 wskaźnikami dla całego subset universe (SP100 dla SP500, WIG20+mWIG40 dla GPW = razem ~160 spółek)
- 6 głównych filtrów widocznych od razu + 5 zaawansowanych w expander
- Sort by dowolnym wskaźnikiem (ascending/descending properly per metric)
- Top N selektor (5/10/15/25/wszystkie)
- Summary cards (liczba spółek, median P/E, median ROE, top sektor)
- CSV export dla downstream analysis
- Klik wiersza → pre-fill ticker w tabie Finanse (UX bonus)

## Non-Goals

- **Cross-asset (SP500 + GPW razem)** — tab per universe, nie nowa strona. Decyzja: czystsze rozdzielenie, różne edge cases (banki GPW, currency).
- **Pełen universe (456 SP500 + 121 GPW)** — subset SP100 + WIG20+mWIG40 wystarczy dla MVP. Mała kapitalizacja ma dziury w danych yfinance i tak.
- **Custom presets ("Value"/"Growth"/"Dividend")** — out of MVP. User wybiera filtry sam.
- **Real-time refresh** — cache 24h. Financials zmieniają się rzadko.
- **MCP financial-datasets bulk fetch** ($20+ pay-as-you-go per MEMORY) — yfinance wystarczy dla 160 tickerów.
- **Krypto + ETF screening fundamentalny** — krypto nie ma P/E, ETF ma TER/holdings, nie ratios. Out of scope.

## Architecture

```
data/
├── sp500_universe.py        [EDYTUJ] dodać export SP500_TOP100: list[str]
│                            Top-100 spółek S&P 500 by market cap (manual lub auto-pick)
├── financials.py            [EDYTUJ] dodać 2 funkcje:
│                            - bulk_fetch_universe(_tickers_tuple) → dict[ticker, dict]
│                              Iteruje _fetch_info (z cache 24h) dla każdego tickera.
│                              First run: 30-60s. Subsequent w 24h: instant cache hit.
│                            - to_screener_df(bulk) → pd.DataFrame
│                              Konwersja na DataFrame + pochodne (upside_pct, is_buy).

pages/
├── 7_sp500.py               [EDYTUJ] dodać 7-my tab "📊 Screening" przed "💰 Finanse"
│                            Logiczna kolejność: Ranking → Wykresy → Porownanie →
│                            Backtest → RS → Screening → Finanse (zoom na 1 spółkę)
│                            - 6 filtrów głównych (slider/multiselect)
│                            - expander z 5 zaawansowanymi
│                            - sort + top N
│                            - summary 4 cards
│                            - st.dataframe z natywnym sortowaniem
│                            - CSV export
│                            - klik wiersza → pre-fill sp_finanse_ticker
├── 8_gpw.py                 [EDYTUJ] analogicznie + GPW edge case:
│                            - bank handling: kolumny EV/EBITDA pokazują "N/A" dla GPW_BANKS
│                            - currency: "zł" zamiast "$" w cap slider + market_cap column
│                            - universe: WIG20 + mWIG40 (60 spółek) z gpw_universe.GPW_CATEGORIES
```

### Universe scope

- **SP500 → SP100**: top-100 spółek by market cap z `ALL_SP500_TICKERS`. Lista statyczna w `sp500_universe.SP500_TOP100` (manual, refresh raz na 6 miesięcy). Alternatywa: dynamicznie auto-pick top 100 po `market_cap` z bulk fetch — odłożone do iteracji 2.
- **GPW → WIG20 + mWIG40**: `GPW_CATEGORIES["WIG20"] + GPW_CATEGORIES["mWIG40"]` = 60 spółek. sWIG80 pominięty — yfinance ma duże dziury w pokryciu analityków dla małych GPW.

### Filtry główne (6 widocznych)

| # | Filtr | Type | Default | Zakres |
|---|---|---|---|---|
| 1 | P/E max | slider (float) | 25 | 5-100 |
| 2 | ROE min | slider (%) | 15 | 0-50 |
| 3 | EV/EBITDA max | slider (float) | 20 | 1-60 |
| 4 | Sektor | multiselect | wszystkie | unique sectors z DataFrame |
| 5 | Market cap min | number_input | $10B / 5 mld zł | 0-5000 |
| 6 | Tylko BUY | checkbox | False | bool |

### Filtry zaawansowane (5 w expander)

| # | Filtr | Default |
|---|---|---|
| 7 | Div Yield min (%) | 0 |
| 8 | Revenue Growth min (%) | -20 (faktycznie OFF) |
| 9 | Debt/E max | 500 (faktycznie OFF) |
| 10 | Profit Margin min (%) | -20 |
| 11 | P/B max | 30 |

### Sort by + Top N

- **Sort by**: dropdown z 13 opcji (ticker, name, sector, pe, fwd_pe, ev_ebitda, roe, profit_margin, dividend_yield, market_cap, revenue_growth, upside_pct, num_analysts).
- **Ascending direction**: per metric (P/E/EV-EBITDA/Debt/E/P/B → ascending = "taniej lepiej"; ROE/Profit/Div Yield/Rev Growth/Cap → descending = "więcej lepiej").
- **Top N**: `["5", "10", "15", "25", "Wszystkie"]`, default "15".

## Components

### Data layer — `data/financials.py` (rozszerzenie)

```python
@st.cache_data(ttl=86400, show_spinner="Pobieram dane fundamentalne universe...")
def bulk_fetch_universe(_tickers_tuple: tuple[str, ...]) -> dict[str, dict]:
    """Bulk fetch dla całego universe.

    Reuses _fetch_info (cache TTL 24h) — pierwsze wywołanie 30-60s,
    kolejne 24h instant (cache hit per ticker).

    Args:
        _tickers_tuple: tuple żeby cache klucz był hashable.

    Returns:
        dict[ticker, {info dict}] — empty dict dla tickerów z 404/timeout.
        Klucze: pe, fwd_pe, ev_ebitda, ebitda, roe, profit_margin,
                gross_margin, debt_to_equity, price_to_book, dividend_yield,
                revenue_growth, market_cap, name, sector, currency,
                num_analysts, target_mean, current_price, recommendation_key.
    """


def to_screener_df(bulk: dict[str, dict]) -> pd.DataFrame:
    """Konwersja bulk → DataFrame screen-ready.

    Pochodne pola:
        - upside_pct = (target_mean / current_price - 1) * 100
        - is_buy = recommendation_key in {"strong_buy", "buy", "outperform"}
    """
```

### UI layer — inline w `pages/7_sp500.py` i `pages/8_gpw.py`

```python
# wewnątrz with tab_screening: @st.fragment _screener_fragment():

# 1. Filtry główne (6) w 3-col × 2-row
# 2. Expander zaawansowane (5 filtrów w 3+2 col)
# 3. Sort + Top N + counter (3-col)
# 4. Bulk fetch + filtry + sort + top
# 5. Summary 4 cards
# 6. st.dataframe z selection_mode="single-row", on_select="rerun"
# 7. CSV export
```

### Helper functions (page-specific, ~30 LOC łącznie per page)

- `apply_filters(df, pe_max, roe_min, ...)` — kaskada warunków na DataFrame
- `_format_screener_df(df)` — fmt_pct/fmt_number/format_large_number na display
- `_render_summary_cards(df)` — 4 st.html cards w 4-col grid

Funkcje **NIE** wynosić do `components/` — różne dla SP500 vs GPW (bank hiding, currency).

## Data flow

```
[User otwiera tab "📊 Screening"]
              ↓
[Fragment startuje — Streamlit renderuje filtry z defaultami]
              ↓
[bulk_fetch_universe(tuple(SP500_TOP100))]
   ├─ Cache hit (TTL 24h)? → instant return cached dict[100 tickers]
   └─ Miss → iteracja 100 tickerów × _fetch_info(t):
         ├─ Per-ticker cache hit (z poprzednich sesji)? → instant
         └─ Miss → yf.Ticker(t).info → cache 24h + return
   Spinner: "Pobieram dane fundamentalne universe..."
   Total time: 30-60s first run, <1s drugi raz w 24h
              ↓
[to_screener_df(bulk) → DataFrame ~100 wierszy × ~18 kolumn]
              ↓
[Filtry aplikowane lokalnie (pandas mask)]
   ├─ df = df[df["pe"].fillna(np.inf) <= pe_max]  # NaN excluded gdy filter aktywny
   ├─ df = df[df["roe"].fillna(-np.inf) >= roe_min / 100]
   ├─ ... (analogicznie dla pozostałych 9)
   ├─ if buy_only: df = df[df["is_buy"]]
              ↓
[Sort + Top N]
   ├─ ascending_metrics = {"pe", "fwd_pe", "ev_ebitda", "debt_to_equity", "price_to_book"}
   ├─ ascending = sort_by in ascending_metrics
   ├─ df = df.sort_values(sort_by, ascending=ascending, na_position="last")
   ├─ if top_n != "Wszystkie": df = df.head(int(top_n))
              ↓
[Render]
   ├─ 4 summary cards (st.columns + st.html): count, median_pe, median_roe, top_sector
   ├─ st.dataframe(df_formatted, height=500, use_container_width=True,
   │              on_select="rerun", selection_mode="single-row",
   │              column_config=...)
   ├─ if selected: st.session_state[ticker_key] = clicked + info toast
   ├─ st.download_button "📥 Eksport CSV"
              ↓
[User zmienia filtr → fragment rerun → bulk cache hit → filter/sort re-aplikowane <100ms]
```

### Cache strategy

- **Per-ticker** (`_fetch_info`): TTL 24h, klucz `(funkcja, ticker)`. **Reuse między tabami** Finanse i Screening, między SP500 i GPW (gdy ticker pokrywa się — rzadkie).
- **Bulk** (`bulk_fetch_universe`): TTL 24h, klucz `(funkcja, tuple_tickerów)`. Praktycznie zawsze cache hit (universe statyczna).
- **Streamlit Cloud restart** → cache pamięci puste → first user czeka 30-60s. Akceptowalne.

### Pre-fill Finanse tab (UX bonus)

```python
sel = st.dataframe(df, on_select="rerun", selection_mode="single-row")
if sel and sel.selection.rows:
    clicked_ticker = df.index[sel.selection.rows[0]]
    st.session_state["sp_finanse_ticker"] = clicked_ticker
    st.info(f"✓ Wybrano {clicked_ticker} — przełącz na tab 💰 Finanse aby zobaczyć szczegóły")
```

Streamlit nie ma natywnego "switch tab by code" — user musi kliknąć tab Finanse sam. Toast jako wskazówka.

## Error handling

Strategia: **graceful per-ticker**, partial results OK, jasne info dla user'a.

| Scenario | Detekcja | Fallback |
|---|---|---|
| Pojedynczy ticker 404 (delisted) | `_fetch_info(t)` → `{}` | Skip w `bulk_fetch_universe`, brak rekordu w DataFrame |
| Yahoo rate limit 429 | Per-ticker try/except w `_fetch_info` | Ticker skipnięty. Po 24h TTL retry naturalnie |
| Cały bulk fails (sieć down) | `bulk_fetch_universe` pusty dict | UI: "Nie udało się pobrać danych. Sprawdź połączenie." + `st.stop()` |
| <70% pokrycie | `len(bulk) < 0.7 * len(universe)` | `st.warning("Pobrano N/100 spółek. Yahoo może być throttle'd.")` |
| NaN w polach filtrowanych | pandas `<=` z NaN = False | Spółka wykluczona gdy filtr aktywny. Documentacja w `st.caption` pod tabelą |
| Bank GPW | `ticker in GPW_BANKS` | Tabela: "N/A" w EBITDA/EV-EBITDA/FCF. Filter EV/EBITDA traktuje NaN jak NaN (filter wyklucza). Caption: "Banki nie raportują EBITDA — kolumny pokazują N/A" |
| Pusty wynik filtra | `df.empty` po wszystkich filter | UI: "Brak wyników po zastosowaniu filtrów. Rozluźnij kryteria." — bez tabeli/CSV |
| Sort by kolumna z dużą ilością NaN | `na_position="last"` | NaN zawsze na końcu, niezależnie ascending/descending |
| Currency mismatch | Walidacja per page (SP500: $B; GPW: mld zł) | Slider label uwzględnia walutę, wewnątrz konwersja: `cap_min * 1e9` |

### UX hints po render

```python
st.caption(
    "💡 Spółki z brakującym wskaźnikiem są odfiltrowane gdy filtr aktywny "
    "(np. spółka bez P/E nie pojawi się gdy P/E max < 100)."
)
# Dla GPW dodatkowo:
st.caption(
    "🏦 Banki (PKO, PEO, SPL, MBK, BHW, BNP, MIL, ING, ALR) nie raportują "
    "klasycznego EBITDA — kolumny EV/EBITDA pokazują „N/A bank”."
)
```

## Testing

GEM dashboard nie ma pytest — manual smoke + visual review.

### Manual smoke list

```
SP500 happy:
  defaults → ~20-40 spółek z 100 (top tech + finance)
  Sort by ROE descending → top 15 → AAPL, NVDA, MSFT na górze
  Klik AAPL → toast "Wybrano AAPL — przełącz na Finanse"
  CSV export → ASCII OK + PL znaki dla nazw

SP500 edge:
  P/E max = 5 → mało wyników (warning gdy 0)
  Sektor = Tech only → 15-20 spółek
  Tylko BUY ON → wykluczone HOLD/SELL spółki
  Sort by market_cap descending → AAPL/MSFT/NVDA top 5

GPW happy:
  defaults → ~15-25 spółek z 60
  Sort by ROE → CDR/DNP/PKN/ALE typowo wysokie

GPW bank edge:
  PKO/PEO/SPL/MBK widoczne z "N/A" w EV/EBITDA
  Filter EV/EBITDA max 15 → banki znikają (NaN excluded)
  Filter EV/EBITDA max 100 → banki nadal widoczne

Cross-edge:
  Pusty wynik (P/E≤5 + ROE≥50%) → info "Rozluźnij"
  Streamlit Cloud restart → first user 30-60s spinner
```

### Visual review checklist

- **Desktop (1920px)**: 6 filtrów w 3-col × 2-row, tabela full width, 11 kolumn
- **Tablet (768px)**: filtry 2-col, tabela horizontal scroll
- **Mobile (375px)**: filtry 1-col stack, tabela natywny scroll
- **Tabela**: gold header text, sortable kolumny, row highlight on hover
- **Summary cards**: gold accent dla "count" (active filter result)
- **Spinner**: tylko first load, nie blokuje przy zmianie filtrów

### Performance acceptance

- First load (cache miss): ≤60s dla 100 SP500, ≤45s dla 60 GPW
- Cache hit (≤24h): <1s
- Filter change: <100ms (in-memory pandas)
- Sort change: instant
- Streamlit Cloud restart: 1× full fetch (akceptowalne)

### Acceptance criteria (Definition of Done)

1. Tab "📊 Screening" widoczny w `7_sp500.py` i `8_gpw.py` jako 7-my (przed Finanse)
2. 6 głównych + 5 zaawansowanych filtrów działają
3. Sort by każdym z 13 wskaźników (ascending/descending properly per metric)
4. Top N: 5/10/15/25/all działa
5. 4 summary cards renderują się
6. st.dataframe z formatowaniem (P/E "36.1", ROE "141%", cap "4.38T")
7. CSV export działa, UTF-8 dla PL nazw
8. Banki GPW pokazują "N/A" w EV/EBITDA bez wykluczania z tabeli
9. Brak wyników → info message, no empty table
10. Klik wiersza → pre-fill `sp_finanse_ticker` / `gpw_finanse_ticker`
11. Mobile responsywne (manual DevTools)
12. Logi Streamlit Cloud bez ERROR z `bulk_fetch_universe`

## Open questions / Future work

**Iteracja 2 (jeśli feature się przyjmie):**

- **Custom presets** — radio "Value" / "Growth" / "Dividend" / "Custom" jako preset filter combinations
- **Full universe** (456 SP500 + 121 GPW) — z progress bar i ostrzeżeniem o 5-8 min first load
- **Auto-pick SP500 top-100** dynamicznie zamiast statycznej listy `SP500_TOP100`
- **MCP financial-datasets bulk** — szybszy fetch (<10s) ale $20+ pay-as-you-go
- **Save filter combinations** — st.session_state["saved_filters"], dropdown z historii
- **Compare 2-3 stocks side-by-side** z screening table → multi-select wierszy → mini-view
- **Sektory rotation hint** — pokazać "Tech 12 spółek vs Banki 3" jako bar chart kontekst
- **Historical comparison** — slider "P/E ratio 1Y ago" (wymaga dodatkowych yfinance calls)

**SP500_TOP100 maintenance:** lista statyczna wymaga okresowego review (raz na 6 miesięcy — np. po Q1 i Q3 quarterly results). Dodać komentarz "Last verified: 2026-05-18" w pliku.

**Yahoo throttling risk:** jeśli okaże się że Streamlit Cloud regularnie hit'uje 429, dodać `time.sleep(0.5)` między fetches w `bulk_fetch_universe` (zwolni do ~50s ale stabilniejsze).
