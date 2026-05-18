# Screener Fundamentalny Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dodać tab "📊 Screening" do `pages/7_sp500.py` i `pages/8_gpw.py` — pełna tabela z 11 wskaźnikami fundamentalnymi, 6 filtrów głównych + 5 zaawansowanych, sort by + top N + CSV export, dla subset universe (SP100 + WIG20+mWIG40 = ~160 spółek).

**Architecture:** Reuse `data/financials.py:_fetch_info` (cache 24h z poprzedniego feature). Dodać `bulk_fetch_universe(tickers_tuple) → dict` + `to_screener_df(bulk) → DataFrame`. Tab UI inline w obu pages (per-page edge cases: bank "N/A" dla GPW, currency display).

**Tech Stack:** Streamlit 1.55, pandas, yfinance, plotly (już używane). Brak pytest — smoke tests przez standalone `venv/Scripts/python.exe -c "..."` (jak w `2026-05-14-finanse-spolki-plan.md`).

**Spec:** [2026-05-18-screener-fundamentalny-design.md](../specs/2026-05-18-screener-fundamentalny-design.md) (commit `e941428`)

---

## File Structure

```
data/
├── sp500_universe.py             [MODIFY] +SP500_TOP100: list[str] (statyczna lista top-100 by cap)
├── financials.py                 [MODIFY] +bulk_fetch_universe() + to_screener_df()
                                            Reuses _fetch_info (cache 24h) z poprzedniego feature.

pages/
├── 7_sp500.py                    [MODIFY] +7-my tab "📊 Screening" przed "💰 Finanse"
                                            +_screener_fragment() z 6 filtrami głównymi + 5 advanced
                                            +apply_filters() helper (page-local)
                                            +_format_screener_df() helper
                                            +_render_summary_cards() helper
├── 8_gpw.py                      [MODIFY] analogicznie + GPW edge cases:
                                            - currency "zł" w cap slider + market_cap column
                                            - bank handling: ratios_for_bank() helper
                                            - universe: WIG20+mWIG40 (60 spółek)

CLAUDE.md                         [MODIFY] dodać sekcję Screener Fundamentalny (F12)
```

Każdy plik ma jedną odpowiedzialność. Filtry i format helpers per-page bo różnice w currency/banks/universe — przeniesienie do `components/` byłoby premature abstraction (per spec sekcja Architecture).

---

### Task 1: SP500_TOP100 lista

**Files:**
- Modify: `data/sp500_universe.py:end-of-file`

- [ ] **Step 1: Sprawdź gdzie kończy się plik + jakie eksporty już istnieją**

```bash
cd "C:/Users/m4x/Desktop/AI/gem-dashboard"
tail -10 data/sp500_universe.py
grep "^[A-Z_]* =" data/sp500_universe.py | head
```

Expected: na końcu pliku jest `ALL_SP500_TICKERS = list(SP500_NAMES.keys())` lub podobny.

- [ ] **Step 2: Dopisz SP500_TOP100 na końcu pliku**

```python
# Top-100 spółek S&P 500 wg market cap (snapshot 2026-05).
# Lista statyczna — refresh raz na 6 miesięcy (Q1 + Q3 quarterly results).
# Używana przez tab "📊 Screening" w pages/7_sp500.py (subset universe dla
# szybkiego bulk fetch — 100 zamiast 456 tickerów).
# Last verified: 2026-05-18
SP500_TOP100: list[str] = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK-B",
    "JPM", "V", "WMT", "MA", "UNH", "XOM", "JNJ", "PG", "HD", "ORCL",
    "LLY", "ABBV", "BAC", "AVGO", "COST", "NFLX", "CRM", "CVX", "MRK",
    "ADBE", "AMD", "PEP", "KO", "TMO", "ACN", "MCD", "LIN", "ABT",
    "CSCO", "WFC", "DHR", "TXN", "DIS", "VZ", "INTU", "CAT", "PM",
    "QCOM", "IBM", "AXP", "BX", "AMGN", "GE", "PFE", "ISRG", "RTX",
    "T", "GS", "NOW", "SPGI", "NEE", "UBER", "BKNG", "PGR", "BLK",
    "TJX", "HON", "C", "SCHW", "AMAT", "SYK", "LOW", "DE", "ELV",
    "LMT", "MDT", "MS", "BSX", "REGN", "PLD", "VRTX", "ADP", "GILD",
    "CB", "ETN", "MMC", "ANET", "ADI", "TMUS", "MU", "SO", "PANW",
    "BMY", "INTC", "LRCX", "KLAC", "DUK", "CI", "ICE", "AON", "MO",
    "ZTS",
]
```

Filter logic: `[t for t in SP500_TOP100 if t in ALL_SP500_TICKERS]` (na wypadek gdyby ALL_SP500_TICKERS się zmienił między aktualizacjami).

- [ ] **Step 3: Weryfikacja parsowania + długości listy**

```bash
venv/Scripts/python.exe -c "
from data.sp500_universe import SP500_TOP100, ALL_SP500_TICKERS
print(f'SP500_TOP100: {len(SP500_TOP100)} tickerów')
missing = [t for t in SP500_TOP100 if t not in ALL_SP500_TICKERS]
print(f'NOT in ALL_SP500_TICKERS: {missing[:10]}')
print(f'first 5: {SP500_TOP100[:5]}')
"
```

Expected:
```
SP500_TOP100: 100 tickerów
NOT in ALL_SP500_TICKERS: []  (lub bardzo mała lista — wtedy fix tickery)
first 5: ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN']
```

- [ ] **Step 4: Commit**

```bash
git add data/sp500_universe.py
git commit -m "Add SP500_TOP100 — subset top-100 spółek by market cap

Statyczna lista do tab Screening (subset universe = 100 zamiast 456
tickerów dla bulk yfinance.info fetch). Refresh co 6 miesięcy.
Last verified: 2026-05-18.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: bulk_fetch_universe + to_screener_df

**Files:**
- Modify: `data/financials.py:end-of-file`

- [ ] **Step 1: Sprawdź obecny układ pliku — gdzie kończą się funkcje get_***

```bash
grep -n "^def \|^@st" data/financials.py | tail -10
```

Expected: ostatnia funkcja to `format_large_number`, można dopisać po niej.

- [ ] **Step 2: Dopisz bulk_fetch_universe na końcu pliku**

```python
# ---------------------------------------------------------------------------
# Bulk fetch dla tab Screening (pages 7_sp500 + 8_gpw)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=86400, show_spinner="Pobieram dane fundamentalne universe...")
def bulk_fetch_universe(_tickers_tuple: tuple[str, ...]) -> dict[str, dict]:
    """Bulk fetch danych fundamentalnych dla całego subset universe.

    Reuses _fetch_info (cache TTL 24h) — pierwsze wywołanie 30-60s dla 100 tickerów,
    kolejne wywołania w 24h instant (cache hit per ticker).

    Args:
        _tickers_tuple: tuple zamiast list — żeby cache key był hashable.

    Returns:
        dict[ticker, {info dict}] — brak rekordu gdy ticker zwrócił 404/timeout.
    """
    out = {}
    tickers = list(_tickers_tuple)
    for t in tickers:
        info = _fetch_info(t)  # cached per ticker — drugi run instant
        if not info:
            continue
        out[t] = {
            "pe": info.get("trailingPE"),
            "fwd_pe": info.get("forwardPE"),
            "ev_ebitda": info.get("enterpriseToEbitda"),
            "ebitda": info.get("ebitda"),
            "roe": info.get("returnOnEquity"),
            "profit_margin": info.get("profitMargins"),
            "gross_margin": info.get("grossMargins"),
            "debt_to_equity": info.get("debtToEquity"),
            "price_to_book": info.get("priceToBook"),
            "dividend_yield": info.get("dividendYield"),
            "revenue_growth": info.get("revenueGrowth"),
            "market_cap": info.get("marketCap"),
            "name": info.get("longName") or info.get("shortName") or t,
            "sector": info.get("sector"),
            "currency": info.get("currency"),
            "num_analysts": info.get("numberOfAnalystOpinions") or 0,
            "target_mean": info.get("targetMeanPrice"),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "recommendation_key": info.get("recommendationKey"),
        }
    return out


def to_screener_df(bulk: dict[str, dict]) -> pd.DataFrame:
    """Konwersja bulk_fetch_universe wynik → DataFrame screen-ready.

    Dodaje 2 pochodne kolumny:
        - upside_pct = (target_mean / current_price - 1) * 100
        - is_buy = recommendation_key in {"strong_buy", "buy", "outperform"}

    Returns pusty DataFrame gdy bulk = {}.
    """
    if not bulk:
        return pd.DataFrame()
    df = pd.DataFrame(bulk).T  # ticker = index
    # Pochodne — używamy fillna(np.nan) bo target_mean może być None
    cp = pd.to_numeric(df["current_price"], errors="coerce")
    tm = pd.to_numeric(df["target_mean"], errors="coerce")
    df["upside_pct"] = (tm / cp - 1) * 100
    df["upside_pct"] = df["upside_pct"].replace([np.inf, -np.inf], np.nan)
    df["is_buy"] = (
        df["recommendation_key"].fillna("").astype(str).str.lower()
        .isin(["strong_buy", "buy", "outperform"])
    )
    df.index.name = "ticker"
    return df
```

- [ ] **Step 3: Test bulk_fetch_universe na 3 tickerach**

```bash
venv/Scripts/python.exe -c "
import streamlit as st
def passthrough(*a,**k):
    def decorator(fn): return fn
    return decorator
st.cache_data = passthrough

from data.financials import bulk_fetch_universe, to_screener_df

bulk = bulk_fetch_universe(('AAPL','MSFT','NVDA'))
print(f'bulk: {len(bulk)} spólek')
print(f'AAPL.pe: {bulk[\"AAPL\"][\"pe\"]}')
print(f'AAPL.roe: {bulk[\"AAPL\"][\"roe\"]}')
print(f'AAPL.sector: {bulk[\"AAPL\"][\"sector\"]}')

df = to_screener_df(bulk)
print(f'\nDF shape: {df.shape}')
print(f'columns: {list(df.columns)}')
print(f'AAPL upside_pct: {df.loc[\"AAPL\", \"upside_pct\"]}')
print(f'AAPL is_buy: {df.loc[\"AAPL\", \"is_buy\"]}')
"
```

Expected:
```
bulk: 3 spólek
AAPL.pe: ~36 (lub aktualna wartość)
AAPL.roe: ~1.4 (140%)
AAPL.sector: Technology

DF shape: (3, ~20)
columns: ['pe', 'fwd_pe', ...]
AAPL upside_pct: ~2.4
AAPL is_buy: True
```

- [ ] **Step 4: Test z 404 ticker (graceful skip)**

```bash
venv/Scripts/python.exe -c "
import streamlit as st
def passthrough(*a,**k):
    def decorator(fn): return fn
    return decorator
st.cache_data = passthrough

from data.financials import bulk_fetch_universe

bulk = bulk_fetch_universe(('AAPL', 'CCC.WA', 'INVALID_XYZ'))
print(f'bulk len: {len(bulk)}')
print(f'tickers: {list(bulk.keys())}')
"
```

Expected:
```
bulk len: 1
tickers: ['AAPL']
```

- [ ] **Step 5: Commit**

```bash
git add data/financials.py
git commit -m "Add bulk_fetch_universe + to_screener_df for Screener tab

bulk_fetch_universe(tickers_tuple) iteruje _fetch_info (cache 24h) dla
każdego tickera. First run 30-60s dla 100 tickerów, subsequent w 24h
instant cache hit. Graceful skip dla 404/timeout (pusty dict per ticker).

to_screener_df konwertuje na DataFrame z 2 pochodnymi kolumnami:
upside_pct + is_buy flag dla filtrowania.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: Helper functions w 7_sp500.py (apply_filters, format, summary)

**Files:**
- Modify: `pages/7_sp500.py:end-of-file` (przed `render_footer()`)

- [ ] **Step 1: Dodaj 3 helpery na końcu pliku, przed render_footer()**

Znajdź ostatnią linię przed `render_footer()` w `pages/7_sp500.py` (powinno być ~koniec _finanse_fragment). Dodaj przed:

```python
# ===========================================================================
# Screener fundamentalny — helpers (page-local, NIE używane indziej)
# ===========================================================================

def _apply_screener_filters(
    df: pd.DataFrame,
    *,
    pe_max: float,
    roe_min_pct: float,
    ev_ebitda_max: float,
    sectors: list[str],
    cap_min_usd: float,
    buy_only: bool,
    div_yld_min_pct: float,
    rev_growth_min_pct: float,
    debt_eq_max: float,
    profit_margin_min_pct: float,
    pb_max: float,
) -> pd.DataFrame:
    """Aplikuje 11 filtrów (6 main + 5 advanced). NaN-aware:
    spółki z brakującym wskaźnikiem są WYKLUCZONE gdy filtr aktywny.
    """
    out = df.copy()
    # 6 main
    out = out[out["pe"].fillna(np.inf) <= pe_max]
    out = out[out["roe"].fillna(-np.inf) >= roe_min_pct / 100.0]
    out = out[out["ev_ebitda"].fillna(np.inf) <= ev_ebitda_max]
    if sectors:
        out = out[out["sector"].isin(sectors)]
    out = out[out["market_cap"].fillna(0) >= cap_min_usd]
    if buy_only:
        out = out[out["is_buy"]]
    # 5 advanced
    out = out[out["dividend_yield"].fillna(-np.inf) >= div_yld_min_pct]
    out = out[out["revenue_growth"].fillna(-np.inf) >= rev_growth_min_pct / 100.0]
    out = out[out["debt_to_equity"].fillna(np.inf) <= debt_eq_max]
    out = out[out["profit_margin"].fillna(-np.inf) >= profit_margin_min_pct / 100.0]
    out = out[out["price_to_book"].fillna(np.inf) <= pb_max]
    return out


def _format_screener_df(df: pd.DataFrame, currency_sym: str = "$") -> pd.DataFrame:
    """Format kolumn na display strings. Zachowuje ticker jako index."""
    from data.financials import format_large_number
    out = df.copy()
    out["P/E"] = out["pe"].apply(lambda v: f"{v:.1f}" if pd.notna(v) else "—")
    out["Fwd P/E"] = out["fwd_pe"].apply(lambda v: f"{v:.1f}" if pd.notna(v) else "—")
    out["EV/EBITDA"] = out["ev_ebitda"].apply(lambda v: f"{v:.1f}" if pd.notna(v) else "—")
    out["ROE"] = out["roe"].apply(lambda v: f"{v*100:.0f}%" if pd.notna(v) else "—")
    out["Marża"] = out["profit_margin"].apply(lambda v: f"{v*100:.1f}%" if pd.notna(v) else "—")
    out["Div Yld"] = out["dividend_yield"].apply(lambda v: f"{v:.2f}%" if pd.notna(v) else "—")
    out["Cap"] = out["market_cap"].apply(lambda v: f"{currency_sym}{format_large_number(v)}" if pd.notna(v) else "—")
    out["Rev Gr."] = out["revenue_growth"].apply(lambda v: f"{v*100:+.1f}%" if pd.notna(v) else "—")
    out["Reco"] = out["recommendation_key"].fillna("").astype(str).str.upper().str.replace("_", " ")
    out["Nazwa"] = out["name"]
    out["Sektor"] = out["sector"].fillna("—")
    # Wybierz tylko display kolumny + zachowaj ticker w indexie
    return out[["Nazwa", "Sektor", "P/E", "Fwd P/E", "EV/EBITDA", "ROE", "Marża",
                "Div Yld", "Rev Gr.", "Cap", "Reco"]]


def _render_screener_summary(df: pd.DataFrame, total: int) -> None:
    """4 summary cards: liczba, median P/E, median ROE, top sektor."""
    from components.formatting import GOLD, MUTED, BG_CARD, BORDER
    n = len(df)
    pe_med = df["pe"].median() if "pe" in df.columns and n > 0 else None
    roe_med = df["roe"].median() if "roe" in df.columns and n > 0 else None
    top_sec = (df["sector"].value_counts().head(1) if "sector" in df.columns else pd.Series())

    c1, c2, c3, c4 = st.columns(4)
    c1.html(
        f'<div style="background:{BG_CARD};border:1px solid {GOLD}40;border-radius:8px;padding:10px;text-align:center">'
        f'<div style="color:{GOLD};font-size:10px;text-transform:uppercase">Spólek</div>'
        f'<div style="color:#fff;font-size:18px;font-weight:700">{n} / {total}</div></div>'
    )
    c2.html(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:10px;text-align:center">'
        f'<div style="color:{MUTED};font-size:10px;text-transform:uppercase">Med. P/E</div>'
        f'<div style="color:#fff;font-size:18px;font-weight:700">{pe_med:.1f}</div></div>'
        if pe_med is not None and pd.notna(pe_med) else
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:10px;text-align:center">'
        f'<div style="color:{MUTED};font-size:10px;text-transform:uppercase">Med. P/E</div>'
        f'<div style="color:#fff;font-size:18px;font-weight:700">—</div></div>'
    )
    c3.html(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:10px;text-align:center">'
        f'<div style="color:{MUTED};font-size:10px;text-transform:uppercase">Med. ROE</div>'
        f'<div style="color:#71C77E;font-size:18px;font-weight:700">{roe_med*100:.0f}%</div></div>'
        if roe_med is not None and pd.notna(roe_med) else
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:10px;text-align:center">'
        f'<div style="color:{MUTED};font-size:10px;text-transform:uppercase">Med. ROE</div>'
        f'<div style="color:#fff;font-size:18px;font-weight:700">—</div></div>'
    )
    if not top_sec.empty:
        sec_name = top_sec.index[0]
        sec_count = top_sec.iloc[0]
        c4.html(
            f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:10px;text-align:center">'
            f'<div style="color:{MUTED};font-size:10px;text-transform:uppercase">Top sektor</div>'
            f'<div style="color:#fff;font-size:12px;font-weight:700;line-height:1.3">{sec_name}<br>'
            f'<span style="font-size:10px;color:{MUTED}">({sec_count} spólek)</span></div></div>'
        )
    else:
        c4.html(
            f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:10px;text-align:center">'
            f'<div style="color:{MUTED};font-size:10px;text-transform:uppercase">Top sektor</div>'
            f'<div style="color:#fff;font-size:18px;font-weight:700">—</div></div>'
        )
```

- [ ] **Step 2: Smoke test helperów (przed dalszym kodowaniem UI)**

```bash
venv/Scripts/python.exe -c "
import streamlit as st
def passthrough(*a,**k):
    def decorator(fn): return fn
    return decorator
st.cache_data = passthrough

from data.financials import bulk_fetch_universe, to_screener_df
import sys; sys.path.insert(0, 'pages')
# import helperów z 7_sp500.py jest możliwy tylko gdy nie odpalamy całej strony
# Pomijamy smoke test funkcji helper w izolacji (testujemy razem z UI w Task 4)
print('Helpers napisane — test integracyjny w Task 4')
"
```

- [ ] **Step 3: Commit**

```bash
git add pages/7_sp500.py
git commit -m "Add screener helpers to pages/7_sp500.py

_apply_screener_filters: 11 filtrów (6 main + 5 advanced) NaN-aware.
_format_screener_df: konwersja na display strings.
_render_screener_summary: 4 summary cards (count, med P/E, med ROE, top sektor).

Helpery page-local — nie wynoszone do components/ bo 8_gpw.py ma własne
warianty (currency PLN, bank handling).

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: Tab UI w 7_sp500.py (SP500)

**Files:**
- Modify: `pages/7_sp500.py:48-54` (st.tabs definicja)
- Modify: `pages/7_sp500.py:end-of-file` (przed render_footer)

- [ ] **Step 1: Rozszerz st.tabs z 6 na 7 elementów**

Edytuj linie tworzące taby:

```python
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Ranking momentum",
    "📉 Wykresy",
    "⚖️ Porownanie",
    "🧪 Backtest momentum",
    "💪 Relative Strength",
    "📊 Screening",      # NOWY tab 6 (przed Finanse)
    "💰 Finanse",
])
```

**Uwaga:** istniejące `with tab6:` (Finanse) trzeba przemienować na `with tab7:`. Sprawdź:

```bash
grep -n "with tab6:" pages/7_sp500.py
grep -n "with tab7:" pages/7_sp500.py
```

Tab6 obecnie = Finanse → przemianować na tab7. Tab6 nowy = Screening.

- [ ] **Step 2: Dodaj `with tab6: _screener_fragment()` przed obecnym tab6 (Finanse)**

Znajdź `# ========================== TAB 6: FINANSE ==========================` w pliku. PRZED tą sekcją dodaj:

```python
# ========================== TAB 6: SCREENING ==========================
with tab6:
    @st.fragment
    def _screener_fragment():
        from data.financials import bulk_fetch_universe, to_screener_df
        from data.sp500_universe import SP500_TOP100

        st.markdown("### Screening fundamentalny — top 100 S&P 500")
        st.caption(
            "Pełna tabela 11 wskaźników (P/E, ROE, EV/EBITDA, marże, FCF, "
            "div yield, target). Filtruj + sortuj wg kryteriów. "
            "Dane z yfinance, cache 24h."
        )

        # Bulk fetch (cached) — pierwsza ladowanie tabu 30-60s
        with st.spinner("Pobieram dane fundamentalne universe..."):
            bulk = bulk_fetch_universe(tuple(SP500_TOP100))
        df_full = to_screener_df(bulk)
        if df_full.empty:
            st.error("Nie udalo sie pobrac danych z yfinance. Sprobuj odswiezyc strone.")
            return

        if len(bulk) < len(SP500_TOP100) * 0.7:
            st.warning(
                f"⚠️ Pobrano dane dla {len(bulk)}/{len(SP500_TOP100)} spólek. "
                f"Yahoo Finance moze byc throttled. Sprobuj odswiezyc za chwile."
            )

        # 1. Filtry główne (6 w 3-col × 2-row)
        st.markdown("**Filtry główne**")
        col1, col2, col3 = st.columns(3)
        pe_max = col1.slider("P/E max", 5.0, 100.0, 25.0, step=1.0, key="sp_scr_pe")
        roe_min = col2.slider("ROE min (%)", 0, 50, 15, key="sp_scr_roe")
        ev_ebitda_max = col3.slider("EV/EBITDA max", 1.0, 60.0, 20.0, step=1.0, key="sp_scr_ev")

        col4, col5, col6 = st.columns(3)
        available_sectors = sorted([s for s in df_full["sector"].dropna().unique() if s])
        sectors_sel = col4.multiselect("Sektory", available_sectors, default=available_sectors, key="sp_scr_sec")
        cap_min_b = col5.number_input("Market cap min ($B)", 0.0, 5000.0, 10.0, step=5.0, key="sp_scr_cap")
        buy_only = col6.checkbox("Tylko BUY", value=False, key="sp_scr_buy",
                                  help="Tylko spółki z rekomendacją BUY/STRONG_BUY/OUTPERFORM")

        # 2. Expander zaawansowane (5 filtrów)
        with st.expander("Zaawansowane filtry", expanded=False):
            a1, a2, a3 = st.columns(3)
            div_yld_min = a1.slider("Div Yield min (%)", 0.0, 15.0, 0.0, key="sp_scr_div")
            rev_growth_min = a2.slider("Revenue Growth min (%)", -20, 100, -20, key="sp_scr_rev")
            debt_eq_max = a3.slider("Debt/E max", 0, 500, 500, key="sp_scr_de")
            a4, a5 = st.columns(2)
            profit_margin_min = a4.slider("Profit Margin min (%)", -20, 50, -20, key="sp_scr_pm")
            pb_max = a5.slider("P/B max", 0.0, 30.0, 30.0, step=0.5, key="sp_scr_pb")

        # 3. Aplikuj filtry
        df_filtered = _apply_screener_filters(
            df_full,
            pe_max=pe_max, roe_min_pct=roe_min, ev_ebitda_max=ev_ebitda_max,
            sectors=sectors_sel, cap_min_usd=cap_min_b * 1e9, buy_only=buy_only,
            div_yld_min_pct=div_yld_min, rev_growth_min_pct=rev_growth_min,
            debt_eq_max=debt_eq_max, profit_margin_min_pct=profit_margin_min, pb_max=pb_max,
        )

        if df_filtered.empty:
            st.info("Brak wyników po zastosowaniu filtrów. Spróbuj rozluźnić kryteria.")
            return

        # 4. Sort + Top N
        sort_options = {
            "ROE (desc)": ("roe", False),
            "P/E (asc, tańsze)": ("pe", True),
            "Forward P/E (asc)": ("fwd_pe", True),
            "EV/EBITDA (asc)": ("ev_ebitda", True),
            "Profit Margin (desc)": ("profit_margin", False),
            "Revenue Growth (desc)": ("revenue_growth", False),
            "Dividend Yield (desc)": ("dividend_yield", False),
            "Upside % (desc)": ("upside_pct", False),
            "Market Cap (desc)": ("market_cap", False),
        }
        s1, s2, s3 = st.columns([2, 1, 1])
        sort_label = s1.selectbox("Sortuj wg", list(sort_options.keys()), key="sp_scr_sort")
        sort_col, ascending = sort_options[sort_label]
        top_n_label = s2.selectbox("Top N", ["5", "10", "15", "25", "Wszystkie"], index=2, key="sp_scr_topn")
        s3.markdown(f"**Wyników:** {len(df_filtered)}/{len(df_full)}")

        df_sorted = df_filtered.sort_values(sort_col, ascending=ascending, na_position="last")
        if top_n_label != "Wszystkie":
            df_sorted = df_sorted.head(int(top_n_label))

        # 5. Summary cards
        _render_screener_summary(df_sorted, total=len(df_full))
        st.markdown("---")

        # 6. Tabela
        df_display = _format_screener_df(df_sorted, currency_sym="$")
        sel = st.dataframe(
            df_display, height=500, use_container_width=True,
            on_select="rerun", selection_mode="single-row",
        )
        if sel and hasattr(sel, "selection") and sel.selection.rows:
            clicked = df_display.index[sel.selection.rows[0]]
            st.session_state["sp_finanse_ticker"] = clicked
            st.info(f"✓ Wybrano **{clicked}** — przełącz na tab 💰 Finanse aby zobaczyć szczegóły")

        # 7. CSV export
        export_df = df_sorted.copy()
        export_df.index.name = "ticker"
        csv = export_df.to_csv()
        st.download_button("📥 Eksport CSV", csv, "sp500_screener.csv", "text/csv", key="sp_scr_csv")

        st.caption(
            "💡 Spółki z brakującym wskaźnikiem są odfiltrowane gdy filtr aktywny "
            "(np. spółka bez P/E nie pojawi się gdy P/E max < 100)."
        )

    _screener_fragment()
```

- [ ] **Step 3: Update istniejący `with tab6:` (Finanse) → `with tab7:`**

```bash
grep -n "with tab6:" pages/7_sp500.py | grep -i finans  # znajdź który tab6 to Finanse
# Następnie edytuj:
# # ========================== TAB 6: FINANSE  →  TAB 7: FINANSE
# with tab6:  →  with tab7:
```

Tylko **drugie** wystąpienie `with tab6:` (Finanse) → `with tab7:`. Pierwsze (Screening — przed) zostaje.

- [ ] **Step 4: Syntax check + uruchom Streamlit lokalnie**

```bash
venv/Scripts/python.exe -c "import py_compile; py_compile.compile('pages/7_sp500.py', doraise=True); print('OK')"
# Uruchom dashboard:
venv/Scripts/python.exe -m streamlit run app.py --server.headless true --server.port 8501 &
sleep 8
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8501/_stcore/health  # Expected: 200
```

Manual test w przeglądarce: otwórz http://localhost:8501, S&P 500, kliknij tab "📊 Screening". Sprawdź:
- Spinner przy pierwszym ładowaniu (30-60s)
- 6 filtrów widocznych, expander zaawansowane
- Tabela ~20-40 spółek z defaults
- Sort by ROE → AAPL/NVDA na górze
- Klik wiersza → toast "Wybrano X"

- [ ] **Step 5: Commit**

```bash
git add pages/7_sp500.py
git commit -m "Add Screener tab to pages/7_sp500.py

Nowy 6-ty tab \"📊 Screening\" (przed \"💰 Finanse\" które przesunąłem do tab7).
Filtry: 6 main (P/E, ROE, EV/EBITDA, Sektor, Cap, BUY) + 5 advanced
(Div Yld, Rev Growth, Debt/E, Profit Margin, P/B). Sort by + Top N.
Tabela 11 kolumn + 4 summary cards + CSV export. Klik wiersza → pre-fill
sp_finanse_ticker w session_state.

Reuses bulk_fetch_universe (cache 24h) dla SP500_TOP100 (100 spółek).

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: Tab UI w 8_gpw.py (GPW + bank handling)

**Files:**
- Modify: `pages/8_gpw.py:48-54` (st.tabs)
- Modify: `pages/8_gpw.py:end-of-file` (przed render_footer)

- [ ] **Step 1: Rozszerz st.tabs z 6 na 7 + przemianuj tab6→tab7 dla Finanse**

Identyczna procedura jak w Task 4 Step 1+3 ale dla `pages/8_gpw.py`.

- [ ] **Step 2: Dodaj helpery (analogiczne jak w 7_sp500) PLUS bank handling**

Skopiuj `_apply_screener_filters`, `_format_screener_df`, `_render_screener_summary` z 7_sp500 do 8_gpw (page-local). Modyfikacje:

**`_format_screener_df` dla GPW:**
```python
def _format_screener_df(df: pd.DataFrame) -> pd.DataFrame:
    """Format dla GPW: bank handling + PLN currency."""
    from data.financials import format_large_number
    from data.gpw_universe import GPW_BANKS
    out = df.copy()
    out["P/E"] = out["pe"].apply(lambda v: f"{v:.1f}" if pd.notna(v) else "—")
    out["Fwd P/E"] = out["fwd_pe"].apply(lambda v: f"{v:.1f}" if pd.notna(v) else "—")
    # Bank handling: EV/EBITDA = "N/A bank" zamiast "—"
    def _ev(idx, v):
        if idx in GPW_BANKS:
            return "N/A bank"
        return f"{v:.1f}" if pd.notna(v) else "—"
    out["EV/EBITDA"] = [_ev(idx, v) for idx, v in out["ev_ebitda"].items()]
    out["ROE"] = out["roe"].apply(lambda v: f"{v*100:.0f}%" if pd.notna(v) else "—")
    out["Marża"] = out["profit_margin"].apply(lambda v: f"{v*100:.1f}%" if pd.notna(v) else "—")
    out["Div Yld"] = out["dividend_yield"].apply(lambda v: f"{v:.2f}%" if pd.notna(v) else "—")
    out["Cap"] = out["market_cap"].apply(lambda v: f"zł{format_large_number(v)}" if pd.notna(v) else "—")
    out["Rev Gr."] = out["revenue_growth"].apply(lambda v: f"{v*100:+.1f}%" if pd.notna(v) else "—")
    out["Reco"] = out["recommendation_key"].fillna("").astype(str).str.upper().str.replace("_", " ")
    out["Nazwa"] = out["name"]
    out["Sektor"] = out["sector"].fillna("—")
    return out[["Nazwa", "Sektor", "P/E", "Fwd P/E", "EV/EBITDA", "ROE", "Marża",
                "Div Yld", "Rev Gr.", "Cap", "Reco"]]
```

`_apply_screener_filters` taki sam jak w 7_sp500 — wykluczenie NaN przez `fillna(np.inf)` automatycznie wyklucza banki gdy EV/EBITDA filter aktywny. Bez zmian.

- [ ] **Step 3: Dodaj `with tab6: _screener_fragment_gpw()` z GPW universe**

```python
# ========================== TAB 6: SCREENING ==========================
with tab6:
    @st.fragment
    def _screener_fragment_gpw():
        from data.financials import bulk_fetch_universe, to_screener_df
        from data.gpw_universe import GPW_CATEGORIES

        st.markdown("### Screening fundamentalny — WIG20 + mWIG40")
        st.caption(
            "Pełna tabela 11 wskaźników. Banki (PKO, PEO, SPL, MBK, BHW, BNP, "
            "MIL, ING, ALR) pokazują „N/A bank” w EV/EBITDA — nie raportują "
            "klasycznego EBITDA. Dane z yfinance, cache 24h."
        )

        gpw_screener_universe = list(GPW_CATEGORIES["WIG20"].keys()) + list(GPW_CATEGORIES["mWIG40"].keys())

        with st.spinner("Pobieram dane fundamentalne universe..."):
            bulk = bulk_fetch_universe(tuple(gpw_screener_universe))
        df_full = to_screener_df(bulk)
        if df_full.empty:
            st.error("Nie udalo sie pobrac danych z yfinance. Sprobuj odswiezyc strone.")
            return

        if len(bulk) < len(gpw_screener_universe) * 0.7:
            st.warning(
                f"⚠️ Pobrano dane dla {len(bulk)}/{len(gpw_screener_universe)} spólek. "
                f"yfinance ma dziury w pokryciu GPW — to normalne dla mniejszych spólek."
            )

        # Filtry główne (6) — analogicznie do SP500 ale z PLN i innymi defaultami
        st.markdown("**Filtry główne**")
        col1, col2, col3 = st.columns(3)
        pe_max = col1.slider("P/E max", 5.0, 100.0, 25.0, step=1.0, key="gpw_scr_pe")
        roe_min = col2.slider("ROE min (%)", 0, 50, 10, key="gpw_scr_roe")
        ev_ebitda_max = col3.slider("EV/EBITDA max", 1.0, 60.0, 20.0, step=1.0, key="gpw_scr_ev")

        col4, col5, col6 = st.columns(3)
        available_sectors = sorted([s for s in df_full["sector"].dropna().unique() if s])
        sectors_sel = col4.multiselect("Sektory", available_sectors, default=available_sectors, key="gpw_scr_sec")
        cap_min_pln = col5.number_input("Market cap min (mld zł)", 0.0, 500.0, 1.0, step=1.0, key="gpw_scr_cap")
        buy_only = col6.checkbox("Tylko BUY", value=False, key="gpw_scr_buy")

        with st.expander("Zaawansowane filtry", expanded=False):
            a1, a2, a3 = st.columns(3)
            div_yld_min = a1.slider("Div Yield min (%)", 0.0, 15.0, 0.0, key="gpw_scr_div")
            rev_growth_min = a2.slider("Revenue Growth min (%)", -20, 100, -20, key="gpw_scr_rev")
            debt_eq_max = a3.slider("Debt/E max", 0, 500, 500, key="gpw_scr_de")
            a4, a5 = st.columns(2)
            profit_margin_min = a4.slider("Profit Margin min (%)", -20, 50, -20, key="gpw_scr_pm")
            pb_max = a5.slider("P/B max", 0.0, 30.0, 30.0, step=0.5, key="gpw_scr_pb")

        df_filtered = _apply_screener_filters(
            df_full,
            pe_max=pe_max, roe_min_pct=roe_min, ev_ebitda_max=ev_ebitda_max,
            sectors=sectors_sel, cap_min_usd=cap_min_pln * 1e9, buy_only=buy_only,
            div_yld_min_pct=div_yld_min, rev_growth_min_pct=rev_growth_min,
            debt_eq_max=debt_eq_max, profit_margin_min_pct=profit_margin_min, pb_max=pb_max,
        )

        if df_filtered.empty:
            st.info("Brak wyników po zastosowaniu filtrów. Spróbuj rozluźnić kryteria.")
            return

        sort_options = {
            "ROE (desc)": ("roe", False),
            "P/E (asc, tańsze)": ("pe", True),
            "Forward P/E (asc)": ("fwd_pe", True),
            "EV/EBITDA (asc)": ("ev_ebitda", True),
            "Profit Margin (desc)": ("profit_margin", False),
            "Revenue Growth (desc)": ("revenue_growth", False),
            "Dividend Yield (desc)": ("dividend_yield", False),
            "Upside % (desc)": ("upside_pct", False),
            "Market Cap (desc)": ("market_cap", False),
        }
        s1, s2, s3 = st.columns([2, 1, 1])
        sort_label = s1.selectbox("Sortuj wg", list(sort_options.keys()), key="gpw_scr_sort")
        sort_col, ascending = sort_options[sort_label]
        top_n_label = s2.selectbox("Top N", ["5", "10", "15", "25", "Wszystkie"], index=2, key="gpw_scr_topn")
        s3.markdown(f"**Wyników:** {len(df_filtered)}/{len(df_full)}")

        df_sorted = df_filtered.sort_values(sort_col, ascending=ascending, na_position="last")
        if top_n_label != "Wszystkie":
            df_sorted = df_sorted.head(int(top_n_label))

        _render_screener_summary(df_sorted, total=len(df_full))
        st.markdown("---")

        df_display = _format_screener_df(df_sorted)
        sel = st.dataframe(
            df_display, height=500, use_container_width=True,
            on_select="rerun", selection_mode="single-row",
        )
        if sel and hasattr(sel, "selection") and sel.selection.rows:
            clicked = df_display.index[sel.selection.rows[0]]
            st.session_state["gpw_finanse_ticker"] = clicked
            st.info(f"✓ Wybrano **{clicked}** — przełącz na tab 💰 Finanse aby zobaczyć szczegóły")

        export_df = df_sorted.copy()
        export_df.index.name = "ticker"
        csv = export_df.to_csv()
        st.download_button("📥 Eksport CSV", csv, "gpw_screener.csv", "text/csv", key="gpw_scr_csv")

        st.caption(
            "💡 Spółki z brakującym wskaźnikiem są odfiltrowane gdy filtr aktywny."
        )
        st.caption(
            "🏦 Banki nie raportują klasycznego EBITDA — kolumna EV/EBITDA pokazuje "
            "„N/A bank”. Filtr EV/EBITDA max wyklucza banki z tabeli."
        )

    _screener_fragment_gpw()
```

- [ ] **Step 4: Syntax + manual test**

```bash
venv/Scripts/python.exe -c "import py_compile; py_compile.compile('pages/8_gpw.py', doraise=True); print('OK')"
```

Streamlit już działa (uruchomiony w Task 4) — odśwież przeglądarkę → GPW → tab "📊 Screening".

Manual test:
- PKN.WA, CDR.WA, ALE.WA widoczne z pełnymi danymi
- PKO.WA / PEO.WA / SPL.WA / MBK.WA pokazują "N/A bank" w EV/EBITDA
- Sort by ROE → ALE, CDR, DNP top
- Cap min 5 mld zł filter działa (zł zamiast $)
- Filter EV/EBITDA max 15 → banki znikają

- [ ] **Step 5: Commit**

```bash
git add pages/8_gpw.py
git commit -m "Add Screener tab to pages/8_gpw.py

Analogicznie do 7_sp500 + GPW edge cases:
- Currency display: 'zł' zamiast '\$' w cap slider + market_cap column
- Bank handling: EV/EBITDA pokazuje 'N/A bank' dla GPW_BANKS (PKO/PEO/SPL/MBK/BHW/BNP/MIL/ING/ALR)
- Universe: WIG20 + mWIG40 (60 spółek z GPW_CATEGORIES)
- Default cap min: 1 mld zł (mniejsze niż \$10B dla SP500)
- ROE min default: 10% (niższe niż 15% dla SP500 — polskie spółki niższe marże)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: Update CLAUDE.md + smoke test + push

**Files:**
- Modify: `CLAUDE.md` (dodać sekcję Screener F12)

- [ ] **Step 1: Update tabs count w CLAUDE.md**

W `CLAUDE.md` znajdź linie:
```
7_sp500.py            # S&P 500 US stocks (6 tabs: ranking, wykresy, porownanie+stats, backtest, RS, finanse)
8_gpw.py              # Polish stocks GPW (6 tabs: ...)
```

Zmień `6 tabs` → `7 tabs`, dodaj `screening` w opisie:
```
7_sp500.py            # S&P 500 US stocks (7 tabs: ranking, wykresy, porownanie+stats, backtest, RS, screening, finanse)
8_gpw.py              # Polish stocks GPW (7 tabs: ranking, wykresy, porownanie+stats incl. WIG20/mWIG40/sWIG80, backtest, RS, screening, finanse)
```

- [ ] **Step 2: Dodaj sekcję Screener F12 w design decisions**

Po sekcji `Finanse tab (F11)` (linia z `data/financials.py`) dodaj:

```markdown
- **Screener Fundamentalny (F12):** 6-ty tab `📊 Screening` (przed `💰 Finanse`) w pages 7_sp500 + 8_gpw. Pełna tabela 11 wskaźników dla subset universe (SP500_TOP100 / WIG20+mWIG40 = ~160 spółek). Filtry: 6 main (P/E max, ROE min, EV/EBITDA max, sektor, cap min, BUY only) + 5 advanced (div yield, rev growth, debt/E, profit margin, P/B). Sort by 9 wskaźników (ascending/descending properly per metric). Top N: 5/10/15/25/all. 4 summary cards + CSV export. Klik wiersza → pre-fill `sp_finanse_ticker` / `gpw_finanse_ticker`. Reuses `bulk_fetch_universe()` w `data/financials.py` (cache 24h, reuses `_fetch_info` per ticker). GPW edge case: kolumna EV/EBITDA pokazuje "N/A bank" dla GPW_BANKS. Spec: `docs/superpowers/specs/2026-05-18-screener-fundamentalny-design.md`.
- **SP500_TOP100:** statyczna lista 100 spółek by market cap w `data/sp500_universe.py`. Refresh raz na 6 miesięcy (Q1 + Q3 results). Last verified: 2026-05-18.
```

- [ ] **Step 3: Smoke test pełen pipeline lokalnie**

```bash
venv/Scripts/python.exe -m streamlit run app.py --server.headless true --server.port 8501 &
sleep 8
```

Otwórz http://localhost:8501. Test:
1. **S&P 500 → 📊 Screening** → defaults → ~20-40 spółek → sort by ROE → AAPL/NVDA/MSFT top
2. **GPW → 📊 Screening** → defaults → ~15-25 spółek → PKO/PEO widoczne z "N/A bank"
3. Klik wiersza w SP500 Screening → toast → przełącz na Finanse → widzisz wybraną spółkę
4. CSV export → plik pobierany, UTF-8 OK
5. Mobile test (DevTools Toggle device toolbar 375px) — tabela scrolluje się horyzontalnie

- [ ] **Step 4: Commit CLAUDE.md + push wszystkiego**

```bash
git add CLAUDE.md
git commit -m "Update CLAUDE.md — Screener Fundamentalny feature (F12)

Sekcja design decisions + tabs count update (6→7) dla pages 7+8.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"

# Push all 5 commits do Streamlit Cloud auto-deploy
git push origin main
```

Spodziewane push commits (od spec'a do CLAUDE.md):
1. `e941428` — Add design spec
2. `<hash>` — SP500_TOP100
3. `<hash>` — bulk_fetch_universe + to_screener_df
4. `<hash>` — Screener helpers w 7_sp500
5. `<hash>` — Screener tab w 7_sp500
6. `<hash>` — Screener tab w 8_gpw
7. `<hash>` — CLAUDE.md update

- [ ] **Step 5: Verify Streamlit Cloud deploy**

```bash
sleep 180  # 3 min for auto-redeploy
/d/ICT/freqtrade/.venv/Scripts/python.exe -c "
import urllib.request
r = urllib.request.urlopen('https://gem-dashboard.streamlit.app/_stcore/health', timeout=15)
print(f'health: {r.status}')
"
```

Production check: otwórz https://gem-dashboard.streamlit.app/ → S&P 500 → Screening (po obudzeniu app jeśli hibernated).

---

## Self-Review

### Spec coverage check

- ✅ **Tab placement** (7-my, przed Finanse) → Task 4 Step 1, Task 5 Step 1
- ✅ **6 filtrów głównych** (P/E, ROE, EV/EBITDA, Sektor, Cap, BUY) → Task 4 Step 2, Task 5 Step 3
- ✅ **5 zaawansowanych** (Div Yld, Rev Growth, Debt/E, Profit Margin, P/B) → Task 4/5 Step 2/3 (expander)
- ✅ **Sort by 9 wskaźników** + ascending properly per metric → Task 4/5 `sort_options` dict
- ✅ **Top N 5/10/15/25/all** → Task 4/5 (`top_n_label` selectbox)
- ✅ **Bulk fetch + cache** → Task 2 (`bulk_fetch_universe`)
- ✅ **Pochodne pola** (upside_pct, is_buy) → Task 2 (`to_screener_df`)
- ✅ **GPW bank handling** ("N/A bank") → Task 5 Step 2 (`_format_screener_df`)
- ✅ **Currency display** (PLN dla GPW, USD dla SP500) → Task 4/5 (`format_large_number` z prefix `currency_sym`)
- ✅ **Summary cards** (count, med P/E, med ROE, top sektor) → Task 3 (`_render_screener_summary`)
- ✅ **CSV export** → Task 4/5 Step 2/3 (`st.download_button`)
- ✅ **Pre-fill Finanse tab** → Task 4/5 (`sel.selection.rows` → session_state)
- ✅ **Universe SP100 + WIG20+mWIG40** → Task 1, Task 5
- ✅ **Error handling** (<70% pokrycie warning, empty filter info) → Task 4/5 Step 2/3
- ✅ **UX hints** (caption pod tabelą) → Task 4/5 ostatnie linie fragmentu

### Placeholder scan

- ✅ Brak TBD/TODO w treści tasków
- ✅ Każdy step ma konkretny kod lub komendę
- ✅ Importy w kodzie — wymienione explicit (`from data.financials import ...`)

### Type consistency

- `bulk_fetch_universe(_tickers_tuple: tuple[str, ...])` — Task 2 deklaracja, Task 4/5 wywołanie `tuple(SP500_TOP100)` ✓
- `to_screener_df(bulk: dict)` → `pd.DataFrame` — Task 2/4/5 spójne ✓
- `_apply_screener_filters(df, *, pe_max, ...)` keyword args — Task 3 deklaracja, Task 4 wywołanie spójne ✓
- Session state keys: `sp_finanse_ticker`, `gpw_finanse_ticker` — match z poprzednim feature (commit a5924f0) ✓
- Tab indexing: tab6 = Screening, tab7 = Finanse — spójne w obu pages (Task 4/5 Step 1+3) ✓

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-18-screener-fundamentalny.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — dispatch fresh subagent per task, review między taskami, fast iteration. Pasuje gdy każdy task ma jasne acceptance criteria (tu: smoke tests są klarowne).

**2. Inline Execution** — execute tasks w tej sesji używając executing-plans, batch execution z checkpoints. Pasuje gdy chcesz aktywnego nadzoru.

**Który approach?**
