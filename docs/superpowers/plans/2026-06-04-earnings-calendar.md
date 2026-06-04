# Earnings Calendar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nowa strona `pages/22_earnings_calendar.py` — kalendarz nadchodzących i niedawnych raportów (±28 dni) dla SP500 + GPW, z watchlist w localStorage i cross-link do F13 Sprawozdania Q deep dive.

**Architecture:** Rozszerzenie `data/financials.py` o `fetch_earnings_dates(ticker)` + `bulk_fetch_earnings_calendar(universe)` (ThreadPool + parquet cache 24h, filter ETF). Nowy `components/watchlist.py` (localStorage, cross-feature). Nowa strona `pages/22_earnings_calendar.py` z `st.data_editor` (checkbox ⭐) + Plotly heatmapa 8 tygodni + cross-link `st.switch_page` do F13.

**Tech Stack:** Streamlit 1.55+, yfinance 0.2.50+ (`Ticker.earnings_dates`), pandas 2.0+ (uwaga: `DataFrame.map`, nie `applymap` — patrz F13 hotfix `8f73d6e`), plotly 5.18+, pyarrow (parquet), streamlit-local-storage 0.0.25+, pytest>=7.4.0.

**Reference:** Spec `docs/superpowers/specs/2026-06-04-earnings-calendar-design.md` (commit `ab65268`).

---

## File Structure

**Tworzymy:**
- `pages/22_earnings_calendar.py` — UI strony (~300 LOC)
- `components/watchlist.py` — localStorage cross-feature (~70 LOC)
- `tests/test_calendar.py` — unit tests (~200 LOC)
- `data/cache/earnings_dates/` — auto-create przy pierwszym fetch

**Modyfikujemy:**
- `data/financials.py` — +`fetch_earnings_dates` + `bulk_fetch_earnings_calendar` + `_get_etf_set` helper (~180 LOC)
- `components/auth.py` — `PAGE_INFO[22] = ("📅", "Earnings Calendar", "Kalendarz nadchodzacych i niedawnych raportow SP500+GPW")`
- `app.py` — dodać tuple `(22, "📅", "Earnings Calendar", ..., "pages/22_earnings_calendar.py")` w gridzie kart
- `CLAUDE.md` — sekcja "Pages" + nowy F14 w Key Design Decisions

**Bez zmian:**
- `pages/7_sp500.py`, `pages/8_gpw.py` — F13 reaguje na session_state pre-set (już działa po hotfix `b1f8502`)
- `components/financials_ui.py` — F13 deep dive bez zmian

---

## Task 1: Helpery `_status_badge` + `_detect_market` + ETF set

**Files:**
- Create: `tests/test_calendar.py`
- Modify: `data/financials.py` (dopisać na końcu helpery, używane też przez page 22)

- [ ] **Step 1.1: Test failing — `tests/test_calendar.py`**

Utwórz `tests/test_calendar.py`:

```python
"""Testy dla pages/22_earnings_calendar.py + watchlist + earnings calendar helpers."""
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock


def test_status_badge_today():
    from data.financials import _status_badge
    today = pd.Timestamp.now().normalize()
    assert "🔥 DZIŚ" in _status_badge(today, None, None)


def test_status_badge_future_within_week():
    from data.financials import _status_badge
    today = pd.Timestamp.now().normalize()
    date = today + pd.Timedelta(days=3)
    badge = _status_badge(date, None, None)
    assert "🔜" in badge
    assert "3d" in badge


def test_status_badge_future_2weeks():
    from data.financials import _status_badge
    today = pd.Timestamp.now().normalize()
    date = today + pd.Timedelta(days=10)
    assert "⏰" in _status_badge(date, None, None)


def test_status_badge_future_far():
    from data.financials import _status_badge
    today = pd.Timestamp.now().normalize()
    date = today + pd.Timedelta(days=25)
    badge = _status_badge(date, None, None)
    assert "📅" in badge


def test_status_badge_past_beat():
    from data.financials import _status_badge
    today = pd.Timestamp.now().normalize()
    date = today - pd.Timedelta(days=5)
    badge = _status_badge(date, 1.5, 1.4)
    assert "✅ Beat" in badge
    assert "5d temu" in badge


def test_status_badge_past_miss():
    from data.financials import _status_badge
    today = pd.Timestamp.now().normalize()
    date = today - pd.Timedelta(days=5)
    badge = _status_badge(date, 1.3, 1.4)
    assert "❌ Miss" in badge


def test_status_badge_past_no_actual():
    from data.financials import _status_badge
    today = pd.Timestamp.now().normalize()
    date = today - pd.Timedelta(days=5)
    badge = _status_badge(date, None, 1.4)
    assert "⚪" in badge


def test_detect_market_sp500():
    from data.financials import _detect_market
    assert _detect_market("AAPL") == "SP500"
    assert _detect_market("MSFT") == "SP500"


def test_detect_market_gpw():
    from data.financials import _detect_market
    assert _detect_market("PKO.WA") == "GPW"
    assert _detect_market("CDR.WA") == "GPW"


def test_detect_market_etf():
    from data.financials import _detect_market
    # ETF typowo w universe (VOO/QQQ z etf_universe.py)
    assert _detect_market("VOO") == "ETF"
    assert _detect_market("QQQ") == "ETF"


def test_get_etf_set_contains_known():
    from data.financials import _get_etf_set
    etf_set = _get_etf_set()
    assert "VOO" in etf_set
    assert "QQQ" in etf_set
    # AAPL nie powinien byc w ETF set
    assert "AAPL" not in etf_set
```

- [ ] **Step 1.2: Run tests — verify FAIL**

```bash
cd C:\Users\m4x\Desktop\AI\gem-dashboard
./venv/Scripts/python.exe -m pytest tests/test_calendar.py -v
```

Expected: 10 testów FAIL z `ImportError: cannot import name '_status_badge' from 'data.financials'`.

- [ ] **Step 1.3: Implementacja helperów w `data/financials.py`**

Sprawdź gdzie kończy się plik (powinien po `bulk_fetch_earnings_history`):

```bash
tail -5 data/financials.py
```

Dopisz na końcu pliku:

```python


# ---------------------------------------------------------------------------
# Earnings Calendar helpers (page 22)
# ---------------------------------------------------------------------------

def _status_badge(date, eps_act, eps_est) -> str:
    """Badge stanu raportu: Future (🔜/⏰/📅), Past (✅/❌/⚪), DZIŚ (🔥).

    date: datetime/Timestamp daty raportu
    eps_act, eps_est: floaty lub None
    """
    today = pd.Timestamp.now().normalize()
    ts = pd.Timestamp(date).normalize()
    days_diff = (ts - today).days

    if days_diff == 0:
        return "🔥 DZIŚ"
    if days_diff > 0:  # Future
        if days_diff <= 7:
            return f"🔜 W {days_diff}d"
        if days_diff <= 14:
            return f"⏰ W {days_diff}d"
        return f"📅 {ts.strftime('%d.%m')}"
    # Past
    abs_diff = abs(days_diff)
    if pd.notna(eps_act) and pd.notna(eps_est):
        if eps_act > eps_est:
            return f"✅ Beat ({abs_diff}d temu)"
        return f"❌ Miss ({abs_diff}d temu)"
    return f"⚪ {abs_diff}d temu"


def _get_etf_set() -> set[str]:
    """Set tickerow ETF z data/etf_universe.py — uzywany do filtrowania
    ETF z earnings calendar (ETF nie maja earnings, tylko distributions).
    """
    from data.etf_universe import ETF_NAMES
    return set(ETF_NAMES.keys())


def _detect_market(ticker: str) -> str:
    """Lookup ticker -> 'SP500' / 'GPW' / 'ETF'.

    Kolejnosc: SP500 (najwieksze coverage), potem .WA suffix dla GPW,
    potem ETF set. Fallback na 'UNKNOWN' gdy brak w zadnym.
    """
    from data.sp500_universe import ALL_SP500_TICKERS
    from data.gpw_universe import ALL_GPW_TICKERS

    if ticker in ALL_SP500_TICKERS:
        return "SP500"
    if ticker in ALL_GPW_TICKERS or ticker.endswith(".WA"):
        return "GPW"
    if ticker in _get_etf_set():
        return "ETF"
    return "UNKNOWN"
```

- [ ] **Step 1.4: Run tests — verify PASS**

```bash
./venv/Scripts/python.exe -m pytest tests/test_calendar.py -v
```

Expected: 10/10 PASS.

- [ ] **Step 1.5: Commit**

```bash
git add data/financials.py tests/test_calendar.py
git commit -m "Add _status_badge + _detect_market + _get_etf_set helpers (earnings calendar)"
```

---

## Task 2: `fetch_earnings_dates` + `bulk_fetch_earnings_calendar` z parquet cache

**Files:**
- Modify: `data/financials.py` (dopisać po helperach z Task 1)
- Modify: `tests/test_calendar.py` (dopisać 3 testy)
- Create: `data/cache/earnings_dates/` (auto przy pierwszym fetch)

- [ ] **Step 2.1: Dopisać testy do `tests/test_calendar.py`**

Dopisz na końcu pliku:

```python


def test_fetch_earnings_dates_normalizes_columns():
    """Mock yfinance Ticker.earnings_dates — normalize columns."""
    mock_df = pd.DataFrame({
        "EPS Estimate": [1.5, 1.6],
        "Reported EPS": [1.65, None],
        "Surprise(%)": [10.0, None],
    }, index=pd.to_datetime(["2026-05-01", "2026-07-30"]))

    mock_ticker = MagicMock()
    mock_ticker.earnings_dates = mock_df

    from data.financials import fetch_earnings_dates
    with patch("data.financials.yf.Ticker", return_value=mock_ticker), \
         patch("data.financials._cache_path_earnings_dates", return_value=None):
        result = fetch_earnings_dates("AAPL_TEST")

    assert result is not None
    assert "eps_estimate" in result.columns
    assert "eps_actual" in result.columns
    assert "eps_surprise_pct" in result.columns
    assert "is_future" in result.columns
    assert "q_label" in result.columns


def test_fetch_earnings_dates_returns_none_on_empty():
    mock_ticker = MagicMock()
    mock_ticker.earnings_dates = pd.DataFrame()

    from data.financials import fetch_earnings_dates
    with patch("data.financials.yf.Ticker", return_value=mock_ticker), \
         patch("data.financials._cache_path_earnings_dates", return_value=None):
        result = fetch_earnings_dates("EMPTY_TEST")

    assert result is None


def test_bulk_fetch_filters_etf():
    """ETF tickery nie powinny byc fetchowane (no earnings, oszczedza calls)."""
    fetch_calls = []

    def mock_fetch(ticker, **kwargs):
        fetch_calls.append(ticker)
        return pd.DataFrame({
            "eps_estimate": [1.5],
            "eps_actual": [1.6],
            "eps_surprise_pct": [6.7],
            "is_future": [False],
            "q_label": ["Q2'26"],
        }, index=pd.to_datetime(["2026-05-01"]))

    # Mock st.progress (nie chcemy wybuchu poza Streamlit)
    mock_progress = MagicMock()
    mock_progress.progress = MagicMock()
    mock_progress.empty = MagicMock()

    from data.financials import bulk_fetch_earnings_calendar
    # ETF set zawiera VOO, QQQ (z etf_universe.ETF_NAMES)
    with patch("data.financials.fetch_earnings_dates", side_effect=mock_fetch), \
         patch("data.financials.st.progress", return_value=mock_progress):
        result = bulk_fetch_earnings_calendar(("AAPL", "VOO", "QQQ", "MSFT"))

    # VOO, QQQ filtered out — tylko AAPL, MSFT wywołane
    assert "VOO" not in fetch_calls
    assert "QQQ" not in fetch_calls
    assert "AAPL" in fetch_calls
    assert "MSFT" in fetch_calls
    # Wynik DF ma tylko AAPL i MSFT wiersze
    assert set(result["ticker"].unique()).issubset({"AAPL", "MSFT"})
```

- [ ] **Step 2.2: Run tests — verify FAIL**

```bash
./venv/Scripts/python.exe -m pytest tests/test_calendar.py -v -k "earnings_dates or bulk_fetch_filters"
```

Expected: 3 nowe testy FAIL z `ImportError: cannot import name 'fetch_earnings_dates'`.

- [ ] **Step 2.3: Implementacja w `data/financials.py`**

Dopisz na końcu pliku (po helperach z Task 1):

```python


# ---------------------------------------------------------------------------
# Earnings Calendar — fetch_earnings_dates + bulk_fetch
# ---------------------------------------------------------------------------

CACHE_DIR_EARNINGS_DATES = Path(__file__).parent / "cache" / "earnings_dates"


def _cache_path_earnings_dates(ticker: str) -> Path | None:
    """Sciezka cache file dla earnings_dates. None jesli stale/missing."""
    CACHE_DIR_EARNINGS_DATES.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR_EARNINGS_DATES / f"{ticker}.parquet"
    if not path.exists():
        return None
    age = pd.Timestamp.now().timestamp() - path.stat().st_mtime
    if age > CACHE_TTL_SECONDS:
        return None
    return path


def fetch_earnings_dates(ticker: str) -> pd.DataFrame | None:
    """Pobiera earnings dates (historia + future) dla tickera.

    yfinance Ticker.earnings_dates zwraca DF z indeksem DatetimeIndex
    + kolumnami: "EPS Estimate", "Reported EPS", "Surprise(%)".

    Returns DF z normalizowanymi kolumnami:
        eps_estimate, eps_actual, eps_surprise_pct, is_future, q_label
    Indeks: DatetimeIndex (tz_localize(None).normalize()).
    None gdy brak danych.

    Cache parquet 24h.
    """
    # Try cache first
    cache_path = _cache_path_earnings_dates(ticker)
    if cache_path is not None:
        try:
            return pd.read_parquet(cache_path, engine="pyarrow")
        except Exception:
            pass

    try:
        t = yf.Ticker(ticker, session=_get_yf_session())
        df = t.earnings_dates
    except Exception:
        return None

    if df is None or df.empty:
        return None

    out = df.copy()
    # Normalize index: tz-aware -> naive, normalize do daty
    out.index = pd.to_datetime(out.index).tz_localize(None).normalize()

    rename = {
        "EPS Estimate": "eps_estimate",
        "Reported EPS": "eps_actual",
        "Surprise(%)": "eps_surprise_pct",
    }
    out = out.rename(columns={c: rename[c] for c in out.columns if c in rename})

    # Zostaw tylko interesujace kolumny
    keep = [c for c in ["eps_estimate", "eps_actual", "eps_surprise_pct"] if c in out.columns]
    if not keep:
        return None
    out = out[keep]

    # Dodatkowe kolumny
    today = pd.Timestamp.now().normalize()
    out["is_future"] = out.index > today
    out["q_label"] = [_quarter_label(d) for d in out.index]

    # Save cache (best effort)
    cache_save_path = CACHE_DIR_EARNINGS_DATES / f"{ticker}.parquet"
    try:
        out.to_parquet(cache_save_path, engine="pyarrow")
    except Exception:
        pass

    return out


def _fetch_calendar_for_one(ticker: str, retries: int = 3) -> pd.DataFrame | None:
    """Pobiera earnings_dates dla 1 tickera z retry. Zwraca DF lub None.

    DF rows = daty raportow, kolumny zgodne z fetch_earnings_dates.
    """
    df = None
    for attempt in range(retries):
        try:
            df = fetch_earnings_dates(ticker)
            if df is None or df.empty:
                return None
            break
        except Exception:
            if attempt == retries - 1:
                return None
            time.sleep(2 ** attempt)

    if df is None or df.empty:
        return None
    return df


@st.cache_data(ttl=86400, show_spinner="Pobieram kalendarz earnings...")
def bulk_fetch_earnings_calendar(
    tickers_tuple: tuple[str, ...],
    max_workers: int = 8,
    window_days: int = 28,
) -> pd.DataFrame:
    """Bulk fetch earnings dates dla universe.

    Filtruje ETF z input (no earnings). Window: data ± window_days od dzis.

    Returns DataFrame z kolumnami:
        ticker, date, q_label, eps_estimate, eps_actual,
        eps_surprise_pct, is_future, market, name, sector
    """
    # Filter ETF (no earnings)
    etf_set = _get_etf_set()
    eligible = [t for t in tickers_tuple if t not in etf_set]

    if not eligible:
        return pd.DataFrame()

    today = pd.Timestamp.now().normalize()
    window_start = today - pd.Timedelta(days=window_days)
    window_end = today + pd.Timedelta(days=window_days)

    rows: list[dict] = []
    total = len(eligible)
    progress_bar = st.progress(0.0, text=f"Pobieram 0/{total}...")
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(_fetch_calendar_for_one, t): t
            for t in eligible
        }
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                df = future.result()
            except Exception:
                df = None

            if df is not None and not df.empty:
                # Filter window
                in_window = df[(df.index >= window_start) & (df.index <= window_end)]
                for date, row in in_window.iterrows():
                    rows.append({
                        "ticker": ticker,
                        "date": date,
                        "q_label": row.get("q_label", ""),
                        "eps_estimate": row.get("eps_estimate", float("nan")),
                        "eps_actual": row.get("eps_actual", float("nan")),
                        "eps_surprise_pct": row.get("eps_surprise_pct", float("nan")),
                        "is_future": bool(row.get("is_future", False)),
                        "market": _detect_market(ticker),
                    })

            completed += 1
            progress_bar.progress(
                completed / total,
                text=f"Pobieram {completed}/{total}: {ticker}",
            )

    progress_bar.empty()

    if not rows:
        return pd.DataFrame(columns=[
            "ticker", "date", "q_label", "eps_estimate", "eps_actual",
            "eps_surprise_pct", "is_future", "market", "name", "sector",
        ])

    out = pd.DataFrame(rows)
    # Sort: distance from today ascending
    out["_abs_days"] = (out["date"] - today).abs()
    out = out.sort_values("_abs_days").drop(columns=["_abs_days"]).reset_index(drop=True)

    # Lookup name + sector (po sortowaniu zeby bylo szybciej)
    from data.sp500_universe import SP500_NAMES, SP500_SECTOR_MAP
    from data.gpw_universe import GPW_CATEGORIES

    # Flat GPW name lookup
    gpw_names = {}
    gpw_index = {}
    for idx_name, idx_dict in GPW_CATEGORIES.items():
        for tk, nm in idx_dict.items():
            gpw_names[tk] = nm
            gpw_index[tk] = idx_name

    def _name_for(t):
        if t in SP500_NAMES:
            return SP500_NAMES[t]
        if t in gpw_names:
            return gpw_names[t]
        return t

    def _sector_for(t):
        if t in SP500_SECTOR_MAP:
            return SP500_SECTOR_MAP[t]
        if t in gpw_index:
            return gpw_index[t]
        return "—"

    out["name"] = out["ticker"].map(_name_for)
    out["sector"] = out["ticker"].map(_sector_for)

    return out
```

- [ ] **Step 2.4: Run tests — verify PASS**

```bash
./venv/Scripts/python.exe -m pytest tests/test_calendar.py -v
```

Expected: 13/13 PASS (10 z Task 1 + 3 nowe).

- [ ] **Step 2.5: Commit**

```bash
git add data/financials.py tests/test_calendar.py
git commit -m "Add fetch_earnings_dates + bulk_fetch_earnings_calendar (parquet cache, filter ETF)"
```

---

## Task 3: `components/watchlist.py` — localStorage module

**Files:**
- Create: `components/watchlist.py`
- Modify: `tests/test_calendar.py` (dopisać 4 testy)

- [ ] **Step 3.1: Dopisać testy do `tests/test_calendar.py`**

Dopisz na końcu:

```python


def test_watchlist_get_empty():
    from components.watchlist import get_watchlist
    ls_mock = MagicMock()
    ls_mock.getItem.return_value = None
    result = get_watchlist(ls_mock)
    assert result == set()


def test_watchlist_get_corrupt_json():
    from components.watchlist import get_watchlist
    ls_mock = MagicMock()
    ls_mock.getItem.return_value = "!@#invalid"
    result = get_watchlist(ls_mock)
    assert result == set()


def test_watchlist_toggle_add():
    from components.watchlist import toggle_ticker, WATCHLIST_KEY
    ls_mock = MagicMock()
    ls_mock.getItem.return_value = "[]"
    result = toggle_ticker(ls_mock, "AAPL")
    assert result is True  # in watchlist after toggle
    ls_mock.setItem.assert_called_with(WATCHLIST_KEY, '["AAPL"]')


def test_watchlist_toggle_remove():
    from components.watchlist import toggle_ticker, WATCHLIST_KEY
    ls_mock = MagicMock()
    ls_mock.getItem.return_value = '["AAPL", "MSFT"]'
    result = toggle_ticker(ls_mock, "AAPL")
    assert result is False  # not in watchlist after toggle
    ls_mock.setItem.assert_called_with(WATCHLIST_KEY, '["MSFT"]')
```

- [ ] **Step 3.2: Run tests — verify FAIL**

```bash
./venv/Scripts/python.exe -m pytest tests/test_calendar.py -v -k watchlist
```

Expected: 4 FAIL z `ImportError: cannot import name 'get_watchlist' from 'components.watchlist'`.

- [ ] **Step 3.3: Implementacja `components/watchlist.py`**

```python
"""Watchlist user-defined (localStorage przez streamlit-local-storage).

Cross-feature module — uzywany przez:
- pages/22_earnings_calendar.py (filter "tylko watchlist")
- (v2) pages/7_sp500.py + 8_gpw.py screener F13 (filter)

Format storage: JSON array tickerow (sorted, deduplicated).
Klucz wersjonowany ("_v1") na wypadek przyszlej migracji.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from streamlit_local_storage import LocalStorage

WATCHLIST_KEY = "gem_dashboard_watchlist_v1"


def get_watchlist(ls: "LocalStorage") -> set[str]:
    """Zwraca set tickerow w watchlistui. Pusty set gdy brak / corrupt."""
    raw = ls.getItem(WATCHLIST_KEY)
    if not raw:
        return set()
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return set()
        return set(str(t) for t in data)
    except (json.JSONDecodeError, TypeError, ValueError):
        return set()


def save_watchlist(ls: "LocalStorage", tickers: set[str]) -> None:
    """Zapisuje watchlist (sorted JSON array)."""
    ls.setItem(WATCHLIST_KEY, json.dumps(sorted(tickers)))


def toggle_ticker(ls: "LocalStorage", ticker: str) -> bool:
    """Toggle ticker w watchlistui.

    Returns: True jesli w watchlistui PO toggle, False wpp.
    """
    wl = get_watchlist(ls)
    if ticker in wl:
        wl.discard(ticker)
        save_watchlist(ls, wl)
        return False
    wl.add(ticker)
    save_watchlist(ls, wl)
    return True
```

- [ ] **Step 3.4: Run tests — verify PASS**

```bash
./venv/Scripts/python.exe -m pytest tests/test_calendar.py -v
```

Expected: 17/17 PASS (13 + 4 nowe).

- [ ] **Step 3.5: Commit**

```bash
git add components/watchlist.py tests/test_calendar.py
git commit -m "Add components/watchlist.py — localStorage cross-feature module"
```

---

## Task 4: Page 22 skeleton — config + header + filtry + fetch + summary

**Files:**
- Create: `pages/22_earnings_calendar.py`

- [ ] **Step 4.1: Tworzymy plik z minimalną strukturą**

```python
"""Strona 22: Earnings Calendar — nadchodzace + niedawne raporty.

Window: data.today() ± 28 dni.
Universe: SP500 (456) + GPW (121) = 577. ETF wykluczone (no earnings).

Spec: docs/superpowers/specs/2026-06-04-earnings-calendar-design.md
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_local_storage import LocalStorage

from components.auth import require_premium
from components.sidebar import setup_sidebar, render_footer
from components.watchlist import get_watchlist, toggle_ticker
from data.financials import (
    _detect_market,
    _status_badge,
    bulk_fetch_earnings_calendar,
)
from data.gpw_universe import ALL_GPW_TICKERS
from data.sp500_universe import ALL_SP500_TICKERS


# ---------------------------------------------------------------------------
# Module-level helpers (regula @st.fragment: PRZED `with tab:` blokiem)
# ---------------------------------------------------------------------------

def _navigate_to_deep_dive(ticker: str) -> None:
    """Przeskakuje do F13 deep dive dla wybranego tickera.

    Pattern session_state zgodny z F13 hotfix (commit b1f8502):
    osobna 'pending' flaga (nie widget key) + `st.switch_page`.
    """
    market = _detect_market(ticker)
    if market == "SP500":
        st.session_state["sp500_deep_dive_ticker"] = ticker
        st.session_state["sp500_pending_view"] = "deep_dive"
        st.switch_page("pages/7_sp500.py")
    elif market == "GPW":
        st.session_state["gpw_deep_dive_ticker"] = ticker
        st.session_state["gpw_pending_view"] = "deep_dive"
        st.switch_page("pages/8_gpw.py")
    else:
        st.warning(f"Deep dive niedostepny dla ETF/UNKNOWN ({ticker}).")


# ---------------------------------------------------------------------------
# Page config + auth + sidebar
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Earnings Calendar",
    page_icon="📅",
    layout="wide",
)
setup_sidebar()
if not require_premium(22):
    st.stop()

# Header
st.markdown("# 📅 Earnings Calendar")
st.caption(
    "Nadchodzace i niedawne raporty (±28 dni) dla SP500 + GPW. "
    "Kliknij ⭐ aby dodac spolke do watchlistu. "
    "ETF wykluczone — nie maja earnings."
)

# Universe
universe = tuple(ALL_SP500_TICKERS + ALL_GPW_TICKERS)

# Watchlist (localStorage)
ls = LocalStorage()
watchlist = get_watchlist(ls)

# ---------------------------------------------------------------------------
# FILTRY (expander)
# ---------------------------------------------------------------------------

with st.expander("Filtry", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        market_filter = st.radio(
            "Market",
            options=["Wszystkie", "SP500", "GPW"],
            horizontal=True,
            key="calendar_market",
        )
        status_filter = st.radio(
            "Status",
            options=["Wszystkie", "Future", "Past"],
            horizontal=True,
            key="calendar_status",
        )
    with col2:
        sector_filter = st.multiselect(
            "Sektor (multiselect)",
            options=[],  # populated po fetch
            default=[],
            key="calendar_sector",
        )
        only_watchlist = st.checkbox(
            "⭐ Tylko watchlist",
            value=False,
            disabled=len(watchlist) == 0,
            help="Watchlist pusty — kliknij ⭐ w tabeli aby dodac." if not watchlist else None,
            key="calendar_only_watchlist",
        )
    with col3:
        sort_by = st.selectbox(
            "Sort",
            options=[
                "Data (najblizej dzis)",
                "Data (chronologicznie)",
                "EPS surprise % (past)",
                "Ticker A-Z",
            ],
            index=0,
            key="calendar_sort",
        )
        refresh = st.button("🔄 Refresh cache", key="calendar_refresh")
        if refresh:
            st.cache_data.clear()
            st.rerun()

# ---------------------------------------------------------------------------
# BULK FETCH (cache 24h)
# ---------------------------------------------------------------------------

df = bulk_fetch_earnings_calendar(universe)

if df.empty:
    st.warning("Brak danych earnings w wybranym oknie ±28 dni.")
    render_footer()
    st.stop()

# Populate sector filter options (po fetch)
all_sectors = sorted(df["sector"].dropna().unique())
# (Nie aktualizujemy session_state widgetu — Streamlit zarzadza index)

# ---------------------------------------------------------------------------
# APPLY FILTRY
# ---------------------------------------------------------------------------

filtered = df.copy()
if market_filter != "Wszystkie":
    filtered = filtered[filtered["market"] == market_filter]
if status_filter == "Future":
    filtered = filtered[filtered["is_future"]]
elif status_filter == "Past":
    filtered = filtered[~filtered["is_future"]]
if sector_filter:
    filtered = filtered[filtered["sector"].isin(sector_filter)]
if only_watchlist:
    filtered = filtered[filtered["ticker"].isin(watchlist)]

# ---------------------------------------------------------------------------
# SUMMARY CARDS (4 metryki)
# ---------------------------------------------------------------------------

total = len(df)
n_future = int(df["is_future"].sum())
today = pd.Timestamp.now().normalize()
n_this_week = int(((df["date"] >= today) & (df["date"] <= today + pd.Timedelta(days=7))).sum())
past_df = df[~df["is_future"]]
n_beat = int((past_df["eps_actual"] > past_df["eps_estimate"]).sum())
n_miss = int((past_df["eps_actual"] < past_df["eps_estimate"]).sum())
avg_surprise = past_df["eps_surprise_pct"].mean()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total ±28d", f"{total}")
c2.metric("Future (nadchodzace)", f"{n_future}", f"{n_this_week} w tym tyg.")
c3.metric("Past Beat / Miss", f"{n_beat} / {n_miss}",
          f"{n_beat/(n_beat+n_miss)*100:.0f}% beat" if (n_beat + n_miss) > 0 else "")
c4.metric("Avg surprise %", f"{avg_surprise:+.1f}%" if pd.notna(avg_surprise) else "—")

st.markdown("---")

# Placeholder dla Task 5 (heatmapa) i Task 6 (tabela) i Task 7 (cross-link)
st.info("🚧 Heatmapa, tabela i cross-link dodane w kolejnych taskach.")

render_footer()
```

- [ ] **Step 4.2: Smoke test — import + AST parse**

```bash
./venv/Scripts/python.exe -c "
import ast
with open('pages/22_earnings_calendar.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('Syntax OK')
"
```

Expected: `Syntax OK`.

- [ ] **Step 4.3: Smoke test imports**

```bash
./venv/Scripts/python.exe -c "
import ast
with open('pages/22_earnings_calendar.py', encoding='utf-8') as f:
    tree = ast.parse(f.read())
for node in tree.body:
    if isinstance(node, ast.ImportFrom):
        print(f'from {node.module} import {[a.name for a in node.names]}')
"
```

Sprawdź że wszystkie importy resolveable.

- [ ] **Step 4.4: Test suite still passing**

```bash
./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```

Expected: 17/17 PASS.

- [ ] **Step 4.5: Commit**

```bash
git add pages/22_earnings_calendar.py
git commit -m "Add pages/22_earnings_calendar.py skeleton (header + filtry + summary)"
```

---

## Task 5: Heatmapa Plotly 8 tygodni

**Files:**
- Modify: `pages/22_earnings_calendar.py`

- [ ] **Step 5.1: Dodać helper `_render_heatmap` PRZED main logic (po `_navigate_to_deep_dive`)**

Znajdź sekcję module-level helpers w `pages/22_earnings_calendar.py` (po `_navigate_to_deep_dive`) i dopisz:

```python


def _render_heatmap(df: pd.DataFrame, weeks_back: int = 3, weeks_fwd: int = 4) -> None:
    """Renderuje Plotly calendar heatmap 8 tygodni.

    Komorka = jeden dzien (Pon-Pt, weekendy ukryte).
    Kolor = ilosc raportow tego dnia (gold scale).
    Dzis = czerwona ramka.
    """
    today = pd.Timestamp.now().normalize()
    start = today - pd.Timedelta(weeks=weeks_back)
    end = today + pd.Timedelta(weeks=weeks_fwd)

    # Wszystkie dni robocze (Mon-Fri) w window
    all_days = pd.bdate_range(start, end)

    # Aggregate: data -> lista tickerow
    by_day = df.groupby(df["date"].dt.normalize())["ticker"].apply(list).to_dict()

    # Build matrix: rows = tygodnie, cols = dni (Pon-Pt)
    matrix = []
    week_labels = []
    cell_data = []  # tickery dla hover
    current_week_start = start - pd.Timedelta(days=start.weekday())  # poniedzialek

    while current_week_start <= end:
        row = []
        row_data = []
        for dow in range(5):  # Pon-Pt
            day = current_week_start + pd.Timedelta(days=dow)
            if day < start or day > end:
                row.append(None)
                row_data.append(None)
                continue
            tickers_for_day = by_day.get(day, [])
            row.append(len(tickers_for_day))
            row_data.append(tickers_for_day)

        # Label tygodnia: numer relatywny do dziś
        week_diff = ((current_week_start - today).days) // 7
        week_labels.append(f"T{week_diff:+d}")
        matrix.append(row)
        cell_data.append(row_data)
        current_week_start += pd.Timedelta(weeks=1)

    # Hover text builder
    hover_text = []
    for week_row, day_idx in zip(cell_data, range(len(cell_data))):
        hover_row = []
        for cell_tickers in week_row:
            if cell_tickers is None or len(cell_tickers) == 0:
                hover_row.append("")
            else:
                preview = cell_tickers[:5]
                more = len(cell_tickers) - 5
                hover = f"{len(cell_tickers)} raporty:<br>" + "<br>".join(f"• {t}" for t in preview)
                if more > 0:
                    hover += f"<br>+ {more} wiecej"
                hover_row.append(hover)
        hover_text.append(hover_row)

    # Heatmap
    fig = go.Figure(go.Heatmap(
        z=matrix,
        x=["Pon", "Wt", "Sr", "Cz", "Pt"],
        y=week_labels,
        colorscale=[[0, "#1F2937"], [0.5, "#C9A84C"], [1, "#FFD700"]],
        showscale=True,
        colorbar=dict(title="Raporty"),
        hovertext=hover_text,
        hovertemplate="%{hovertext}<extra></extra>",
        zmin=0,
    ))

    # Dziś = ramka (annotacja)
    today_dow = today.weekday()
    if today_dow < 5:  # tylko Pon-Pt
        today_week_diff = 0  # dziś jest w tygodniu T0
        # Znajdz row index dla T0
        try:
            t0_idx = week_labels.index("T+0")
        except ValueError:
            t0_idx = -1
        if t0_idx >= 0:
            fig.add_shape(
                type="rect",
                x0=today_dow - 0.5, x1=today_dow + 0.5,
                y0=t0_idx - 0.5, y1=t0_idx + 0.5,
                line=dict(color="#EF4444", width=2),
                fillcolor="rgba(0,0,0,0)",
            )

    fig.update_layout(
        title="Kalendarz miesiecy — 8 tygodni (T-3 do T+4)",
        template="plotly_dark",
        height=400,
        yaxis=dict(autorange="reversed"),  # T-3 na gorze, T+4 na dole
        margin=dict(l=40, r=40, t=60, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)
```

- [ ] **Step 5.2: Wywołać `_render_heatmap` w main code**

Znajdź placeholder `st.info("🚧 Heatmapa, tabela...")` i zamień na:

```python
# ---------------------------------------------------------------------------
# HEATMAPA (8 tygodni)
# ---------------------------------------------------------------------------

_render_heatmap(filtered)

st.markdown("---")

# Placeholder dla Task 6 (tabela) i Task 7 (cross-link)
st.info("🚧 Tabela i cross-link dodane w kolejnych taskach.")
```

- [ ] **Step 5.3: Syntax check**

```bash
./venv/Scripts/python.exe -c "
import ast
with open('pages/22_earnings_calendar.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('Syntax OK')
"
```

- [ ] **Step 5.4: Regression tests**

```bash
./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```

Expected: 17/17 PASS.

- [ ] **Step 5.5: Commit**

```bash
git add pages/22_earnings_calendar.py
git commit -m "Add Plotly heatmap 8 weeks (T-3..T+4) z hover tickers + today ramka"
```

---

## Task 6: Tabela `st.data_editor` + watchlist toggle + CSV export

**Files:**
- Modify: `pages/22_earnings_calendar.py`

- [ ] **Step 6.1: Dodać helper `_render_calendar_table` (po `_render_heatmap`)**

Znajdź sekcję helperów modułu i dopisz:

```python


def _apply_sort(df: pd.DataFrame, sort_by: str) -> pd.DataFrame:
    """Sortowanie tabeli wedlug wybranej opcji."""
    today = pd.Timestamp.now().normalize()
    if sort_by == "Data (najblizej dzis)":
        df = df.copy()
        df["_abs_days"] = (df["date"] - today).abs()
        return df.sort_values("_abs_days").drop(columns=["_abs_days"])
    if sort_by == "Data (chronologicznie)":
        return df.sort_values("date")
    if sort_by == "EPS surprise % (past)":
        # NaN (future) na koncu
        return df.sort_values("eps_surprise_pct", ascending=False, na_position="last")
    if sort_by == "Ticker A-Z":
        return df.sort_values("ticker")
    return df


def _render_calendar_table(df: pd.DataFrame, watchlist: set[str], ls: LocalStorage) -> None:
    """Renderuje tabele st.data_editor z checkbox watchlist + CSV export.

    Po edycji checkboxa: diff vs current watchlist, toggle w localStorage,
    st.rerun() dla refresh state.
    """
    if df.empty:
        st.info("Brak wynikow po filtrach.")
        return

    # Status badge per row
    df = df.copy()
    df["status"] = df.apply(
        lambda r: _status_badge(r["date"], r.get("eps_actual"), r.get("eps_estimate")),
        axis=1,
    )
    df["in_watchlist"] = df["ticker"].isin(watchlist)

    # Format kolumn dla wyswietlania
    display_cols = [
        "in_watchlist", "ticker", "name", "market", "sector",
        "date", "q_label", "eps_estimate", "eps_actual",
        "eps_surprise_pct", "status",
    ]
    display = df[display_cols].copy()
    display = display.rename(columns={
        "in_watchlist": "⭐",
        "ticker": "Ticker",
        "name": "Nazwa",
        "market": "Market",
        "sector": "Sektor",
        "date": "Data",
        "q_label": "Q",
        "eps_estimate": "EPS est",
        "eps_actual": "EPS act",
        "eps_surprise_pct": "Δ%",
        "status": "Status",
    })

    # Edytowalny tylko ⭐
    disabled_cols = [c for c in display.columns if c != "⭐"]

    edited = st.data_editor(
        display,
        column_config={
            "⭐": st.column_config.CheckboxColumn("⭐", width="small"),
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Market": st.column_config.TextColumn("Market", width="small"),
            "Q": st.column_config.TextColumn("Q", width="small"),
            "EPS est": st.column_config.NumberColumn("EPS est", format="%.2f", width="small"),
            "EPS act": st.column_config.NumberColumn("EPS act", format="%.2f", width="small"),
            "Δ%": st.column_config.NumberColumn("Δ%", format="%+.1f%%", width="small"),
            "Data": st.column_config.DateColumn("Data", format="YYYY-MM-DD", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="medium"),
        },
        disabled=disabled_cols,
        hide_index=True,
        use_container_width=True,
        key="calendar_table",
    )

    # Diff toggles -> save do localStorage
    diff_mask = edited["⭐"] != display["⭐"]
    if diff_mask.any():
        for _, row in edited[diff_mask].iterrows():
            toggle_ticker(ls, row["Ticker"])
        st.rerun()

    # CSV export
    csv = display.drop(columns=["⭐"]).to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Eksport CSV",
        data=csv,
        file_name="earnings_calendar.csv",
        mime="text/csv",
        key="calendar_csv",
    )
```

- [ ] **Step 6.2: Wywołać `_render_calendar_table` w main code**

Znajdź placeholder `st.info("🚧 Tabela...")` po heatmapie i zamień na:

```python
# ---------------------------------------------------------------------------
# TABELA (data_editor z checkbox watchlist)
# ---------------------------------------------------------------------------

st.markdown("### 📋 Tabela raportow")
sorted_df = _apply_sort(filtered, sort_by)
_render_calendar_table(sorted_df, watchlist, ls)

st.markdown("---")

# Placeholder dla Task 7 (cross-link)
st.info("🚧 Cross-link dodany w kolejnym tasku.")
```

- [ ] **Step 6.3: Syntax + regression**

```bash
./venv/Scripts/python.exe -c "
import ast
with open('pages/22_earnings_calendar.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('Syntax OK')
" && ./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```

Expected: Syntax OK + 17/17 PASS.

- [ ] **Step 6.4: Commit**

```bash
git add pages/22_earnings_calendar.py
git commit -m "Add data_editor table + watchlist toggle (localStorage) + CSV export"
```

---

## Task 7: Cross-link selectbox + button

**Files:**
- Modify: `pages/22_earnings_calendar.py`

- [ ] **Step 7.1: Zamień placeholder na cross-link UI**

Znajdź `st.info("🚧 Cross-link...")` po tabeli i zamień na:

```python
# ---------------------------------------------------------------------------
# CROSS-LINK do F13 Sprawozdania Q deep dive
# ---------------------------------------------------------------------------

st.markdown("### 📈 Deep dive (Sprawozdania Q)")
col_sel, col_btn = st.columns([3, 1])
with col_sel:
    selected_ticker = st.selectbox(
        "Wybierz ticker do deep dive:",
        options=[""] + sorted_df["ticker"].tolist(),
        key="calendar_deep_dive_select",
    )
with col_btn:
    st.write("")  # spacer
    go_btn = st.button(
        "📈 Pokaz szczegoly",
        key="calendar_deep_dive_btn",
        disabled=not selected_ticker,
    )

if go_btn and selected_ticker:
    _navigate_to_deep_dive(selected_ticker)
```

- [ ] **Step 7.2: Syntax + regression**

```bash
./venv/Scripts/python.exe -c "
import ast
with open('pages/22_earnings_calendar.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('Syntax OK')
" && ./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```

Expected: Syntax OK + 17/17 PASS.

- [ ] **Step 7.3: Commit**

```bash
git add pages/22_earnings_calendar.py
git commit -m "Add cross-link selectbox + button -> F13 deep dive (st.switch_page)"
```

---

## Task 8: Integracja w `app.py` + `auth.py` + `CLAUDE.md`

**Files:**
- Modify: `components/auth.py`
- Modify: `app.py`
- Modify: `CLAUDE.md`

- [ ] **Step 8.1: Dodać entry `PAGE_INFO[22]` w `components/auth.py`**

Znajdź linię 31 (entry dla page 21):

```python
21: ("\U0001f680", "GEM Extended", "Backtest GEM z dowolnym universe (do 10 ETF + krypto), top N equal-weight"),
```

Dopisz po niej linię z page 22:

```python
22: ("📅", "Earnings Calendar", "Kalendarz nadchodzacych i niedawnych raportow SP500 + GPW (±28 dni) z watchlist"),
```

- [ ] **Step 8.2: Dodać tuple karty w `app.py`**

Znajdź linię 43 w `app.py`:

```python
(21, "🚀", "GEM Extended", "Backtest GEM z dowolnym universe (do 10 ETF + krypto), top N equal-weight", "pages/21_gem_extended.py"),
```

Dopisz po niej (zachowaj indentację i końcowy przecinek):

```python
(22, "📅", "Earnings Calendar", "Kalendarz nadchodzacych raportow SP500+GPW (±28 dni) z watchlist i cross-link do F13", "pages/22_earnings_calendar.py"),
```

- [ ] **Step 8.3: Update CLAUDE.md — sekcja Pages**

Znajdź linię z page 21 w sekcji Pages w `CLAUDE.md` i dopisz po niej:

```markdown
  22_earnings_calendar.py # Earnings Calendar (±28 dni), watchlist localStorage, cross-link do F13 Sprawozdania Q
```

- [ ] **Step 8.4: Update CLAUDE.md — Key Design Decisions (F14)**

W sekcji Key Design Decisions, po wpisie F13 (Sprawozdania Q), dopisz nowy paragraf F14:

```markdown
- **Earnings Calendar (F14):** `pages/22_earnings_calendar.py` (page 22). Kalendarz nadchodzacych i niedawnych raportow (±28 dni) dla SP500 + GPW (effective universe 577 — ETF wykluczone, no earnings). UI: filtry expander + 4 summary cards + Plotly heatmapa 8 tygodni (T-3 do T+4, dzis = czerwona ramka, hover do 5 tickerow) + `st.data_editor` z checkbox ⭐ watchlist + CSV export + cross-link selectbox+button do F13 deep dive. Data layer (`data/financials.py`): `fetch_earnings_dates(ticker)` z parquet cache 24h, `bulk_fetch_earnings_calendar(universe)` z ThreadPool 8 workers + retry, filter ETF (z `_get_etf_set()`). Watchlist: `components/watchlist.py` (localStorage przez streamlit-local-storage, klucz `gem_dashboard_watchlist_v1`, cross-feature module). Cross-link: `st.switch_page("pages/7_sp500.py")` + session_state `{market}_deep_dive_ticker` + `{market}_pending_view = "deep_dive"` (pattern z F13 hotfix `b1f8502`). Spec: `docs/superpowers/specs/2026-06-04-earnings-calendar-design.md`.
```

- [ ] **Step 8.5: Smoke test app.py + auth.py + page 22 imports**

```bash
./venv/Scripts/python.exe -c "
import ast
for f in ['app.py', 'components/auth.py', 'pages/22_earnings_calendar.py']:
    with open(f, encoding='utf-8') as fh:
        ast.parse(fh.read())
    print(f, 'OK')
"
```

Expected: 3x OK.

- [ ] **Step 8.6: Test suite still passing**

```bash
./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```

Expected: 17/17 PASS.

- [ ] **Step 8.7: Commit**

```bash
git add components/auth.py app.py CLAUDE.md
git commit -m "Integration page 22 (Earnings Calendar) — PAGE_INFO + app.py card + CLAUDE.md F14"
```

---

## Task 9: Final QA + push + MEMORY.md

**Files:**
- Modify: `C:\Users\m4x\.claude\projects\C--Users-m4x-Desktop-AI-ebook-white-new-A4\memory\MEMORY.md`
- Create: `C:\Users\m4x\.claude\projects\C--Users-m4x-Desktop-AI-ebook-white-new-A4\memory\project_gem_dashboard_earnings_calendar.md`

- [ ] **Step 9.1: Final test suite run**

```bash
cd C:\Users\m4x\Desktop\AI\gem-dashboard
./venv/Scripts/python.exe -m pytest tests/ -v 2>&1 | tail -25
```

Expected: 17/17 PASS (15 z F13 + 17 nowych z F14 = 32 total? Sprawdzić w teorii).
Realnie: F13 ma 15 testów, F14 dodaje 17 (10 helper + 3 fetch + 4 watchlist). Total ~32.

- [ ] **Step 9.2: Push do main**

```bash
git push origin main
```

Streamlit Cloud auto-redeploy ~3-5 min.

- [ ] **Step 9.3: Manual QA na produkcji**

Otwórz `https://gem-dashboard.streamlit.app/`:
1. Sidebar — sprawdź czy karta "📅 Earnings Calendar" jest widoczna
2. Klik → strona 22
3. Premium gate (kod)
4. Czekać na bulk fetch (~1-2 min cold cache, potem cache 24h)
5. Sprawdzić:
   - [ ] 4 summary cards renderują (Total / Future / Beat-Miss / Avg surprise)
   - [ ] Heatmapa 8 tygodni z DZIŚ jako czerwoną ramką
   - [ ] Tabela z kolumnami: ⭐/Ticker/Nazwa/Market/Sektor/Data/Q/EPS est/EPS act/Δ%/Status
   - [ ] AAPL widoczny w future (najbliższy Q3'26)
   - [ ] JPM w past (Q1'26) z badge ✅ Beat lub ❌ Miss
   - [ ] Klik checkbox ⭐ przy AAPL — dodaje do watchlistu (page reload zachowuje state)
   - [ ] Filter "⭐ Tylko watchlist" — pokazuje tylko zaznaczone
   - [ ] Selectbox AAPL + "Pokaż szczegóły" → przełącza na page 7 tab 8 deep dive AAPL
6. Test edge case: VOO/QQQ NIE pojawia się w tabeli (filtered out)
7. Test edge case: PKO.WA jest w GPW market badge

- [ ] **Step 9.4: MEMORY.md entry**

Najpierw utwórz topic file `project_gem_dashboard_earnings_calendar.md`:

```markdown
---
name: project-gem-dashboard-earnings-calendar
description: Page 22 Earnings Calendar (F14) — WGRANE 2026-06-XX, kalendarz ±28 dni SP500+GPW, watchlist localStorage, cross-link do F13
metadata:
  type: project
---

# Page 22 Earnings Calendar (F14) — WGRANE YYYY-MM-DD

**Final commit:** `<HASH>` na main. Live: `gem-dashboard.streamlit.app` → karta "📅 Earnings Calendar".

## Co zostało dodane

**Data layer (`data/financials.py` — rozszerzony):**
- `_status_badge(date, eps_act, eps_est)` — Future (🔜/⏰/📅) / Past (✅/❌/⚪) / DZIŚ (🔥)
- `_detect_market(ticker)` — lookup → "SP500" / "GPW" / "ETF" / "UNKNOWN"
- `_get_etf_set()` — set tickerów ETF z `ETF_NAMES.keys()`, do filtru
- `fetch_earnings_dates(ticker)` — yfinance `Ticker.earnings_dates`, parquet cache 24h
- `bulk_fetch_earnings_calendar(universe, window_days=28)` — ThreadPool + retry, filter ETF

**UI layer:**
- `pages/22_earnings_calendar.py` (~330 LOC) — config + filtry + 4 summary + heatmapa + tabela + cross-link

**Cross-feature module:**
- `components/watchlist.py` — localStorage `gem_dashboard_watchlist_v1` (sorted JSON array)

**Tests:** `tests/test_calendar.py` ~17 testów (status badge, detect market, ETF filter, watchlist toggle).

## Decyzje architektoniczne

- Universe **577** (SP500 + GPW). ETF wykluczone (no earnings)
- Window **±28 dni** (4 tyg. wstecz + 4 do przodu)
- Watchlist localStorage (persystuje między sesjami w przeglądarce)
- Cross-link via `st.switch_page` + session_state (F13 hotfix pattern `b1f8502`)

## v2 backlog

- ETF Distribution Calendar (dywidendy/distros)
- Email alerts z watchlistu
- Filtr "ile dni do raportu" slider
- Watchlist cloud sync (Supabase)
- Cross-link watchlist do F13 Screener bulk (filter "Tylko watchlist")
```

Następnie dodaj 1-liniowy entry w `MEMORY.md` w sekcji "Projekt: gem-dashboard" (po wpisie Sprawozdania Q):

```markdown
- [Page 22 Earnings Calendar (F14) — WGRANE YYYY-MM-DD](project_gem_dashboard_earnings_calendar.md) — kalendarz raportów ±28 dni SP500+GPW (577 spółek), watchlist localStorage cross-feature, heatmapa Plotly 8 tygodni, cross-link do F13 deep dive. Final commit `<HASH>`.
```

(Podstaw YYYY-MM-DD i `<HASH>` przed commit.)

- [ ] **Step 9.5: Sprawdzić Streamlit Cloud + status**

W przeglądarce `gem-dashboard.streamlit.app` → przejdź do "📅 Earnings Calendar" → cały flow działa. Daj user feedback.

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Page 22 z layoutem zgodnym ze specu — Tasks 4-7
- ✅ Data layer (`fetch_earnings_dates` + `bulk_fetch_earnings_calendar`) — Task 2
- ✅ Watchlist module (localStorage, cross-feature) — Task 3
- ✅ ETF filtered (no earnings) — Tasks 1 (helper) + 2 (filter logic)
- ✅ Plotly heatmap 8 tygodni z hover + DZIŚ ramka — Task 5
- ✅ `st.data_editor` z checkbox ⭐ + diff detection — Task 6
- ✅ Cross-link `st.switch_page` + session_state pre-set — Task 7 (helper z Task 4)
- ✅ CSV export — Task 6
- ✅ `auth.py` PAGE_INFO + `app.py` karta + CLAUDE.md F14 — Task 8
- ✅ Tests pytest — Tasks 1-3
- ✅ Manual QA matrix — Task 9
- ✅ MEMORY.md entry — Task 9

**Placeholder scan:**
- ✅ Brak TBD/TODO
- ✅ Wszystkie code blocks kompletne
- ⚠️ Task 9 Step 9.4 MEMORY.md entry ma placeholder `YYYY-MM-DD` i `<HASH>` — to zamierzone (wypełnia się przy commit). Engineer wypełnia z `git log`.

**Type consistency:**
- ✅ `_status_badge(date, eps_act, eps_est)` — spójne między Task 1 (impl) i Task 6 (caller w `_render_calendar_table`)
- ✅ `_detect_market(ticker)` — Task 1 + Task 4 (`_navigate_to_deep_dive`)
- ✅ `_get_etf_set()` — Task 1 + Task 2 (filter w `bulk_fetch_earnings_calendar`)
- ✅ `fetch_earnings_dates(ticker)` → `DataFrame | None` — Task 2 + reused jako wrapper przez `_fetch_calendar_for_one`
- ✅ `bulk_fetch_earnings_calendar(tickers_tuple, max_workers=8, window_days=28)` — Task 2 + Task 4 (caller)
- ✅ `get_watchlist(ls) -> set[str]` — Task 3 + Task 4 (caller)
- ✅ `toggle_ticker(ls, ticker) -> bool` — Task 3 + Task 6 (caller w diff loop)
- ✅ `_navigate_to_deep_dive(ticker)` — Task 4 (impl) + Task 7 (caller)
- ✅ `_render_heatmap(df, weeks_back=3, weeks_fwd=4)` — Task 5
- ✅ `_render_calendar_table(df, watchlist, ls)` — Task 6
- ✅ `_apply_sort(df, sort_by) -> DataFrame` — Task 6

**No spec requirement gaps detected.**
