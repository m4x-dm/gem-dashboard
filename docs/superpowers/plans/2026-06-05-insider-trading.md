# Insider Trading & Institutional Holdings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dodać 5. sub-tab "👥 Insiders" w F13 Sprawozdania Q deep dive (`render_sprawozdania_deep_dive` w `components/financials_ui.py`) — pełen obraz smart money: insider transactions, roster, institutional holders, mutual fund holders, major holders breakdown.

**Architecture:** Rozszerzenie `data/financials.py` o 6 funkcji `fetch_insider_*` / `fetch_institutional_*` / `fetch_mutualfund_*` / `fetch_major_*` + helper `_normalize_transaction_type` (Sale → Sell). Rozszerzenie `components/financials_ui.py` o `_render_insiders_tab` z 6 sekcjami UI + 2 Plotly chart helpers (bar net buy/sell per miesiąc, donut top 10 institutional). 5. sub-tab w istniejącym `render_sprawozdania_deep_dive`. GPW fallback gdy wszystkie 6 endpointów None → info box.

**Tech Stack:** Streamlit 1.55+, yfinance 0.2.50+ (`Ticker.insider_transactions` + `insider_purchases` + `insider_roster_holders` + `institutional_holders` + `mutualfund_holders` + `major_holders`), pandas 2.0+ (`DataFrame.map` nie `applymap`), plotly 5.18+. Brak parquet — in-memory cache `@st.cache_data(ttl=86400)`.

**Reference:** Spec `docs/superpowers/specs/2026-06-05-insider-trading-design.md` (commit `24cade2`).

---

## File Structure

**Modyfikowane:**
- `data/financials.py` — +6 funkcji fetch_* + 1 helper `_normalize_transaction_type` (+~250 LOC)
- `components/financials_ui.py` — +`_render_insiders_tab` z 6 sekcjami + 2 chart helpers + 5. sub-tab w `render_sprawozdania_deep_dive` (+~250 LOC)
- `tests/test_financials.py` — +9 testów mock-based (3 normalize_type + 1 transactions + 1 empty + 1 institutional + 3 major holders)
- `CLAUDE.md` — F15 paragraph w Key Design Decisions

**Bez nowych plików** — wszystko jako rozszerzenie istniejących modułów.

**Bez zmian:**
- `pages/7_sp500.py`, `pages/8_gpw.py` — F13 tab8 bez zmian
- `app.py`, `auth.py` — sub-tab nie nowa strona
- `pages/22_earnings_calendar.py` — F14 cross-link do F13 deep dive nadal działa (5 sub-tabów zamiast 4 to nie problem)

---

## Task 1: Helper `_normalize_transaction_type`

**Files:**
- Modify: `data/financials.py` (dopisać po ostatniej funkcji `bulk_fetch_earnings_calendar`)
- Modify: `tests/test_financials.py` (dopisać 3 testy)

- [ ] **Step 1.1: Dopisać 3 testy do `tests/test_financials.py`**

Otwórz `tests/test_financials.py` i dopisz na końcu:

```python


def test_normalize_transaction_type_sale_variants():
    from data.financials import _normalize_transaction_type
    # Wszystkie warianty "Sale" -> "Sell"
    assert _normalize_transaction_type("Sale") == "Sell"
    assert _normalize_transaction_type("Sale (Non Open Market)") == "Sell"
    assert _normalize_transaction_type("Sale at Public Offering") == "Sell"
    assert _normalize_transaction_type("Sell") == "Sell"


def test_normalize_transaction_type_purchase():
    from data.financials import _normalize_transaction_type
    assert _normalize_transaction_type("Purchase") == "Buy"
    assert _normalize_transaction_type("Buy") == "Buy"
    assert _normalize_transaction_type("Purchase (Open Market)") == "Buy"


def test_normalize_transaction_type_other_kept():
    from data.financials import _normalize_transaction_type
    # Inne typy zostawiamy (informacyjne, nie liczymy w net buy/sell)
    # Split na "(" zeby dostac sama akcje
    assert _normalize_transaction_type("Exercise of Options") == "Exercise of Options"
    assert _normalize_transaction_type("Conversion") == "Conversion"
    assert _normalize_transaction_type("Other (Acquisition)") == "Other"
```

- [ ] **Step 1.2: Run tests — verify FAIL**

```bash
cd C:\Users\m4x\Desktop\AI\gem-dashboard
./venv/Scripts/python.exe -m pytest tests/test_financials.py -v -k normalize_transaction_type
```

Expected: 3 FAIL z `ImportError: cannot import name '_normalize_transaction_type'`.

- [ ] **Step 1.3: Implementacja w `data/financials.py`**

Sprawdź gdzie kończy się plik:

```bash
tail -5 data/financials.py
```

Powinno być `return out` na końcu `bulk_fetch_earnings_calendar`. Dopisz po:

```python


# ---------------------------------------------------------------------------
# Insider Trading & Institutional Holdings (F15)
# ---------------------------------------------------------------------------

def _normalize_transaction_type(raw: str) -> str:
    """Mapuje yfinance transaction type na ujednolicony Buy/Sell.

    Sale variants ("Sale", "Sale (Non Open Market)", "Sell") -> "Sell"
    Purchase variants ("Purchase", "Buy") -> "Buy"
    Pozostale (Exercise of Options, Conversion, Other) zostawione,
    z odcietym suffix w nawiasie (np. "Other (Acquisition)" -> "Other").
    """
    raw_str = str(raw)
    raw_lower = raw_str.lower()
    if "sale" in raw_lower or "sell" in raw_lower:
        return "Sell"
    if "purchase" in raw_lower or "buy" in raw_lower:
        return "Buy"
    return raw_str.split("(")[0].strip()
```

- [ ] **Step 1.4: Run tests — verify PASS**

```bash
./venv/Scripts/python.exe -m pytest tests/test_financials.py -v -k normalize_transaction_type
```

Expected: 3 PASS.

- [ ] **Step 1.5: Regression check**

```bash
./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```

Expected: 37/37 PASS (34 dotychczasowe + 3 nowe).

- [ ] **Step 1.6: Commit**

```bash
git add data/financials.py tests/test_financials.py
git commit -m "Add _normalize_transaction_type helper (Sale variants -> Sell, Purchase -> Buy)"
```

---

## Task 2: `fetch_insider_transactions`

**Files:**
- Modify: `data/financials.py` (dopisać po `_normalize_transaction_type`)
- Modify: `tests/test_financials.py` (dopisać 2 testy)

- [ ] **Step 2.1: Dopisać 2 testy do `tests/test_financials.py`**

Dopisz na końcu:

```python


def test_fetch_insider_transactions_normalizes_types():
    """Mock yfinance insider_transactions — normalize Type column."""
    mock_df = pd.DataFrame({
        "Insider": ["TIMOTHY D. COOK", "LUCA MAESTRI", "ELON MUSK"],
        "Position": ["CEO", "CFO", "CEO"],
        "Transaction": ["Sale (Non Open Market)", "Purchase", "Exercise of Options"],
        "Shares": [100000, 5000, 250000],
        "Value": [20_000_000, 1_000_000, 50_000_000],
    }, index=pd.to_datetime(["2026-05-15", "2026-04-20", "2026-03-10"]))

    mock_ticker = MagicMock()
    mock_ticker.insider_transactions = mock_df

    from data.financials import fetch_insider_transactions
    with patch("data.financials.yf.Ticker", return_value=mock_ticker):
        result = fetch_insider_transactions("AAPL_TEST")

    assert result is not None
    assert "Type" in result.columns
    # "Sale (Non Open Market)" -> "Sell"
    # "Purchase" -> "Buy"
    # "Exercise of Options" zostawione
    types = result["Type"].tolist()
    assert "Sell" in types
    assert "Buy" in types
    assert "Exercise of Options" in types


def test_fetch_insider_transactions_returns_none_on_empty():
    mock_ticker = MagicMock()
    mock_ticker.insider_transactions = pd.DataFrame()

    from data.financials import fetch_insider_transactions
    with patch("data.financials.yf.Ticker", return_value=mock_ticker):
        result = fetch_insider_transactions("EMPTY_TEST")

    assert result is None
```

- [ ] **Step 2.2: Run tests — verify FAIL**

```bash
./venv/Scripts/python.exe -m pytest tests/test_financials.py -v -k fetch_insider_transactions
```

Expected: 2 FAIL z `ImportError: cannot import name 'fetch_insider_transactions'`.

- [ ] **Step 2.3: Implementacja**

Dopisz w `data/financials.py` po `_normalize_transaction_type`:

```python


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_insider_transactions(ticker: str) -> pd.DataFrame | None:
    """Historia transakcji insiderów (CEO/CFO/...) ostatnie ~6 mc.

    yfinance Ticker.insider_transactions zwraca DF z indeksem DatetimeIndex
    + kolumnami: Insider, Position, Transaction, Shares, Value, URL.

    Returns DF z znormalizowanymi kolumnami:
        Insider, Position, Type (Buy/Sell/Other), Shares, Value
    Indeks: DatetimeIndex (date raportu).
    None gdy brak danych.
    """
    try:
        t = yf.Ticker(ticker, session=_get_yf_session())
        df = t.insider_transactions
    except Exception:
        return None

    if df is None or df.empty:
        return None

    out = df.copy()

    # Normalize Type column
    type_col = None
    for cand in ["Transaction", "Type", "Action"]:
        if cand in out.columns:
            type_col = cand
            break
    if type_col is None:
        return None

    out["Type"] = out[type_col].apply(_normalize_transaction_type)

    # Keep tylko interesujace kolumny
    keep = []
    for cand in ["Insider", "Position", "Type", "Shares", "Value"]:
        if cand in out.columns:
            keep.append(cand)
    if not keep or "Type" not in keep:
        return None
    out = out[keep]

    return out
```

- [ ] **Step 2.4: Run tests — verify PASS**

```bash
./venv/Scripts/python.exe -m pytest tests/test_financials.py -v -k fetch_insider_transactions
```

Expected: 2 PASS.

- [ ] **Step 2.5: Commit**

```bash
git add data/financials.py tests/test_financials.py
git commit -m "Add fetch_insider_transactions z normalize Type (Sale -> Sell)"
```

---

## Task 3: `fetch_insider_purchases` + `fetch_insider_roster_holders`

**Files:**
- Modify: `data/financials.py` (dopisać po `fetch_insider_transactions`)
- Modify: `tests/test_financials.py` (dopisać 2 testy)

- [ ] **Step 3.1: Dopisać 2 testy**

```python


def test_fetch_insider_purchases_returns_df():
    """Mock yfinance insider_purchases — agregat 6mc."""
    mock_df = pd.DataFrame({
        "Insider Purchases Last 6m": [
            "Purchases", "Sales", "Net Shares Purchased (Sold)",
            "Total Insider Shares Held", "% Net Shares Purchased (Sold)",
        ],
        "Shares": [5000, 100000, -95000, 3280000, -2.9],
        "Trans": [12, 47, -35, None, None],
    })

    mock_ticker = MagicMock()
    mock_ticker.insider_purchases = mock_df

    from data.financials import fetch_insider_purchases
    with patch("data.financials.yf.Ticker", return_value=mock_ticker):
        result = fetch_insider_purchases("AAPL_TEST")

    assert result is not None
    assert not result.empty


def test_fetch_insider_roster_holders_returns_df():
    """Mock yfinance insider_roster_holders."""
    mock_df = pd.DataFrame({
        "Name": ["Timothy D. Cook", "Luca Maestri"],
        "Position": ["CEO", "CFO"],
        "Most Recent Transaction": ["Sale", "Sale"],
        "Latest Transaction Date": pd.to_datetime(["2026-05-15", "2026-04-20"]),
        "Shares Owned Directly": [3_280_000, 850_000],
    })

    mock_ticker = MagicMock()
    mock_ticker.insider_roster_holders = mock_df

    from data.financials import fetch_insider_roster_holders
    with patch("data.financials.yf.Ticker", return_value=mock_ticker):
        result = fetch_insider_roster_holders("AAPL_TEST")

    assert result is not None
    assert len(result) == 2
```

- [ ] **Step 3.2: Verify FAIL**

```bash
./venv/Scripts/python.exe -m pytest tests/test_financials.py -v -k "insider_purchases or insider_roster"
```

Expected: 2 FAIL.

- [ ] **Step 3.3: Implementacja**

Dopisz w `data/financials.py` po `fetch_insider_transactions`:

```python


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_insider_purchases(ticker: str) -> pd.DataFrame | None:
    """Insider purchases summary (agregat 6 mc).

    yfinance Ticker.insider_purchases zwraca DF z metrykami:
    Total Purchases, Total Sales, Net Shares Purchased/Sold,
    Total Insider Shares Held, % Net Shares Purchased/Sold.

    Returns: surowy DF (UI sam parsuje rows). None gdy empty.
    """
    try:
        t = yf.Ticker(ticker, session=_get_yf_session())
        df = t.insider_purchases
    except Exception:
        return None

    if df is None or df.empty:
        return None
    return df


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_insider_roster_holders(ticker: str) -> pd.DataFrame | None:
    """Roster insiderow — kto z zarzadu trzyma ile akcji.

    yfinance Ticker.insider_roster_holders zwraca DF z kolumnami:
    Name, Position, Most Recent Transaction, Latest Transaction Date,
    Shares Owned Directly, Shares Owned Indirectly.

    Returns: surowy DF. None gdy empty.
    """
    try:
        t = yf.Ticker(ticker, session=_get_yf_session())
        df = t.insider_roster_holders
    except Exception:
        return None

    if df is None or df.empty:
        return None
    return df
```

- [ ] **Step 3.4: Verify PASS**

```bash
./venv/Scripts/python.exe -m pytest tests/test_financials.py -v -k "insider_purchases or insider_roster"
```

Expected: 2 PASS.

- [ ] **Step 3.5: Commit**

```bash
git add data/financials.py tests/test_financials.py
git commit -m "Add fetch_insider_purchases + fetch_insider_roster_holders (surowe DF)"
```

---

## Task 4: `fetch_institutional_holders` + `fetch_mutualfund_holders`

**Files:**
- Modify: `data/financials.py` (dopisać po `fetch_insider_roster_holders`)
- Modify: `tests/test_financials.py` (dopisać 2 testy)

- [ ] **Step 4.1: Dopisać 2 testy**

```python


def test_fetch_institutional_holders_returns_df():
    """Mock yfinance institutional_holders — top 10 funduszy."""
    mock_df = pd.DataFrame({
        "Holder": ["Vanguard Group Inc", "BlackRock Inc.", "Berkshire Hathaway Inc"],
        "Shares": [1_300_000_000, 1_000_000_000, 890_000_000],
        "Date Reported": pd.to_datetime(["2026-03-31", "2026-03-31", "2026-03-31"]),
        "% Out": [8.2, 6.5, 5.5],
        "Value": [260_000_000_000, 200_000_000_000, 178_000_000_000],
    })

    mock_ticker = MagicMock()
    mock_ticker.institutional_holders = mock_df

    from data.financials import fetch_institutional_holders
    with patch("data.financials.yf.Ticker", return_value=mock_ticker):
        result = fetch_institutional_holders("AAPL_TEST")

    assert result is not None
    assert "Holder" in result.columns
    assert len(result) == 3


def test_fetch_mutualfund_holders_returns_df():
    mock_df = pd.DataFrame({
        "Holder": ["Vanguard Total Market", "SPDR S&P 500 ETF"],
        "Shares": [365_000_000, 285_000_000],
        "Date Reported": pd.to_datetime(["2026-03-31", "2026-03-31"]),
        "% Out": [2.3, 1.8],
        "Value": [73_000_000_000, 57_000_000_000],
    })

    mock_ticker = MagicMock()
    mock_ticker.mutualfund_holders = mock_df

    from data.financials import fetch_mutualfund_holders
    with patch("data.financials.yf.Ticker", return_value=mock_ticker):
        result = fetch_mutualfund_holders("AAPL_TEST")

    assert result is not None
    assert len(result) == 2
```

- [ ] **Step 4.2: Verify FAIL**

```bash
./venv/Scripts/python.exe -m pytest tests/test_financials.py -v -k "institutional_holders or mutualfund_holders"
```

Expected: 2 FAIL.

- [ ] **Step 4.3: Implementacja**

Dopisz w `data/financials.py`:

```python


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_institutional_holders(ticker: str) -> pd.DataFrame | None:
    """Top 10 funduszy instytucjonalnych (BlackRock, Vanguard, etc.).

    yfinance Ticker.institutional_holders zwraca DF z kolumnami:
    Holder, Shares, Date Reported, % Out, Value.

    Returns: surowy DF (top 10). None gdy empty.
    """
    try:
        t = yf.Ticker(ticker, session=_get_yf_session())
        df = t.institutional_holders
    except Exception:
        return None

    if df is None or df.empty:
        return None
    return df


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_mutualfund_holders(ticker: str) -> pd.DataFrame | None:
    """Top 10 mutual funds.

    yfinance Ticker.mutualfund_holders — taka sama struktura co
    institutional_holders.
    """
    try:
        t = yf.Ticker(ticker, session=_get_yf_session())
        df = t.mutualfund_holders
    except Exception:
        return None

    if df is None or df.empty:
        return None
    return df
```

- [ ] **Step 4.4: Verify PASS**

```bash
./venv/Scripts/python.exe -m pytest tests/test_financials.py -v -k "institutional_holders or mutualfund_holders"
```

Expected: 2 PASS.

- [ ] **Step 4.5: Commit**

```bash
git add data/financials.py tests/test_financials.py
git commit -m "Add fetch_institutional_holders + fetch_mutualfund_holders"
```

---

## Task 5: `fetch_major_holders` z defensywnym parserem (dict ALBO DF)

**Files:**
- Modify: `data/financials.py` (dopisać)
- Modify: `tests/test_financials.py` (dopisać 3 testy)

- [ ] **Step 5.1: Dopisać 3 testy**

```python


def test_fetch_major_holders_dict_format():
    """yfinance zwraca dict (newer versions)."""
    mock_dict = {
        "insidersPercentHeld": 0.0007,
        "institutionsPercentHeld": 0.625,
        "institutionsCount": 4892,
        "institutionsFloatPercentHeld": 0.9993,
    }

    mock_ticker = MagicMock()
    mock_ticker.major_holders = mock_dict

    from data.financials import fetch_major_holders
    with patch("data.financials.yf.Ticker", return_value=mock_ticker):
        result = fetch_major_holders("AAPL_TEST")

    assert result is not None
    assert result["insider_pct"] == 0.0007
    assert result["institutional_pct"] == 0.625
    assert result["institutional_count"] == 4892
    assert result["float_pct"] == 0.9993


def test_fetch_major_holders_df_format():
    """yfinance zwraca DataFrame (older versions) — defensywny parser."""
    mock_df = pd.DataFrame(
        {"Value": [0.0007, 0.625, 4892, 0.9993]},
        index=[
            "% of Shares Held by All Insider",
            "% of Shares Held by Institutions",
            "Number of Institutions Holding Shares",
            "% of Float Held by Institutions",
        ],
    )

    mock_ticker = MagicMock()
    mock_ticker.major_holders = mock_df

    from data.financials import fetch_major_holders
    with patch("data.financials.yf.Ticker", return_value=mock_ticker):
        result = fetch_major_holders("AAPL_TEST")

    assert result is not None
    assert result["insider_pct"] == 0.0007
    assert result["institutional_pct"] == 0.625


def test_fetch_major_holders_returns_none_when_all_empty():
    mock_ticker = MagicMock()
    mock_ticker.major_holders = None

    from data.financials import fetch_major_holders
    with patch("data.financials.yf.Ticker", return_value=mock_ticker):
        result = fetch_major_holders("EMPTY_TEST")

    assert result is None
```

- [ ] **Step 5.2: Verify FAIL**

```bash
./venv/Scripts/python.exe -m pytest tests/test_financials.py -v -k major_holders
```

Expected: 3 FAIL.

- [ ] **Step 5.3: Implementacja**

```python


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_major_holders(ticker: str) -> dict | None:
    """Major Holders breakdown — % insider / % institutional / # institutions / % float.

    yfinance Ticker.major_holders moze zwrocic dict ALBO DataFrame
    (rozne wersje). Defensywny parser obsluguje oba formaty.

    Returns dict: {insider_pct, institutional_pct, institutional_count, float_pct}
    None gdy wszystkie pola brak.
    """
    try:
        t = yf.Ticker(ticker, session=_get_yf_session())
        raw = t.major_holders
    except Exception:
        return None

    if raw is None:
        return None

    out = {
        "insider_pct": None,
        "institutional_pct": None,
        "institutional_count": None,
        "float_pct": None,
    }

    if isinstance(raw, dict):
        out["insider_pct"] = raw.get("insidersPercentHeld")
        out["institutional_pct"] = raw.get("institutionsPercentHeld")
        out["institutional_count"] = raw.get("institutionsCount")
        out["float_pct"] = raw.get("institutionsFloatPercentHeld")
    elif isinstance(raw, pd.DataFrame) and not raw.empty:
        # Index = label, kolumna 0 = value
        idx_map = {
            "% of shares held by all insider": "insider_pct",
            "% of shares held by institutions": "institutional_pct",
            "number of institutions holding shares": "institutional_count",
            "% of float held by institutions": "float_pct",
        }
        value_col = raw.columns[0]
        for idx in raw.index:
            idx_lower = str(idx).lower()
            for needle, our_key in idx_map.items():
                if needle in idx_lower:
                    out[our_key] = raw.loc[idx, value_col]
                    break

    if all(v is None for v in out.values()):
        return None
    return out
```

- [ ] **Step 5.4: Verify PASS**

```bash
./venv/Scripts/python.exe -m pytest tests/test_financials.py -v -k major_holders
```

Expected: 3 PASS.

- [ ] **Step 5.5: Full suite regression**

```bash
./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```

Expected: 44/44 PASS (34 base + 3 normalize + 2 transactions + 2 purchases/roster + 2 institutional/mutual + 3 major).

- [ ] **Step 5.6: Commit**

```bash
git add data/financials.py tests/test_financials.py
git commit -m "Add fetch_major_holders z defensywnym parserem (dict | DataFrame format)"
```

---

## Task 6: Chart helpers + 6 sekcji render w `components/financials_ui.py`

**Files:**
- Modify: `components/financials_ui.py` (dopisać helpery PRZED `render_sprawozdania_deep_dive`)

- [ ] **Step 6.1: Sprawdzić aktualne importy w `components/financials_ui.py`**

```bash
head -25 /c/Users/m4x/Desktop/AI/gem-dashboard/components/financials_ui.py
```

Powinno być coś jak:
```python
from data.financials import (
    bulk_fetch_earnings_history,
    fetch_annual_statements,
    fetch_earnings_trend,
    fetch_quarterly_statements,
    format_currency,
    format_large_number,
    get_earnings_history,
    get_forward_consensus,
    get_ratios_snapshot,
    is_bank,
)
```

- [ ] **Step 6.2: Rozszerzyć import z `data.financials`**

W `components/financials_ui.py` znajdź sekcję `from data.financials import (...)` i dopisz nowe symbole (zachowaj porządek alfabetyczny):

```python
from data.financials import (
    bulk_fetch_earnings_history,
    fetch_annual_statements,
    fetch_earnings_trend,
    fetch_insider_purchases,
    fetch_insider_roster_holders,
    fetch_insider_transactions,
    fetch_institutional_holders,
    fetch_major_holders,
    fetch_mutualfund_holders,
    fetch_quarterly_statements,
    format_currency,
    format_large_number,
    get_earnings_history,
    get_forward_consensus,
    get_ratios_snapshot,
    is_bank,
)
```

- [ ] **Step 6.3: Dopisać 2 chart helpers PRZED `render_sprawozdania_deep_dive`**

Znajdź linię `def render_sprawozdania_deep_dive(ticker: str, market: str)` (linia ~377) i dopisz PRZED nią:

```python


# ---------------------------------------------------------------------------
# Insiders sub-tab helpers (F15)
# ---------------------------------------------------------------------------

def _chart_insider_net_per_month(transactions_df: pd.DataFrame) -> None:
    """Plotly bar chart: net buy/sell value per miesiac (6 mc).

    Zielony slupek gdy net > 0 (kupujace insider'y), czerwony gdy net < 0.
    """
    if transactions_df is None or transactions_df.empty:
        return

    # Wymagamy kolumn Type + Value + index DatetimeIndex
    if "Type" not in transactions_df.columns or "Value" not in transactions_df.columns:
        return

    df = transactions_df.copy()
    df = df[df["Type"].isin(["Buy", "Sell"])]
    if df.empty:
        return

    # Year-month grupowanie
    df["_yearmonth"] = pd.to_datetime(df.index).to_period("M")
    agg = df.groupby("_yearmonth").apply(
        lambda x: float(x[x["Type"] == "Buy"]["Value"].sum())
        - float(x[x["Type"] == "Sell"]["Value"].sum())
    )

    # Reindex do full 6 mc range (puste miesiace = 0)
    all_months = pd.period_range(
        end=pd.Timestamp.now().to_period("M"),
        periods=6,
        freq="M",
    )
    agg = agg.reindex(all_months, fill_value=0)

    colors = [GREEN if v > 0 else RED for v in agg.values]

    fig = go.Figure(go.Bar(
        x=[str(p) for p in agg.index],
        y=agg.values,
        marker_color=colors,
        name="Net insider activity",
    ))
    fig.update_layout(
        title="Net insider buy/sell value per miesiac (6 mc)",
        template="plotly_dark",
        height=300,
        yaxis_title="Net USD",
        showlegend=False,
        margin=dict(l=40, r=40, t=60, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def _chart_institutional_pie(institutional_df: pd.DataFrame) -> None:
    """Plotly donut chart: top 10 funduszy + 'Reszta'.

    Top 5 = gold variants, top 6-10 = gray. Hole=0.4 (donut).
    """
    if institutional_df is None or institutional_df.empty:
        return

    if "Holder" not in institutional_df.columns or "% Out" not in institutional_df.columns:
        return

    top10 = institutional_df.head(10)
    top10_sum = float(top10["% Out"].sum())
    rest_pct = max(0.0, 100.0 - top10_sum)

    labels = list(top10["Holder"]) + ["Reszta"]
    values = list(top10["% Out"]) + [rest_pct]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(
            colors=[
                GOLD, "#E8C96A", "#FFD700", "#B8860B", "#DAA520",  # top 5 gold
                "#888", "#777", "#666", "#555", "#444",            # 6-10 gray
                "#222",                                            # Reszta
            ],
        ),
        textinfo="label+percent",
        textposition="outside",
        sort=False,
    ))
    fig.update_layout(
        title="Distribution institutional ownership",
        template="plotly_dark",
        height=380,
        showlegend=False,
        margin=dict(l=40, r=40, t=60, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_insiders_tab(ticker: str) -> None:
    """Sub-tab 5: Insiders & Institutional (6 sekcji).

    Sekcje:
    1. Major Holders (4 metric cards)
    2. Insider Purchases summary (3 metric cards)
    3. Insider Transactions (tabela + bar chart net per miesiac)
    4. Insider Roster (tabela)
    5. Institutional Holders (tabela + donut top 10)
    6. Mutual Fund Holders (tabela)

    GPW fallback: jesli wszystkie 6 endpointow None -> info box.
    """
    major = fetch_major_holders(ticker)
    purchases = fetch_insider_purchases(ticker)
    transactions = fetch_insider_transactions(ticker)
    roster = fetch_insider_roster_holders(ticker)
    institutional = fetch_institutional_holders(ticker)
    mutual = fetch_mutualfund_holders(ticker)

    # GPW fallback — wszystkie None
    if all(x is None for x in [major, purchases, transactions, roster, institutional, mutual]):
        st.info(
            "⚠️ Brak danych insider/institutional dla tego tickera.\n\n"
            "Dla spolek GPW raporty biezace ida przez ESPI (poza zakresem yfinance).\n"
            "Sprawdz recznie: https://www.gpw.pl/komunikaty-spolek"
        )
        return

    # ============== SEKCJA 1: Major Holders (4 metric cards 2x2) ==============
    st.markdown("#### 📊 Major Holders")
    c1, c2, c3, c4 = st.columns(4)
    if major is not None:
        def _fmt_pct(v):
            if v is None:
                return "—"
            try:
                return f"{float(v) * 100:.2f}%"
            except Exception:
                return "—"

        def _fmt_count(v):
            if v is None:
                return "—"
            try:
                return f"{int(v):,}"
            except Exception:
                return "—"

        c1.metric("% Insider", _fmt_pct(major.get("insider_pct")))
        c2.metric("% Institutional", _fmt_pct(major.get("institutional_pct")))
        c3.metric("# Institutions", _fmt_count(major.get("institutional_count")))
        c4.metric("% Float", _fmt_pct(major.get("float_pct")))
    else:
        c1.metric("% Insider", "—")
        c2.metric("% Institutional", "—")
        c3.metric("# Institutions", "—")
        c4.metric("% Float", "—")

    st.markdown("---")

    # ============== SEKCJA 2: Insider Purchases summary ==============
    st.markdown("#### 💰 Insider Purchases (6 mc agregat)")
    if purchases is not None and not purchases.empty:
        st.dataframe(purchases, use_container_width=True, hide_index=True)
    else:
        st.caption("Brak danych dla Insider Purchases.")

    st.markdown("---")

    # ============== SEKCJA 3: Insider Transactions + bar chart ==============
    st.markdown("#### 📈 Historia transakcji insiderów (6 mc)")
    if transactions is not None and not transactions.empty:
        _chart_insider_net_per_month(transactions)
        # Tabela: 30 ostatnich, format Value/Shares
        display = transactions.head(30).copy()
        st.dataframe(
            display,
            use_container_width=True,
            column_config={
                "Shares": st.column_config.NumberColumn("Shares", format="%d"),
                "Value": st.column_config.NumberColumn("Value (USD)", format="$%d"),
                "Type": st.column_config.TextColumn("Type"),
            },
        )
    else:
        st.caption("Brak danych dla Insider Transactions.")

    st.markdown("---")

    # ============== SEKCJA 4: Insider Roster ==============
    st.markdown("#### 🏢 Roster zarządu")
    if roster is not None and not roster.empty:
        st.dataframe(roster, use_container_width=True, hide_index=True)
    else:
        st.caption("Brak danych dla Insider Roster.")

    st.markdown("---")

    # ============== SEKCJA 5: Institutional Holders + donut ==============
    st.markdown("#### 🏛️ Top 10 funduszy instytucjonalnych")
    if institutional is not None and not institutional.empty:
        col_t, col_c = st.columns([6, 4])
        with col_t:
            st.dataframe(institutional, use_container_width=True, hide_index=True)
        with col_c:
            _chart_institutional_pie(institutional)
    else:
        st.caption("Brak danych dla Institutional Holders.")

    st.markdown("---")

    # ============== SEKCJA 6: Mutual Fund Holders ==============
    st.markdown("#### 💼 Top 10 mutual funds")
    if mutual is not None and not mutual.empty:
        st.dataframe(mutual, use_container_width=True, hide_index=True)
    else:
        st.caption("Brak danych dla Mutual Fund Holders.")
```

- [ ] **Step 6.4: Syntax check**

```bash
./venv/Scripts/python.exe -c "
import ast
with open('components/financials_ui.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('Syntax OK')
"
```

Expected: `Syntax OK`.

- [ ] **Step 6.5: Smoke import test**

```bash
./venv/Scripts/python.exe -c "
from components.financials_ui import _render_insiders_tab, _chart_insider_net_per_month, _chart_institutional_pie
print('Imports OK')
"
```

Expected: `Imports OK`.

- [ ] **Step 6.6: Regression**

```bash
./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```

Expected: 44/44 PASS.

- [ ] **Step 6.7: Commit**

```bash
git add components/financials_ui.py
git commit -m "Add _render_insiders_tab + 2 chart helpers (net per month, institutional donut)"
```

---

## Task 7: Integracja 5. sub-tab w `render_sprawozdania_deep_dive`

**Files:**
- Modify: `components/financials_ui.py:443-455` (`st.tabs` + `with sub5`)

- [ ] **Step 7.1: Sprawdzić aktualny kod**

```bash
grep -n "st.tabs\|with sub" /c/Users/m4x/Desktop/AI/gem-dashboard/components/financials_ui.py | head -10
```

- [ ] **Step 7.2: Zamiana 4 sub-tabów na 5**

W `components/financials_ui.py` znajdź:

```python
    sub1, sub2, sub3, sub4 = st.tabs([
        "📊 Beat/Miss historia",
        "📑 Income Statement",
        "💰 Balance Sheet",
        "💵 Cash Flow",
    ])
    with sub1:
        _render_beat_miss_tab(ticker)
    with sub2:
        _render_income_statement_tab(ticker)
    with sub3:
        _render_balance_sheet_tab(ticker)
    with sub4:
        _render_cashflow_tab(ticker)
```

Zamień na:

```python
    sub1, sub2, sub3, sub4, sub5 = st.tabs([
        "📊 Beat/Miss historia",
        "📑 Income Statement",
        "💰 Balance Sheet",
        "💵 Cash Flow",
        "👥 Insiders",
    ])
    with sub1:
        _render_beat_miss_tab(ticker)
    with sub2:
        _render_income_statement_tab(ticker)
    with sub3:
        _render_balance_sheet_tab(ticker)
    with sub4:
        _render_cashflow_tab(ticker)
    with sub5:
        _render_insiders_tab(ticker)
```

- [ ] **Step 7.3: Syntax + regression**

```bash
./venv/Scripts/python.exe -c "
import ast
with open('components/financials_ui.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('Syntax OK')
" && ./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```

Expected: Syntax OK + 44/44 PASS.

- [ ] **Step 7.4: Smoke import test (page 7 / 8)**

```bash
./venv/Scripts/python.exe -c "
import ast
for f in ['pages/7_sp500.py', 'pages/8_gpw.py', 'pages/22_earnings_calendar.py', 'components/financials_ui.py']:
    with open(f, encoding='utf-8') as fh:
        ast.parse(fh.read())
    print(f, 'OK')
"
```

Expected: 4x OK.

- [ ] **Step 7.5: Commit**

```bash
git add components/financials_ui.py
git commit -m "Integration: 5. sub-tab 'Insiders' w render_sprawozdania_deep_dive"
```

---

## Task 8: CLAUDE.md F15 paragraph

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 8.1: Znaleźć F14 paragraph w CLAUDE.md**

```bash
grep -n "F14\|F15\|Earnings Calendar" /c/Users/m4x/Desktop/AI/gem-dashboard/CLAUDE.md | head -5
```

- [ ] **Step 8.2: Dopisać F15 paragraph po F14**

Znajdź linię z `- **Earnings Calendar (F14):**` w CLAUDE.md. Po tej linii (jednej długiej) dopisz:

```markdown
- **Insider Trading & Institutional (F15):** 5. sub-tab `👥 Insiders` w F13 Sprawozdania Q deep dive (`components/financials_ui.py:render_sprawozdania_deep_dive`). 6 sekcji: Major Holders (4 metric cards % insider/institutional/count/float) + Insider Purchases summary + Insider Transactions (tabela + Plotly bar net buy/sell per miesiąc 6 mc, zielony/czerwony) + Insider Roster + Institutional Holders (tabela + Plotly donut top 10 + Reszta) + Mutual Fund Holders. 6 funkcji w `data/financials.py`: `fetch_insider_transactions` (z normalize Sale→Sell przez `_normalize_transaction_type`), `fetch_insider_purchases`, `fetch_insider_roster_holders`, `fetch_institutional_holders`, `fetch_mutualfund_holders`, `fetch_major_holders` (defensywny parser dict ALBO DataFrame). Cache `@st.cache_data(ttl=86400)` in-memory (lekkie endpointy, brak parquet). GPW fallback: wszystkie 6 None → info box z linkiem do gpw.pl/komunikaty-spolek (yfinance nie ma SEC Form 4 dla polskich spółek). Banki USA bez special handling. Spec: `docs/superpowers/specs/2026-06-05-insider-trading-design.md`. Plan: `docs/superpowers/plans/2026-06-05-insider-trading.md`. Tests: `tests/test_financials.py` +12 testów mock-based (44/44 → 56/56 full suite).
```

(Uwaga: liczba testów się aktualizuje zgodnie z rzeczywistym stanem; sprawdź końcowo i podstaw realny wynik.)

- [ ] **Step 8.3: Commit**

```bash
git add CLAUDE.md
git commit -m "Update CLAUDE.md — F15 Insider Trading paragraph"
```

---

## Task 9: Final QA + push + MEMORY.md

**Files:**
- Modify: `C:\Users\m4x\.claude\projects\C--Users-m4x-Desktop-AI-ebook-white-new-A4\memory\MEMORY.md`
- Create: `C:\Users\m4x\.claude\projects\C--Users-m4x-Desktop-AI-ebook-white-new-A4\memory\project_gem_dashboard_insider_trading.md`

- [ ] **Step 9.1: Final test suite run**

```bash
cd C:\Users\m4x\Desktop\AI\gem-dashboard
./venv/Scripts/python.exe -m pytest tests/ -v 2>&1 | tail -10
```

Expected: 46/46 PASS (34 base + 12 nowe insider/major).

(Liczba dokładna może być 44-46 zależnie czy dotychczas 34 czy 33 — sprawdź realny output.)

- [ ] **Step 9.2: Verify commits ahead**

```bash
git log origin/main..HEAD --oneline
```

Powinno być **9 commitów** (spec `24cade2` + 8 task commits Task 1-8).

- [ ] **Step 9.3: Push do main**

```bash
git push origin main
```

Streamlit Cloud auto-redeploy ~3-5 min.

- [ ] **Step 9.4: Manual QA na produkcji**

Otwórz `https://gem-dashboard.streamlit.app/`:
1. Sidebar → **📈 S&P 500** (page 7)
2. Tab **"📈 Sprawozdania Q"** (tab 8)
3. **🏢 Deep dive** view → wybierz ticker → "Pokaż szczegóły"
4. W deep dive sprawdź **5. sub-tab "👥 Insiders"** (po Cash Flow)
5. Test matrix:
   - [ ] **AAPL** — wszystkie 6 sekcji renderują, Major Holders cards mają realne %, Transactions ma Tim Cook sells, Institutional donut pokazuje Vanguard/BlackRock top
   - [ ] **JPM** — bank USA, brak special handling, dane są (Insiders + Institutional)
   - [ ] **TSLA** — różne transaction types (Elon: Sale/Exercise/Conversion), Type column ma "Sell"/"Buy"/"Exercise of Options"
   - [ ] **MSFT** — institutional dominance (Vanguard/BlackRock w top)
6. **GPW test** — page 8 (🇵🇱 GPW), tab Sprawozdania Q, Deep dive:
   - [ ] **PKO.WA** — sub-tab Insiders → **info box** ("Brak danych... ESPI...") + link do gpw.pl
   - [ ] **11B.WA** — analogicznie info box
   - [ ] **KGH.WA** — analogicznie info box
7. **F14 cross-link sanity** — Earnings Calendar (page 22) → wybierz AAPL → "Pokaż szczegóły" → page 7 tab 8 deep dive z 5 sub-tabami, sub5 "Insiders" działa

- [ ] **Step 9.5: MEMORY.md entry**

Najpierw utwórz topic file `project_gem_dashboard_insider_trading.md`:

```markdown
---
name: project-gem-dashboard-insider-trading
description: F15 Insider Trading & Institutional — WGRANE YYYY-MM-DD, 5. sub-tab "Insiders" w F13 deep dive z 6 sekcjami + 2 wykresami
metadata:
  type: project
---

# F15 Insider Trading — WGRANE YYYY-MM-DD

**Final commit:** `<HASH>` na main. Live: `gem-dashboard.streamlit.app` → SP500/GPW → Sprawozdania Q → Deep dive → 5. sub-tab "👥 Insiders".

## Co zostało dodane

**Data layer (`data/financials.py` — rozszerzony +~250 LOC):**
- `_normalize_transaction_type(raw)` — Sale variants → Sell, Purchase → Buy, Exercise/Conversion zostawione (split "(")
- `fetch_insider_transactions(ticker)` — historia 6mc z normalize Type
- `fetch_insider_purchases(ticker)` — agregat 6mc
- `fetch_insider_roster_holders(ticker)` — kto z zarządu trzyma
- `fetch_institutional_holders(ticker)` — top 10 funduszy
- `fetch_mutualfund_holders(ticker)` — top 10 mutual funds
- `fetch_major_holders(ticker)` — dict {insider_pct, institutional_pct, institutional_count, float_pct}, defensywny parser dict|DataFrame

**UI layer (`components/financials_ui.py` — rozszerzony +~250 LOC):**
- `_render_insiders_tab(ticker)` — 6 sekcji (Major / Purchases / Transactions+bar / Roster / Institutional+pie / Mutual Fund)
- `_chart_insider_net_per_month(transactions_df)` — Plotly bar (green/red per miesiąc 6mc, reindex puste miesiące)
- `_chart_institutional_pie(institutional_df)` — Plotly donut top 10 + Reszta (gold variants + grays)
- 5. sub-tab "👥 Insiders" w `render_sprawozdania_deep_dive`

**Tests:** `tests/test_financials.py` +12 testów mock-based.

## Decyzje architektoniczne

- 5. sub-tab w F13 (nie nowa strona) — pełen kontekst spółki w jednym miejscu
- Cache **in-memory only** (brak parquet — lekkie endpointy ~5-30 rows DF)
- GPW fallback: wszystkie 6 None → info box (yfinance nie ma SEC Form 4 dla PL)
- Banki USA bez special handling
- Format Value: zawsze `$` USD (yfinance natural)

## v2 backlog

- Bulk screener "kto najwięcej kupił w SP500 ostatnio"
- Cross-link transactions → F14 Earnings Calendar (insider sale przed earnings = red flag)
- Alerty z watchlistu (CEO/CFO kupili >$X)
- Polskie ESPI scraping (gpw.pl)
- Insider sentiment composite score

## Powiązane

- [[project-gem-dashboard-sprawozdania-q]] — F13 (host dla 5. sub-tab)
- [[project-gem-dashboard-earnings-calendar]] — F14 (cross-link do F13 deep dive)
- [[feedback-yfinance-flaky-endpoints]] — manual QA pattern (każdy endpoint izolowany)
```

(YYYY-MM-DD + `<HASH>` podstaw z `git log -1 --oneline`.)

Następnie dodaj 1-liniowy entry w `MEMORY.md` w sekcji "Projekt: gem-dashboard" (po wpisie F14 Earnings Calendar):

```markdown
- [F15 Insider Trading & Institutional — WGRANE YYYY-MM-DD](project_gem_dashboard_insider_trading.md) — 5. sub-tab "Insiders" w F13 deep dive (SP500+GPW): Major Holders + Purchases + Transactions (+bar net) + Roster + Institutional (+donut top 10) + Mutual Fund. 6 funkcji yfinance + 2 chart helpers. GPW fallback (info box). Final commit `<HASH>`. ~56 tests PASS.
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Helper `_normalize_transaction_type` (Sale→Sell, Purchase→Buy, Exercise zostawione) — Task 1
- ✅ `fetch_insider_transactions` z normalize Type — Task 2
- ✅ `fetch_insider_purchases` — Task 3
- ✅ `fetch_insider_roster_holders` — Task 3
- ✅ `fetch_institutional_holders` — Task 4
- ✅ `fetch_mutualfund_holders` — Task 4
- ✅ `fetch_major_holders` z defensywnym parserem dict|DF — Task 5
- ✅ `_chart_insider_net_per_month` — Task 6
- ✅ `_chart_institutional_pie` — Task 6
- ✅ `_render_insiders_tab` z 6 sekcjami — Task 6
- ✅ GPW fallback (info box) — Task 6
- ✅ 5. sub-tab integration — Task 7
- ✅ CLAUDE.md F15 — Task 8
- ✅ Final QA + MEMORY.md — Task 9

**Placeholder scan:** ✅ Brak TBD/TODO. `<HASH>` i `YYYY-MM-DD` w MEMORY.md są zamierzone (wypełnia engineer z `git log`).

**Type consistency:**
- ✅ `_normalize_transaction_type(raw: str) -> str` — Task 1 + Task 2 (caller)
- ✅ `fetch_insider_transactions(ticker) -> DataFrame | None` — Task 2 + Task 6 (caller)
- ✅ `fetch_insider_purchases` / `fetch_insider_roster_holders` / `fetch_institutional_holders` / `fetch_mutualfund_holders` — wszystko zwraca `DataFrame | None`
- ✅ `fetch_major_holders(ticker) -> dict | None` — Task 5 + Task 6 (caller używa `.get()` na dict)
- ✅ `_chart_insider_net_per_month(transactions_df)` + `_chart_institutional_pie(institutional_df)` — sygnatury spójne Task 6 (impl) + caller w `_render_insiders_tab`
- ✅ `_render_insiders_tab(ticker)` — Task 6 (impl) + Task 7 (caller w `with sub5`)

**No spec requirement gaps detected.**
