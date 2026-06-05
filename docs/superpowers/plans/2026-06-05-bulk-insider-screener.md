# Bulk Insider Screener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nowa strona `pages/23_insider_screener.py` (page 23) — bulk screener insider activity dla SP500 (456 spółek): top buyers/sellers w 6 mc, sektorowa heatmapa, tabela z filtrami, cross-link do F13 deep dive Insiders.

**Architecture:** Rozszerzenie `data/financials.py` o 3 funkcje (`_compute_buy_streak`, `_aggregate_insider_for_ticker`, `bulk_fetch_insider_screener`). Reuse F15 (`fetch_insider_transactions` + `fetch_institutional_holders` z fallback chain `_try_insider_endpoint`), F11 (`get_ratios_snapshot`), F14 (`_get_etf_set` filter, cross-link pattern). Nowa strona z layoutem wzorowanym na F14 (filtry + summary + bar charts + tabela + heatmapa + cross-link + CSV).

**Tech Stack:** Streamlit 1.55+, yfinance 0.2.50+, pandas 2.0+ (`DataFrame.map` nie `applymap`), plotly 5.18+. ThreadPool 8 workers + `@st.cache_data(ttl=86400)` per ticker + per universe.

**Reference:** Spec `docs/superpowers/specs/2026-06-05-bulk-insider-screener-design.md` (commit `1922f7d`).

---

## File Structure

**Tworzymy:**
- `pages/23_insider_screener.py` (~250 LOC) — UI strony

**Modyfikujemy:**
- `data/financials.py` — +3 funkcje `_compute_buy_streak`, `_aggregate_insider_for_ticker`, `bulk_fetch_insider_screener` (~150 LOC)
- `tests/test_financials.py` — +6 testów mock-based
- `components/auth.py` — `PAGE_INFO[23]`
- `app.py` — karta page 23 w gridzie
- `CLAUDE.md` — Pages structure + F16 paragraph

**Bez nowych plików** — wszystko jako rozszerzenie istniejących modułów.

**Bez zmian:**
- `pages/7_sp500.py`, `pages/8_gpw.py`, `pages/22_earnings_calendar.py` — F13/F14/F15 reagują na session_state pre-set (już działa)
- `components/financials_ui.py` — F15 deep dive Insiders bez zmian
- `components/watchlist.py` — F14 (watchlist nie używany w F16 MVP, v2)

---

## Task 1: `_compute_buy_streak` helper

**Files:**
- Modify: `data/financials.py` (dopisać na końcu po `fetch_major_holders`)
- Modify: `tests/test_financials.py` (dopisać 3 testy)

- [ ] **Step 1.1: Dopisać 3 testy do `tests/test_financials.py`**

Otwórz `tests/test_financials.py` i dopisz na końcu:

```python


def test_compute_buy_streak_full_buys():
    """Wszystkie 6 ostatnich miesięcy buy > sell → streak 6."""
    df = pd.DataFrame({
        "Type": ["Buy"] * 6,
        "Value": [1_000_000] * 6,
    }, index=pd.to_datetime([
        "2026-05-15", "2026-04-15", "2026-03-15",
        "2026-02-15", "2026-01-15", "2025-12-15",
    ]))
    from data.financials import _compute_buy_streak
    assert _compute_buy_streak(df) == 6


def test_compute_buy_streak_breaks_on_sell_month():
    """Ostatnie 2 buy, potem sell — streak 2."""
    df = pd.DataFrame({
        "Type": ["Buy", "Buy", "Sell"],
        "Value": [1_000_000, 1_000_000, 5_000_000],
    }, index=pd.to_datetime(["2026-05-15", "2026-04-15", "2026-03-15"]))
    from data.financials import _compute_buy_streak
    assert _compute_buy_streak(df) == 2


def test_compute_buy_streak_empty():
    from data.financials import _compute_buy_streak
    assert _compute_buy_streak(pd.DataFrame()) == 0
```

- [ ] **Step 1.2: Run tests — verify FAIL**

```bash
cd C:\Users\m4x\Desktop\AI\gem-dashboard
./venv/Scripts/python.exe -m pytest tests/test_financials.py -v -k compute_buy_streak
```

Expected: 3 FAIL z `ImportError: cannot import name '_compute_buy_streak'`.

- [ ] **Step 1.3: Implementacja w `data/financials.py`**

Sprawdź gdzie kończy się plik:

```bash
tail -5 data/financials.py
```

Powinno być na końcu `fetch_major_holders` (zwraca dict). Dopisz po niej:

```python


# ---------------------------------------------------------------------------
# Bulk Insider Screener (F16)
# ---------------------------------------------------------------------------

def _compute_buy_streak(transactions: pd.DataFrame) -> int:
    """Liczy kolejne ostatnie miesiące gdzie buy_value > sell_value.

    Iteruje od najnowszego miesiąca wstecz. Stop na pierwszym miesiącu
    gdzie buy <= sell. Max 6 miesięcy.

    Exercise/Conversion ignorowane (informacyjne, nie wpływają).

    Returns: int 0-6.
    """
    if transactions is None or transactions.empty:
        return 0
    if "Type" not in transactions.columns or "Value" not in transactions.columns:
        return 0

    df = transactions.copy()
    df["_yearmonth"] = pd.to_datetime(df.index).to_period("M")
    months_sorted = sorted(df["_yearmonth"].unique(), reverse=True)

    streak = 0
    for ym in months_sorted[:6]:
        month_df = df[df["_yearmonth"] == ym]
        buy = float(month_df[month_df["Type"] == "Buy"]["Value"].sum())
        sell = float(month_df[month_df["Type"] == "Sell"]["Value"].sum())
        if buy > sell:
            streak += 1
        else:
            break
    return streak
```

- [ ] **Step 1.4: Run tests — verify PASS**

```bash
./venv/Scripts/python.exe -m pytest tests/test_financials.py -v -k compute_buy_streak
```

Expected: 3 PASS.

- [ ] **Step 1.5: Regression check**

```bash
./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```

Expected: 49/49 PASS (46 dotychczasowych + 3 nowe).

- [ ] **Step 1.6: Commit**

```bash
git add data/financials.py tests/test_financials.py
git commit -m "Add _compute_buy_streak helper (kolejne miesiace buy > sell, 0-6)"
```

---

## Task 2: `_aggregate_insider_for_ticker`

**Files:**
- Modify: `data/financials.py` (dopisać po `_compute_buy_streak`)
- Modify: `tests/test_financials.py` (dopisać 2 testy)

- [ ] **Step 2.1: Dopisać 2 testy**

Dopisz na końcu `tests/test_financials.py`:

```python


def test_aggregate_insider_for_ticker_full_data():
    """Mock 3 endpoint — transactions + institutional + ratios."""
    mock_transactions = pd.DataFrame({
        "Insider": ["TIM COOK", "LUCA MAESTRI", "ELON MUSK"],
        "Position": ["CEO", "CFO", "Other"],
        "Type": ["Buy", "Sell", "Buy"],
        "Shares": [5000, 10000, 3000],
        "Value": [1_000_000, 2_000_000, 600_000],
    }, index=pd.to_datetime(["2026-05-15", "2026-04-20", "2026-03-10"]))

    mock_institutional = pd.DataFrame({
        "Holder": ["Vanguard Group Inc", "BlackRock Inc."],
        "% Out": [8.2, 6.5],
        "Shares": [1_300_000_000, 1_000_000_000],
    })

    from data.financials import _aggregate_insider_for_ticker
    with patch("data.financials.fetch_insider_transactions", return_value=mock_transactions), \
         patch("data.financials.fetch_institutional_holders", return_value=mock_institutional), \
         patch("data.financials.get_ratios_snapshot", return_value={
             "name": "Apple Inc.",
             "sector": "Information Technology",
             "market_cap": 3_400_000_000_000,
         }):
        result = _aggregate_insider_for_ticker("AAPL")

    assert result is not None
    assert result["ticker"] == "AAPL"
    # Net: 1.6M buy - 2M sell = -400k
    assert result["net_value_6m"] == -400_000
    assert result["n_buys"] == 2
    assert result["n_sells"] == 1
    assert result["top_buyer"] == "TIM COOK"  # 1M > 600k
    assert result["top_seller"] == "LUCA MAESTRI"
    assert result["top_institutional"] == "Vanguard Group Inc"
    # net < 0 ale n_sells = 1 (< 2) → 🟡 mixed
    assert result["sentiment"] == "🟡"


def test_aggregate_insider_returns_none_when_no_data():
    """Wszystkie 3 fetch None → return None."""
    from data.financials import _aggregate_insider_for_ticker
    with patch("data.financials.fetch_insider_transactions", return_value=None), \
         patch("data.financials.fetch_institutional_holders", return_value=None), \
         patch("data.financials.get_ratios_snapshot", return_value=None):
        result = _aggregate_insider_for_ticker("EMPTY_TEST")
    assert result is None
```

- [ ] **Step 2.2: Verify FAIL**

```bash
./venv/Scripts/python.exe -m pytest tests/test_financials.py -v -k aggregate_insider
```

Expected: 2 FAIL z `ImportError: cannot import name '_aggregate_insider_for_ticker'`.

- [ ] **Step 2.3: Implementacja w `data/financials.py`**

Dopisz po `_compute_buy_streak`:

```python


def _aggregate_insider_for_ticker(ticker: str) -> dict | None:
    """Agregat insider activity dla 1 tickera.

    Pobiera (z fallback chain F15):
    - fetch_insider_transactions (6mc historia)
    - fetch_institutional_holders (top 10 fundusz)
    - get_ratios_snapshot (sektor + market_cap z Ticker.info, F11)

    Returns dict z 16 polami lub None gdy oba endpointy puste.

    Fallback sektor + nazwa: jesli ratios None, uzywamy SP500_SECTOR_MAP
    + SP500_NAMES (static).

    Sentiment:
    - 🟢 net > 0 i n_buys >= 2
    - 🔴 net < 0 i n_sells >= 2
    - 🟡 mixed (jedna transakcja lub net mieszany)
    - ⚪ brak danych
    """
    transactions = fetch_insider_transactions(ticker)
    institutional = fetch_institutional_holders(ticker)
    ratios = get_ratios_snapshot(ticker)

    # Fallback sektor + nazwa
    sector = None
    name = None
    market_cap = None
    if ratios is not None:
        sector = ratios.get("sector")
        name = ratios.get("name")
        market_cap = ratios.get("market_cap")
    if not sector:
        from data.sp500_universe import SP500_SECTOR_MAP, SP500_NAMES
        sector = SP500_SECTOR_MAP.get(ticker, "—")
        if not name:
            name = SP500_NAMES.get(ticker, ticker)

    row = {
        "ticker": ticker,
        "name": name or ticker,
        "sector": sector,
        "market_cap": market_cap,
        "net_value_6m": float("nan"),
        "n_buys": 0,
        "n_sells": 0,
        "avg_buy_size": float("nan"),
        "avg_sell_size": float("nan"),
        "top_buyer": "—",
        "top_buyer_value": float("nan"),
        "top_seller": "—",
        "top_seller_value": float("nan"),
        "top_institutional": "—",
        "top_inst_pct": float("nan"),
        "sentiment": "⚪",
        "beat_streak_buys": 0,
    }

    # Insider transactions agregat
    if transactions is not None and not transactions.empty and "Type" in transactions.columns:
        buys = transactions[transactions["Type"] == "Buy"]
        sells = transactions[transactions["Type"] == "Sell"]
        buy_value = float(buys["Value"].sum()) if "Value" in buys.columns else 0.0
        sell_value = float(sells["Value"].sum()) if "Value" in sells.columns else 0.0
        net = buy_value - sell_value
        row["net_value_6m"] = net
        row["n_buys"] = len(buys)
        row["n_sells"] = len(sells)
        row["avg_buy_size"] = float(buys["Value"].mean()) if len(buys) > 0 else float("nan")
        row["avg_sell_size"] = float(sells["Value"].mean()) if len(sells) > 0 else float("nan")

        if len(buys) > 0:
            top_b = buys.nlargest(1, "Value").iloc[0]
            row["top_buyer"] = str(top_b.get("Insider", "—"))[:40]
            row["top_buyer_value"] = float(top_b.get("Value", 0))
        if len(sells) > 0:
            top_s = sells.nlargest(1, "Value").iloc[0]
            row["top_seller"] = str(top_s.get("Insider", "—"))[:40]
            row["top_seller_value"] = float(top_s.get("Value", 0))

        if pd.notna(net):
            if net > 0 and row["n_buys"] >= 2:
                row["sentiment"] = "🟢"
            elif net < 0 and row["n_sells"] >= 2:
                row["sentiment"] = "🔴"
            else:
                row["sentiment"] = "🟡"

        row["beat_streak_buys"] = _compute_buy_streak(transactions)

    # Institutional top fund
    if institutional is not None and not institutional.empty:
        if "Holder" in institutional.columns and "% Out" in institutional.columns:
            top_inst = institutional.iloc[0]
            row["top_institutional"] = str(top_inst.get("Holder", "—"))[:40]
            try:
                row["top_inst_pct"] = float(top_inst.get("% Out", float("nan")))
            except Exception:
                pass

    # Jesli wszystko None → return None
    if (transactions is None or transactions.empty) and \
       (institutional is None or institutional.empty):
        return None

    return row
```

- [ ] **Step 2.4: Run tests — verify PASS**

```bash
./venv/Scripts/python.exe -m pytest tests/test_financials.py -v -k aggregate_insider
```

Expected: 2 PASS.

- [ ] **Step 2.5: Regression check**

```bash
./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```

Expected: 51/51 PASS.

- [ ] **Step 2.6: Commit**

```bash
git add data/financials.py tests/test_financials.py
git commit -m "Add _aggregate_insider_for_ticker (16 pol agregat, fallback sektor+name)"
```

---

## Task 3: `bulk_fetch_insider_screener` z ETF filter

**Files:**
- Modify: `data/financials.py` (dopisać po `_aggregate_insider_for_ticker`)
- Modify: `tests/test_financials.py` (dopisać 1 test)

- [ ] **Step 3.1: Dopisać test ETF filter**

```python


def test_bulk_fetch_insider_screener_filters_etf():
    """ETF nie powinny byc fetchowane (no insider data)."""
    fetch_calls = []

    def mock_agg(ticker):
        fetch_calls.append(ticker)
        return {
            "ticker": ticker, "name": ticker, "sector": "—", "market_cap": None,
            "net_value_6m": 1_000_000, "n_buys": 1, "n_sells": 0,
            "avg_buy_size": float("nan"), "avg_sell_size": float("nan"),
            "top_buyer": "—", "top_buyer_value": float("nan"),
            "top_seller": "—", "top_seller_value": float("nan"),
            "top_institutional": "—", "top_inst_pct": float("nan"),
            "sentiment": "🟢", "beat_streak_buys": 0,
        }

    mock_progress = MagicMock()
    mock_progress.progress = MagicMock()
    mock_progress.empty = MagicMock()

    from data.financials import bulk_fetch_insider_screener
    with patch("data.financials._aggregate_insider_for_ticker", side_effect=mock_agg), \
         patch("data.financials.st.progress", return_value=mock_progress):
        result = bulk_fetch_insider_screener(("AAPL", "VOO", "MSFT", "QQQ"))

    # ETF (VOO, QQQ) filtered out
    assert "VOO" not in fetch_calls
    assert "QQQ" not in fetch_calls
    assert "AAPL" in fetch_calls
    assert "MSFT" in fetch_calls
    assert len(result) == 2
```

- [ ] **Step 3.2: Verify FAIL**

```bash
./venv/Scripts/python.exe -m pytest tests/test_financials.py -v -k bulk_fetch_insider_screener
```

Expected: 1 FAIL z `ImportError: cannot import name 'bulk_fetch_insider_screener'`.

- [ ] **Step 3.3: Implementacja w `data/financials.py`**

Dopisz po `_aggregate_insider_for_ticker`:

```python


@st.cache_data(ttl=86400, show_spinner="Pobieram bulk insider screener (~5-7 min cold cache)...")
def bulk_fetch_insider_screener(
    tickers_tuple: tuple[str, ...],
    max_workers: int = 8,
) -> pd.DataFrame:
    """Bulk insider screener — agregat per spolka z ThreadPool.

    Filtruje ETF (z _get_etf_set, F14 reuse).
    Default sort: net_value_6m DESC, NaN na koncu.

    Returns DataFrame 16-kolumnowy lub pusty.
    """
    etf_set = _get_etf_set()
    eligible = [t for t in tickers_tuple if t not in etf_set]

    rows: list[dict] = []
    total = len(eligible)
    progress_bar = st.progress(0.0, text=f"Pobieram 0/{total}...")
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(_aggregate_insider_for_ticker, t): t
            for t in eligible
        }
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                row = future.result()
            except Exception:
                row = None
            if row is not None:
                rows.append(row)
            completed += 1
            progress_bar.progress(
                completed / total,
                text=f"Pobieram {completed}/{total}: {ticker}",
            )

    progress_bar.empty()

    if not rows:
        return pd.DataFrame(columns=[
            "ticker", "name", "sector", "market_cap", "net_value_6m",
            "n_buys", "n_sells", "avg_buy_size", "avg_sell_size",
            "top_buyer", "top_buyer_value", "top_seller", "top_seller_value",
            "top_institutional", "top_inst_pct", "sentiment", "beat_streak_buys",
        ])

    df = pd.DataFrame(rows)
    df = df.sort_values(by="net_value_6m", ascending=False, na_position="last").reset_index(drop=True)
    return df
```

- [ ] **Step 3.4: Run tests + regression**

```bash
./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```

Expected: 52/52 PASS.

- [ ] **Step 3.5: Commit**

```bash
git add data/financials.py tests/test_financials.py
git commit -m "Add bulk_fetch_insider_screener (ThreadPool 8 + filter ETF + cache 24h)"
```

---

## Task 4: Page skeleton `pages/23_insider_screener.py`

**Files:**
- Create: `pages/23_insider_screener.py`

- [ ] **Step 4.1: Utworzyć plik z konfiguracją + filtrami + summary**

```python
"""Strona 23: Bulk Insider Screener.

Bulk insider activity dla SP500 (456 spolek). Window: 6 mc.
ETF wykluczone (no insider data). GPW pominiete (yfinance brak SEC Form 4).

Spec: docs/superpowers/specs/2026-06-05-bulk-insider-screener-design.md
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.auth import require_premium
from components.formatting import GOLD, GREEN, RED
from components.sidebar import setup_sidebar, render_footer
from data.financials import (
    bulk_fetch_insider_screener,
    format_large_number,
)
from data.sp500_universe import ALL_SP500_TICKERS


# ---------------------------------------------------------------------------
# Page config + auth + sidebar
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Insider Screener",
    page_icon="👥",
    layout="wide",
)
setup_sidebar()
if not require_premium(23):
    st.stop()

st.markdown("# 👥 Bulk Insider Screener")
st.caption(
    "Bulk insider activity dla SP500 (456 spolek). "
    "Window: ostatnie 6 mc. ETF wykluczone (no insider data). "
    "GPW pominiete (yfinance nie ma SEC Form 4 dla PL)."
)

# ---------------------------------------------------------------------------
# BULK FETCH (cache 24h, cold cache ~5-7 min)
# ---------------------------------------------------------------------------

universe = tuple(ALL_SP500_TICKERS)
df = bulk_fetch_insider_screener(universe)

if df.empty:
    st.warning(
        "Brak danych insider — yfinance moze byc globalnie blocked dla "
        "insider endpointow. Sprobuj ponownie za kilka minut (cache 24h)."
    )
    render_footer()
    st.stop()

# ---------------------------------------------------------------------------
# FILTRY (expander)
# ---------------------------------------------------------------------------

with st.expander("Filtry", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        sector_options = sorted(set(df["sector"].dropna()))
        sector_filter = st.multiselect(
            "Sektor",
            options=sector_options,
            default=[],
            key="insider_screener_sector",
        )
        status_filter = st.radio(
            "Status",
            ["Wszystkie", "Net Buyers 🟢", "Net Sellers 🔴", "Mixed 🟡"],
            horizontal=True, key="insider_screener_status",
        )
    with c2:
        min_net_value = st.number_input(
            "Min |Net Value| ($)",
            min_value=0, value=0, step=100_000,
            help="Filter abs(net_value_6m). 0 = bez filtra.",
            key="insider_screener_min_net",
        )
        min_streak = st.slider(
            "Min beat streak (mc 0-6)", 0, 6, 0,
            key="insider_screener_min_streak",
        )
    with c3:
        cap_options = [
            ("Brak", 0),
            ("$1B+", 1e9),
            ("$10B+", 10e9),
            ("$100B+", 100e9),
            ("$1T+", 1e12),
        ]
        min_cap_choice = st.selectbox(
            "Min Market Cap",
            options=cap_options,
            format_func=lambda x: x[0],
            key="insider_screener_min_cap",
        )
        sort_by = st.selectbox(
            "Sort by",
            options=[
                "net_value_6m DESC", "net_value_6m ASC",
                "n_buys DESC", "n_sells DESC",
                "beat_streak_buys DESC", "market_cap DESC",
                "top_inst_pct DESC", "avg_buy_size DESC", "ticker A-Z",
            ],
            key="insider_screener_sort",
        )
        top_n = st.selectbox(
            "Top N", [10, 25, 50, 100, 250], index=2,
            key="insider_screener_top_n",
        )
        if st.button("🔄 Refresh cache", key="insider_screener_refresh"):
            st.cache_data.clear()
            st.rerun()

# ---------------------------------------------------------------------------
# APPLY FILTRY
# ---------------------------------------------------------------------------

filtered = df.copy()
if sector_filter:
    filtered = filtered[filtered["sector"].isin(sector_filter)]
if status_filter == "Net Buyers 🟢":
    filtered = filtered[filtered["sentiment"] == "🟢"]
elif status_filter == "Net Sellers 🔴":
    filtered = filtered[filtered["sentiment"] == "🔴"]
elif status_filter == "Mixed 🟡":
    filtered = filtered[filtered["sentiment"] == "🟡"]
if min_net_value > 0:
    filtered = filtered[filtered["net_value_6m"].abs() >= min_net_value]
if min_streak > 0:
    filtered = filtered[filtered["beat_streak_buys"] >= min_streak]
if min_cap_choice[1] > 0:
    filtered = filtered[filtered["market_cap"].fillna(0) >= min_cap_choice[1]]

# Sort
if sort_by.endswith("DESC"):
    col = sort_by.replace(" DESC", "")
    filtered = filtered.sort_values(by=col, ascending=False, na_position="last")
elif sort_by.endswith("ASC"):
    col = sort_by.replace(" ASC", "")
    filtered = filtered.sort_values(by=col, ascending=True, na_position="last")
elif sort_by == "ticker A-Z":
    filtered = filtered.sort_values(by="ticker")

# ---------------------------------------------------------------------------
# SUMMARY (4 metric cards)
# ---------------------------------------------------------------------------

total_with_data = len(df)
n_net_buyers = int((df["sentiment"] == "🟢").sum())
n_net_sellers = int((df["sentiment"] == "🔴").sum())
avg_net = df["net_value_6m"].mean()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Spolek z danymi", f"{total_with_data}/456")
c2.metric(
    "Net Buyers 🟢", f"{n_net_buyers}",
    f"{n_net_buyers / total_with_data * 100:.0f}%" if total_with_data else "",
)
c3.metric("Net Sellers 🔴", f"{n_net_sellers}")
c4.metric("Avg Net 6mc", format_large_number(avg_net) if pd.notna(avg_net) else "—")

st.markdown("---")

# Placeholder dla Task 5 (top movers) i Task 6 (tabela) i Task 7 (heatmapa) i Task 8 (cross-link + CSV)
st.info("🚧 Top movers, tabela, heatmapa, cross-link i CSV dodane w kolejnych taskach.")

render_footer()
```

- [ ] **Step 4.2: Syntax check**

```bash
./venv/Scripts/python.exe -c "
import ast
with open('pages/23_insider_screener.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('Syntax OK')
"
```

Expected: `Syntax OK`.

- [ ] **Step 4.3: Regression check**

```bash
./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```

Expected: 52/52 PASS.

- [ ] **Step 4.4: Commit**

```bash
git add pages/23_insider_screener.py
git commit -m "Add pages/23_insider_screener.py skeleton (config + filtry + summary + bulk fetch)"
```

---

## Task 5: Top Buyers + Top Sellers bar charts

**Files:**
- Modify: `pages/23_insider_screener.py`

- [ ] **Step 5.1: Zamień placeholder na sekcję Top movers**

Znajdź `st.info("🚧 Top movers...")` i zamień na:

```python
# ---------------------------------------------------------------------------
# SEKCJA 1: Top Buyers + Top Sellers (2 bar charts side-by-side)
# ---------------------------------------------------------------------------

st.markdown("### 📈 Top movers")
col_b, col_s = st.columns(2)

with col_b:
    top_buyers = filtered.nlargest(10, "net_value_6m")
    if not top_buyers.empty and top_buyers["net_value_6m"].max() > 0:
        labels_b = [
            f"{t} — {n[:25]}"
            for t, n in zip(top_buyers["ticker"], top_buyers["name"])
        ]
        fig_b = go.Figure(go.Bar(
            x=top_buyers["net_value_6m"],
            y=labels_b,
            orientation="h",
            marker_color=GREEN,
            text=[format_large_number(v) for v in top_buyers["net_value_6m"]],
            textposition="outside",
        ))
        fig_b.update_layout(
            title="Top 10 Net Buyers (6 mc)",
            template="plotly_dark",
            height=380,
            yaxis=dict(autorange="reversed"),
            xaxis_title="Net Value USD",
            margin=dict(l=40, r=80, t=60, b=40),
            showlegend=False,
        )
        st.plotly_chart(fig_b, use_container_width=True)
    else:
        st.caption("Brak net buyers po filtrach.")

with col_s:
    top_sellers = filtered.nsmallest(10, "net_value_6m")
    if not top_sellers.empty and top_sellers["net_value_6m"].min() < 0:
        labels_s = [
            f"{t} — {n[:25]}"
            for t, n in zip(top_sellers["ticker"], top_sellers["name"])
        ]
        fig_s = go.Figure(go.Bar(
            x=top_sellers["net_value_6m"],
            y=labels_s,
            orientation="h",
            marker_color=RED,
            text=[format_large_number(v) for v in top_sellers["net_value_6m"]],
            textposition="outside",
        ))
        fig_s.update_layout(
            title="Top 10 Net Sellers (6 mc)",
            template="plotly_dark",
            height=380,
            yaxis=dict(autorange="reversed"),
            xaxis_title="Net Value USD",
            margin=dict(l=40, r=80, t=60, b=40),
            showlegend=False,
        )
        st.plotly_chart(fig_s, use_container_width=True)
    else:
        st.caption("Brak net sellers po filtrach.")

st.markdown("---")

# Placeholder dla Task 6 (tabela) i Task 7 (heatmapa) i Task 8 (cross-link + CSV)
st.info("🚧 Tabela, heatmapa, cross-link i CSV dodane w kolejnych taskach.")
```

- [ ] **Step 5.2: Syntax + tests + commit**

```bash
./venv/Scripts/python.exe -c "
import ast
with open('pages/23_insider_screener.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('Syntax OK')
" && ./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3 && \
git add pages/23_insider_screener.py && \
git commit -m "Add top buyers/sellers bar charts side-by-side (green/red)"
```

Expected: Syntax OK + 52/52 PASS + commit success.

---

## Task 6: Tabela screener

**Files:**
- Modify: `pages/23_insider_screener.py`

- [ ] **Step 6.1: Zamień placeholder na tabelę**

Znajdź `st.info("🚧 Tabela, heatmapa...")` po sekcji 1 i zamień na:

```python
# ---------------------------------------------------------------------------
# SEKCJA 2: Tabela screener (st.dataframe)
# ---------------------------------------------------------------------------

st.markdown(f"### 📋 Tabela screener ({len(filtered)} spolek)")

display = filtered.head(top_n).copy()
display = display.rename(columns={
    "sentiment": "🎯",
    "ticker": "Ticker",
    "name": "Nazwa",
    "sector": "Sektor",
    "market_cap": "Cap",
    "net_value_6m": "Net 6mc",
    "n_buys": "#Buys",
    "n_sells": "#Sells",
    "top_buyer": "Top Buyer",
    "top_institutional": "Top Fund",
    "beat_streak_buys": "Streak",
})
display_cols = [
    "🎯", "Ticker", "Nazwa", "Sektor", "Cap", "Net 6mc",
    "#Buys", "#Sells", "Top Buyer", "Top Fund", "Streak",
]

st.dataframe(
    display[display_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Cap": st.column_config.NumberColumn("Cap", format="$%.0f"),
        "Net 6mc": st.column_config.NumberColumn("Net 6mc", format="$%+.0f"),
        "Streak": st.column_config.ProgressColumn(
            "Streak", min_value=0, max_value=6, format="%d mc",
        ),
    },
)

st.markdown("---")

# Placeholder dla Task 7 (heatmapa) i Task 8 (cross-link + CSV)
st.info("🚧 Heatmapa, cross-link i CSV dodane w kolejnych taskach.")
```

- [ ] **Step 6.2: Syntax + tests + commit**

```bash
./venv/Scripts/python.exe -c "
import ast
with open('pages/23_insider_screener.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('Syntax OK')
" && ./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3 && \
git add pages/23_insider_screener.py && \
git commit -m "Add tabela screener z 11 kolumn (sentiment, sector, cap, net, streak)"
```

---

## Task 7: Sektorowa heatmapa

**Files:**
- Modify: `pages/23_insider_screener.py`

- [ ] **Step 7.1: Zamień placeholder na sektorową heatmapę**

Znajdź `st.info("🚧 Heatmapa, cross-link...")` po sekcji 2 i zamień na:

```python
# ---------------------------------------------------------------------------
# SEKCJA 3: Sektorowa heatmapa (Plotly horizontal bar)
# ---------------------------------------------------------------------------

st.markdown("### 🏭 Net insider activity per sektor")

sector_agg = filtered.groupby("sector")["net_value_6m"].sum().sort_values()
if not sector_agg.empty:
    colors_sec = [GREEN if v > 0 else RED for v in sector_agg.values]
    fig_sec = go.Figure(go.Bar(
        x=sector_agg.values,
        y=sector_agg.index,
        orientation="h",
        marker_color=colors_sec,
        text=[format_large_number(v) for v in sector_agg.values],
        textposition="outside",
    ))
    fig_sec.update_layout(
        title="Sum net insider value 6 mc per sektor",
        template="plotly_dark",
        height=400,
        xaxis_title="Sum Net Value USD",
        margin=dict(l=40, r=80, t=60, b=40),
        showlegend=False,
    )
    st.plotly_chart(fig_sec, use_container_width=True)
else:
    st.caption("Brak danych sektorowych po filtrach.")

st.markdown("---")

# Placeholder dla Task 8 (cross-link + CSV)
st.info("🚧 Cross-link i CSV dodane w kolejnym tasku.")
```

- [ ] **Step 7.2: Syntax + tests + commit**

```bash
./venv/Scripts/python.exe -c "
import ast
with open('pages/23_insider_screener.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('Syntax OK')
" && ./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3 && \
git add pages/23_insider_screener.py && \
git commit -m "Add sektorowa heatmapa (Plotly horizontal bar, green/red per net value)"
```

---

## Task 8: Cross-link selectbox + button + CSV export

**Files:**
- Modify: `pages/23_insider_screener.py`

- [ ] **Step 8.1: Zamień placeholder na cross-link + CSV**

Znajdź `st.info("🚧 Cross-link...")` po sekcji 3 i zamień na:

```python
# ---------------------------------------------------------------------------
# CROSS-LINK do F13 Sprawozdania Q deep dive Insiders sub-tab
# ---------------------------------------------------------------------------

st.markdown("### 📈 Deep dive (F13 Insiders)")
col_sel, col_btn = st.columns([3, 1])
with col_sel:
    selected_ticker = st.selectbox(
        "Wybierz ticker do deep dive:",
        options=[""] + filtered["ticker"].tolist(),
        key="insider_screener_deep_dive_select",
    )
with col_btn:
    st.write("")  # spacer
    go_btn = st.button(
        "📈 Pokaz szczegoly",
        key="insider_screener_deep_dive_btn",
        disabled=not selected_ticker,
    )

if go_btn and selected_ticker:
    # Pattern session_state z F14 hotfix (b1f8502): pending flag NIE widget key
    st.session_state["sp500_deep_dive_ticker"] = selected_ticker
    st.session_state["sp500_pending_view"] = "deep_dive"
    st.switch_page("pages/7_sp500.py")

st.markdown("---")

# ---------------------------------------------------------------------------
# CSV EXPORT
# ---------------------------------------------------------------------------

csv = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    "📥 Eksport CSV (screener)",
    data=csv,
    file_name=f"insider_screener_sp500_{pd.Timestamp.now():%Y%m%d}.csv",
    mime="text/csv",
    key="insider_screener_csv",
)
```

- [ ] **Step 8.2: Syntax + smoke test imports + tests + commit**

```bash
./venv/Scripts/python.exe -c "
import ast
for f in ['pages/7_sp500.py', 'pages/8_gpw.py', 'pages/22_earnings_calendar.py', 'pages/23_insider_screener.py']:
    with open(f, encoding='utf-8') as fh:
        ast.parse(fh.read())
    print(f, 'OK')
" && ./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3 && \
git add pages/23_insider_screener.py && \
git commit -m "Add cross-link selectbox + button -> F13 deep dive + CSV export"
```

Expected: 4x OK + 52/52 PASS + commit success.

---

## Task 9: Integracja `app.py` + `auth.py` + `CLAUDE.md`

**Files:**
- Modify: `components/auth.py`
- Modify: `app.py`
- Modify: `CLAUDE.md`

- [ ] **Step 9.1: Dodać `PAGE_INFO[23]` w `components/auth.py`**

Znajdź linię z page 22 w `PAGE_INFO`:

```python
22: ("📅", "Earnings Calendar", "Kalendarz nadchodzacych i niedawnych raportow SP500 + GPW (±28 dni) z watchlist"),
```

Dopisz po niej:

```python
23: ("👥", "Insider Screener", "Bulk insider activity SP500 — top buyers/sellers, sektory, beat streak"),
```

- [ ] **Step 9.2: Dodać kartę w `app.py`**

Znajdź tuple page 22:

```python
(22, "📅", "Earnings Calendar", "Kalendarz nadchodzacych raportow SP500+GPW (±28 dni) z watchlist i cross-link do F13", "pages/22_earnings_calendar.py"),
```

Dopisz po niej (zachowaj indentację + końcowy przecinek):

```python
(23, "👥", "Insider Screener", "Bulk insider screener SP500 — kto kupuje, kto sprzedaje, sektorowa heatmapa, cross-link do F13", "pages/23_insider_screener.py"),
```

- [ ] **Step 9.3: Update `CLAUDE.md` — sekcja Pages**

Znajdź linię z page 22 w sekcji Pages:

```markdown
  22_earnings_calendar.py # Earnings Calendar (±28 dni), watchlist localStorage, cross-link do F13 Sprawozdania Q
```

Dopisz po niej:

```markdown
  23_insider_screener.py  # Bulk Insider Screener SP500 (456), top buyers/sellers, sektorowa heatmapa, cross-link do F13 Insiders
```

- [ ] **Step 9.4: Update `CLAUDE.md` — Key Design Decisions F16**

Znajdź wpis F15 (Insider Trading & Institutional) — to długa linia. Dopisz po niej:

```markdown
- **Bulk Insider Screener (F16):** `pages/23_insider_screener.py` (page 23). Bulk insider activity dla SP500 (456 spółek, ETF filtered, GPW pominięte). UI: filtry expander (sektor multiselect, status Buy/Sell/Mixed/All, Min Net Value, Min beat streak 0-6, Min Market Cap 5 opcji, Sort 9 metryk, Top N 10/25/50/100/250) + 4 summary cards (Spółek z danymi X/456, Net Buyers, Net Sellers, Avg Net) + 2 Plotly bar charts side-by-side (Top 10 Buyers green, Top 10 Sellers red) + tabela 11 kolumn (🎯 sentiment / Ticker / Nazwa / Sektor / Cap / Net 6mc / #Buys / #Sells / Top Buyer / Top Fund / Streak ProgressColumn 0-6) + sektorowa Plotly horizontal bar (sum net per sektor GICS, green/red) + cross-link selectbox+button do F13 deep dive Insiders sub-tab (`st.switch_page` + session_state pattern z F14 `b1f8502`) + CSV export. Data layer (`data/financials.py`): `_compute_buy_streak` (kolejne miesiące buy > sell, 0-6) + `_aggregate_insider_for_ticker` (16 pól: net_value_6m, n_buys/sells, top_buyer single largest, top_seller, top_institutional Holder #1, sentiment 🟢/🔴/🟡/⚪, beat_streak) + `bulk_fetch_insider_screener` (ThreadPool 8 workers, `@st.cache_data ttl=86400`, filter ETF z `_get_etf_set` F14). Reuse: F15 `fetch_insider_transactions` + `fetch_institutional_holders` z fallback chain `_try_insider_endpoint`, F11 `get_ratios_snapshot` (sektor + market_cap), fallback sektor + nazwa z `SP500_SECTOR_MAP` + `SP500_NAMES`. Cold cache ~5-7 min (akceptowalne, potem <2s warm). Spec: `docs/superpowers/specs/2026-06-05-bulk-insider-screener-design.md`. Plan: `docs/superpowers/plans/2026-06-05-bulk-insider-screener.md`. Tests: `tests/test_financials.py` +6 testów (52/52 full suite).
```

- [ ] **Step 9.5: Syntax + smoke + tests + commit**

```bash
./venv/Scripts/python.exe -c "
import ast
for f in ['app.py', 'components/auth.py', 'pages/23_insider_screener.py']:
    with open(f, encoding='utf-8') as fh:
        ast.parse(fh.read())
    print(f, 'OK')
" && ./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3 && \
git add components/auth.py app.py CLAUDE.md && \
git commit -m "Integration page 23 (Insider Screener) — PAGE_INFO + app.py card + CLAUDE.md F16"
```

Expected: 3x OK + 52/52 PASS + commit success.

---

## Task 10: Final QA + push + MEMORY.md

**Files:**
- Modify: `C:\Users\m4x\.claude\projects\C--Users-m4x-Desktop-AI-ebook-white-new-A4\memory\MEMORY.md`
- Create: `C:\Users\m4x\.claude\projects\C--Users-m4x-Desktop-AI-ebook-white-new-A4\memory\project_gem_dashboard_insider_screener.md`

- [ ] **Step 10.1: Final test suite run**

```bash
cd C:\Users\m4x\Desktop\AI\gem-dashboard
./venv/Scripts/python.exe -m pytest tests/ -v 2>&1 | tail -10
```

Expected: 52/52 PASS (46 z F15 + 6 nowe z F16).

- [ ] **Step 10.2: Verify commits ahead**

```bash
git log origin/main..HEAD --oneline
```

Powinno być **10 commitów** (spec `1922f7d` + plan + 8 task commits).

- [ ] **Step 10.3: Push do main**

```bash
git push origin main
```

Streamlit Cloud auto-redeploy ~3-5 min.

- [ ] **Step 10.4: Manual QA na produkcji**

Otwórz `https://gem-dashboard.streamlit.app/`:
1. Sidebar — sprawdź czy karta "👥 Insider Screener" widoczna (po Earnings Calendar)
2. Klik → strona 23
3. Premium gate (kod)
4. **Bulk fetch progress bar** (~5-7 min cold cache pierwsze uruchomienie) — czekaj
5. Sprawdzić:
   - [ ] 4 summary cards renderują, "Spółek z danymi" >200/456 (jeśli <50 → yfinance global block)
   - [ ] Top 10 Buyers + Top 10 Sellers bar charts (zielone vs czerwone, side-by-side)
   - [ ] Tabela 11 kolumn — AAPL widoczny, TSLA jako net seller, JPM
   - [ ] Sektorowa heatmapa renderuje (Tech, Health typowo na górze)
   - [ ] Filter "Net Buyers 🟢" → tabela tylko 🟢 sentiment
   - [ ] Filter "Min Market Cap $10B+" odsiewa małe cap
   - [ ] VOO/QQQ NIE w tabeli (ETF filtered)
   - [ ] Selectbox AAPL + "Pokaż szczegóły" → page 7 tab 8 deep dive 5. sub-tab Insiders
   - [ ] CSV export pobiera plik
6. F15 sanity check — page 7 tab 8 deep dive AAPL → 5. sub-tab Insiders renderuje 6 sekcji
7. F14 sanity check — page 22 Earnings Calendar nadal działa

- [ ] **Step 10.5: MEMORY.md entry**

Utwórz topic file `project_gem_dashboard_insider_screener.md`:

```markdown
---
name: project-gem-dashboard-insider-screener
description: F16 Bulk Insider Screener — WGRANE YYYY-MM-DD, page 23 z screenerem insider activity SP500 + sektorowa heatmapa + cross-link do F13
metadata:
  type: project
---

# F16 Bulk Insider Screener — WGRANE YYYY-MM-DD

**Final commit:** `<HASH>` na main. Live: `gem-dashboard.streamlit.app` → karta "👥 Insider Screener".

## Co zostało dodane

**Data layer (`data/financials.py` +~150 LOC):**
- `_compute_buy_streak(transactions_df)` — kolejne miesiące buy > sell (0-6)
- `_aggregate_insider_for_ticker(ticker)` — 16-pól agregat per spółka
- `bulk_fetch_insider_screener(tickers, max_workers=8)` — ThreadPool + cache 24h + filter ETF

**UI (`pages/23_insider_screener.py` ~250 LOC):**
- Filtry expander (6 kontrolek: sektor, status, min net, min streak, min cap, sort, top N)
- 4 summary cards (X/456, Net Buyers, Net Sellers, Avg Net)
- 2 Plotly bar charts side-by-side (Top 10 Buyers green, Top 10 Sellers red)
- Tabela 11 kolumn (sentiment, ticker, name, sektor, cap, net, buys, sells, top buyer, top fund, streak progress)
- Sektorowa Plotly horizontal bar (sum net per sektor)
- Cross-link selectbox+button → F13 deep dive Insiders (st.switch_page + session_state)
- CSV export

**Reuse:**
- F15: `fetch_insider_transactions`, `fetch_institutional_holders` (z fallback chain `_try_insider_endpoint`)
- F11: `get_ratios_snapshot` (sektor + market_cap)
- F14: `_get_etf_set` (filter ETF), cross-link pattern (`pending_view` flag)

**Tests:** `tests/test_financials.py` +6 testów mock-based.

## Decyzje architektoniczne

- **SP500 only** (456 spółek). ETF wykluczone (no insider). GPW pominięte (F15 lesson — yfinance brak SEC Form 4 dla PL)
- **Bulk per spółka** — `_aggregate_insider_for_ticker` woła 3 endpointy F11/F15 (każdy z fallback chain F15)
- Cold cache ~5-7 min, cache 24h → warm <2s
- `top_buyer` = single largest transaction (nie suma) — pasuje do narracji "X kupił Y$ jednym ruchem"
- Sentiment 🟢/🔴/🟡/⚪ na podstawie net_value + n_buys/sells

## v2 backlog

- Multi-window toggle (3mc / 6mc / 12mc)
- Cross-feature watchlist filter (reuse `components/watchlist.py` z F14)
- "Smart insider" composite score
- Historical mini-sparkline per ticker
- Alerty Telegram/email "CEO/CFO kupili >$X dzisiaj"
- GPW ESPI scraping
- "Tylko z watchlisty" mode

## Powiązane

- [[project-gem-dashboard-insider-trading]] — F15 (host dla cross-link, reuse data layer)
- [[project-gem-dashboard-earnings-calendar]] — F14 (wzorzec cross-link + bulk screener)
- [[feedback-yfinance-fallback-chain-pattern]] — pattern w reused F15 functions
```

(YYYY-MM-DD + `<HASH>` podstaw z `git log -1 --oneline`.)

Następnie dodaj 1-liniowy entry w `MEMORY.md` w sekcji "Projekt: gem-dashboard" (po wpisie F15):

```markdown
- [F16 Bulk Insider Screener — WGRANE YYYY-MM-DD](project_gem_dashboard_insider_screener.md) — page 23 SP500 (456): top buyers/sellers bar charts, tabela 11 kolumn z sentiment 🟢/🔴/🟡, sektorowa heatmapa, cross-link do F13. Bulk z F15 fallback chain. Final commit `<HASH>`. 52/52 tests PASS.
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ `_compute_buy_streak` (Task 1)
- ✅ `_aggregate_insider_for_ticker` (Task 2)
- ✅ `bulk_fetch_insider_screener` z filter ETF (Task 3)
- ✅ Page skeleton + filtry + summary (Task 4)
- ✅ Top buyers/sellers bar charts (Task 5)
- ✅ Tabela 11 kolumn (Task 6)
- ✅ Sektorowa heatmapa (Task 7)
- ✅ Cross-link + CSV (Task 8)
- ✅ `app.py` + `auth.py` + `CLAUDE.md` (Task 9)
- ✅ Final QA + MEMORY.md (Task 10)

**Placeholder scan:**
- ✅ Brak TBD/TODO
- ✅ Wszystkie code blocks kompletne
- ⚠️ `YYYY-MM-DD` i `<HASH>` w MEMORY.md — zamierzone (engineer wypełnia z `git log`)

**Type consistency:**
- ✅ `_compute_buy_streak(transactions: pd.DataFrame) -> int` — Task 1 + Task 2 (caller w `_aggregate_insider_for_ticker`)
- ✅ `_aggregate_insider_for_ticker(ticker: str) -> dict | None` — Task 2 + Task 3 (caller w `bulk_fetch_insider_screener`)
- ✅ `bulk_fetch_insider_screener(tickers_tuple, max_workers=8) -> pd.DataFrame` — Task 3 + Task 4 (caller w page)
- ✅ 16 pól w dict z `_aggregate_insider_for_ticker` używane w Task 4-8 (sentiment, net_value_6m, n_buys, n_sells, top_buyer, top_institutional, beat_streak_buys, market_cap, sector, ticker, name)
- ✅ Cross-link session_state keys (`sp500_deep_dive_ticker`, `sp500_pending_view`) zgodne z F14/F15

**No spec requirement gaps detected.**
