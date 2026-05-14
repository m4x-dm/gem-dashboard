# Design: Tab "Finanse spółki" w GEM ETF Dashboard

**Data:** 2026-05-14
**Status:** Zaakceptowany — gotowy do implementacji
**Autor:** Damian + Claude

## Overview

Dodanie tabu "Finanse" do istniejących stron `pages/7_sp500.py` i `pages/8_gpw.py`, pozwalającego użytkownikowi wybrać spółkę z odpowiedniego universe i zobaczyć:

1. **Ratios snapshot** — 12 kluczowych wskaźników (PE, Fwd PE, EV/EBITDA, EBITDA, ROE, ROA, FCF, Debt/E, P/B, Profit Margin, Gross Margin, Div Yield)
2. **Forward konsensus EPS** — estimaty analityków na 0q/+1q/0y/+1y (avg, low, high, growth, number of analysts)
3. **Earnings history** — actual vs estimate dla ostatnich 8 kwartałów z surprise %
4. **Analyst recommendations** — target mean/median/high/low, recommendation key, liczba analityków, upside %

Wszystkie dane z `yfinance` (`Ticker.info`, `.earnings_estimate`, `.earnings_history`). Cache 24h.

## Problem

Obecnie GEM dashboard pokazuje tylko **ceny historyczne i momentum** (yfinance.download). User nie widzi wskaźników fundamentalnych ani konsensusu analityków per spółka. Ten brak utrudnia decyzje "czy momentum sygnał ma fundamenty" oraz "czy konsensus widzi to samo co model GEM".

## Goals

- Pokazać fundamentalne wskaźniki finansowe dla każdej spółki w universe SP500 (456) i GPW (121)
- Pokazać forward-looking konsensus analityków (0q/+1q/+1y EPS estimates)
- Pokazać historical accuracy analityków (last 8Q actual vs estimate)
- Pokazać target price + reco distribution

## Non-Goals

- **Generowanie własnych prognoz** (np. CAGR extrapolation) — w MVP nie. Decyzja: user widzi tylko konsensus analityków + historical accuracy, nie nasz model EPS.
- **Revision trend konsensusu w czasie** (jak zmieniał się avg estimate przez ostatnie 90 dni) — opóźnione, wymaga `Ticker.eps_revisions` extra dataset.
- **Peer comparison / sektor benchmark** — out-of-scope MVP. Iteracja 2.
- **Segmentowe KPI** (np. iPhone units dla AAPL) — wymaga MCP financial-datasets ($20+ pay-as-you-go per MEMORY), out-of-scope MVP.
- **Krypto i ETF** — feature dotyczy tylko akcji (SP500 + GPW). Krypto nie ma EBITDA, ETF ma TER/holdings nie ratios.

## Architecture

```
data/
├── financials.py             [NOWY] fetch + cache yfinance Ticker.info / .earnings_estimate / .earnings_history
│                             - get_ratios_snapshot(ticker) -> dict (12 metryk)
│                             - get_forward_consensus(ticker) -> DataFrame
│                             - get_earnings_history(ticker, n_quarters=8) -> DataFrame
│                             - get_analyst_recos(ticker) -> dict
│                             - is_bank(ticker) -> bool (sprawdza GPW_BANKS set)
│                             - format_currency(value, ticker) -> str (PLN dla .WA, USD pozostałe)
│                             - @st.cache_data(ttl=86400)  # 24h
│
├── gpw_universe.py           [EDYTUJ] dodać export GPW_BANKS: set[str]
│                             {"PKO.WA","PEO.WA","SPL.WA","MBK.WA","BHW.WA","MIL.WA","ALR.WA","BNP.WA",...}
│
components/
├── cards.py                  [ROZSZERZ] dodać 4 nowe funkcje renderujące:
│                             - ratios_card(snapshot, is_bank=False) -> grid 4×3 metryki
│                             - forward_consensus_card(consensus_df) -> Plotly bar chart EPS estimates
│                             - earnings_history_card(history_df) -> tabela last 8Q surprise %
│                             - analyst_recos_card(recos) -> target price + reco badge + distribution
│
pages/
├── 7_sp500.py                [EDYTUJ] dodać 6-ty tab "Finanse"
│                             - selectbox: default = top-1 z aktualnego ranking_df (jeśli istnieje)
│                                          fallback = pierwsza alfabetycznie z sp500_universe
│                             - layout: 2 cols (ratios | forward) + 2 cols (history | recos)
├── 8_gpw.py                  [EDYTUJ] analogicznie + check is_bank() dla GPW
│                             - dodatkowy info card: "Niektóre wskaźniki niedostępne dla GPW/banków"
```

## Components

### Data layer — `data/financials.py`

```python
@st.cache_data(ttl=86400)
def get_ratios_snapshot(ticker: str) -> dict:
    """
    Returns dict z 12 metryk z yfinance Ticker.info.
    Brakujące pola = None (graceful).

    Klucze: pe, fwd_pe, ev_ebitda, ebitda, roe, roa, profit_margin,
            gross_margin, fcf, debt_to_equity, price_to_book, dividend_yield,
            market_cap, current_price
    """

@st.cache_data(ttl=86400)
def get_forward_consensus(ticker: str) -> pd.DataFrame | None:
    """
    Returns DF: index=period (0q/+1q/0y/+1y), cols=avg/low/high/numAnalysts/growth.
    None gdy brak danych (np. 0 analityków).
    """

@st.cache_data(ttl=86400)
def get_earnings_history(ticker: str, n_quarters: int = 8) -> pd.DataFrame | None:
    """
    Returns DF z yfinance Ticker.earnings_history.
    Cols: quarter, eps_estimate, eps_actual, surprise_pct.
    None gdy brak.
    """

@st.cache_data(ttl=86400)
def get_analyst_recos(ticker: str) -> dict:
    """
    Returns dict: target_mean, target_median, target_high, target_low,
                  recommendation_key (buy/strong_buy/hold/sell), num_analysts,
                  current_price (do oblicz upside %).
    """

def is_bank(ticker: str) -> bool:
    """Check vs gpw_universe.GPW_BANKS set."""

def format_currency(value: float | None, ticker: str) -> str:
    """PLN dla .WA, USD pozostałe. None → '—'."""
```

### UI components — `components/cards.py`

```python
def ratios_card(snapshot: dict, is_bank: bool = False) -> None:
    """
    Grid 4×3. Dla banks: ukryj EBITDA/EV-EBITDA/FCF, label 'N/A (bank)'.
    Render przez st.html() (NIE st.markdown unsafe_allow_html — per CLAUDE.md).
    Empty snapshot → 'Brak danych ze źródła yfinance'.
    """

def forward_consensus_card(df: pd.DataFrame | None) -> None:
    """
    Plotly bar chart: 3-4 słupki (0q, +1q, +1y), wysokość = avg EPS estimate,
    error bars = low-high spread, hover = number of analysts + growth %.
    Plotly _base_layout() z components/charts.py (gold #C9A84C bars, dark bg).
    None df → info card 'Brak konsensusu analityków'.
    """

def earnings_history_card(df: pd.DataFrame | None) -> None:
    """
    Tabela 8 wierszy: Quarter | Estimate | Actual | Surprise%.
    Surprise% color: green > 0, red < 0 (przez fmt_pct z components/formatting.py).
    Average surprise w nagłówku ('Avg beat: +4.2%').
    None df → 'Brak historii earnings'.
    """

def analyst_recos_card(recos: dict) -> None:
    """
    Layout: target_mean + upside% (gauge), reco_key badge (strong_buy=green, hold=yellow, sell=red),
            target_high/median/low jako lista, num_analysts pod spodem.
    Pusty recos → 'Brak rekomendacji analityków'.
    """
```

## Data flow

```
[User klika tab "Finanse" w 7_sp500.py lub 8_gpw.py]
              ↓
[Selectbox spółki]
   ├─ default: top-1 z cached ranking DF danej strony (jeśli istnieje
   │           w st.session_state pod kluczem ustalonym w pages 7/8 — implementacja
   │           sprawdzi istniejący klucz przy writing-plans)
   └─ fallback: alfabetycznie pierwsza z universe (sp500_universe / gpw_universe)
              ↓
[User wybiera ticker, np. "AAPL"]
              ↓
[Sekwencyjne st.cache_data lookup — 4 wywołania]
   ├─→ get_ratios_snapshot("AAPL")        → dict (cache hit / yfinance miss)
   ├─→ get_forward_consensus("AAPL")      → DataFrame | None
   ├─→ get_earnings_history("AAPL", 8)    → DataFrame | None
   └─→ get_analyst_recos("AAPL")          → dict
              ↓
[Każdy fetch wrapped w try/except — błąd = None/empty]
              ↓
[Renderowanie cards w 2×2 grid]
   ├─ ratios_card(snapshot, is_bank=is_bank(ticker))
   ├─ forward_consensus_card(consensus_df)
   ├─ earnings_history_card(history_df)
   └─ analyst_recos_card(recos)
              ↓
[Każda card sprawdza input: None/empty → "Brak danych dla {ticker}"]
```

**Cache:**
- TTL 24h (`@st.cache_data(ttl=86400)`) — financials zmieniają się rzadko, oszczędza Yahoo rate-limit
- Klucz cache = `(funkcja, ticker)` — AAPL fetchowany raz/24h niezależnie czy z SP500 czy GPW page
- Side-effect: pierwszy `Ticker.info` w dashboardzie (były tylko `download` dla cen) — nowe wywołanie API
- Re-call optimization: przełączanie back-and-forth między tickerami trafia w cache po pierwszym fetch'u

**Sekwencyjne (nie parallel):** 4 calls × ~300-500ms = ~1.2-2s na pierwsze ładowanie. Akceptowalne. Parallel via `concurrent.futures` byłby gain ~500ms ale dodaje complexity, nie warto w MVP.

## Error handling

Strategia: **graceful degradation, per-card fallback, no global error**.

| Scenario | Detekcja | Fallback |
|---|---|---|
| yfinance network/404 | `try/except (HTTPError, ConnectionError, Exception)` w każdym `get_*` | return None / empty DF |
| Ticker delisted (CCC.WA → 404) | yf.Ticker(t).info rzuca lub zwraca info bez kluczowych pól | Card: "Spółka niedostępna w yfinance" |
| Partial data | Per-fetch try/except = niezależne | 3 cards renderują, 4-ta "Brak danych" |
| Bank GPW | `is_bank(ticker)` lookup w `GPW_BANKS` set | `ratios_card` skip EBITDA/EV-EBITDA/FCF, label "N/A — sektor bankowy" |
| 0 analityków (PKO.WA) | `numberOfAnalystOpinions in (None, 0)` | `analyst_recos_card`: "Brak rekomendacji"; `forward_consensus_card`: "Brak konsensusu" |
| NaN/inf w ratios | Istniejące `fmt_pct`/`color_for_value` z `components/formatting.py` traktują inf jako "—" | "—" w komórce (per CLAUDE.md inf handling) |
| GPW currency | Suffix `.WA` → PLN, inaczej USD | `format_currency(value, ticker)` helper |
| Cache miss + offline | Te same try/except | None propaguje, cards "Brak danych" |
| yfinance rate limit 429 | Try/except — fail → cache nic, retry naturalnie | "Spróbuj ponownie za chwilę" toast (raz, nie blokuje cards) |

**Brak globalnego error banner** — każda card sama radzi sobie z brakami. Strona zawsze działa, tab "Finanse" nigdy nie crashuje cały dashboard.

**Logging session-state:** nie dodajemy w MVP. Jak okaże się że duża część sWIG80 zawsze fail, w iteracji 2 dodamy `st.session_state["_finance_failures"]` analogicznie do istniejącego `_data_failures` z `downloader.py`.

## Testing

GEM dashboard nie ma pytest setup — test strategy realistyczna dla projektu Streamlit:

### Manual smoke test list (po deploy)

```
SP500 happy path:
  AAPL    → wszystkie 4 cards z pełnymi danymi (42 analityków)
  MSFT    → 26/26 metryk, 54 analityków
  NVDA    → high-growth, sprawdź fmt_pct na dużych wartościach

SP500 edge:
  CRWD    → cybersecurity, brak div yield (None → "—")
  XOM     → energy, traditional metrics
  XYZ123  → losowy nieistniejący → "Brak danych" 4× bez crash

GPW happy:
  PKN.WA  → Orlen, 25/26 + 9 analityków
  CDR.WA  → CD Projekt, wysoki PE
  ALE.WA  → Allegro, 17 analityków (najwięcej GPW)

GPW edge:
  PKO.WA  → BANK detection (skip EBITDA/EV-EBITDA/FCF) + 0 analityków
  CCC.WA  → 404 ticker zmieniony — wszystkie cards "Brak danych"
  CDR.WA  → currency: ceny w PLN, formatowanie z format_currency()

GPW small (sWIG80):
  losowy ticker z gpw_universe → sprawdź ile metryk faktycznie ma
```

### Visual review checklist

- **Desktop (1920px)**: 2×2 grid cards bez horizontal scroll
- **Tablet (768px)**: 2×2 grid lub przechodzi w 1 column
- **Mobile (375px)**: 1 column stack, każda card full width
- **Plotly forward chart**: ciemne tło `#0B0E1A`, gold `#C9A84C` bars, marginesy `_base_layout()` z `charts.py`
- **HTML cards**: użyć `st.html()` (per CLAUDE.md), inline styles (nie `<style>` block — DOMPurify strip)

### Performance

- Pierwszy load tickera: ≤2s (4× yfinance sekwencyjne)
- Subsequent (cache hit): <100ms
- Hot reload (5× back-and-forth tickerami): tylko 1 fetch pierwszego razu

### Acceptance criteria

1. Tab "Finanse" widoczny w `7_sp500.py` i `8_gpw.py`
2. Selectbox pre-fill z aktualnego rankingu lub fallback z universe
3. 4 cards renderują dla happy-path tickerów (AAPL, PKN, CDR)
4. Brak crash dla edge cases (CCC.WA, banki bez EBITDA, 0 analityków)
5. Cache 24h aktywny (drugi click ten sam ticker → instant)
6. Mobile responsywne (manual test DevTools)
7. Manual smoke list — 100% spółek z listy renderuje cards bez crash
8. Logi `streamlit run` bez ERROR/WARNING z `data/financials.py`

## Open questions / Future work

**Iteracja 2 (jeśli feature się przyjmie):**

- **Revision trend konsensusu** — wykres "jak zmieniał się avg EPS estimate w czasie" (`Ticker.eps_revisions`). Dodatkowy 5-ty card.
- **Session-state failure tracking** — `st.session_state["_finance_failures"]` analogicznie do `_data_failures`. Page 0 data status card update.
- **Peer comparison** — auto-pick top 5 spółek z tego samego sektora (GICS sector z sp500_universe), pokaż obok jako benchmark.
- **Segmentowe KPI** — wymaga MCP financial-datasets ($20+ pay-as-you-go per MEMORY). Tylko gdy user explicit zażąda.
- **PDF export integration** — dodać sekcję "Finanse spółki" do istniejącego `components/pdf_report.py`.
- **GPW small caps coverage** — jeśli sWIG80 ma duże luki, rozważyć drugi source (stockwatch.pl scrape lub Macrotrends).

**GPW bank detection — utrzymanie listy:** `GPW_BANKS` set w `gpw_universe.py` wymaga okresowego review (nowe banki, fuzje). Dodać komentarz "Last verified: 2026-05-14".

**Yfinance rate limit:** jeśli okaże się że bullk users walą w `Ticker.info` w short interval, rozważyć global throttle (np. 1 call/sec) lub przejście na MCP financial-datasets.
