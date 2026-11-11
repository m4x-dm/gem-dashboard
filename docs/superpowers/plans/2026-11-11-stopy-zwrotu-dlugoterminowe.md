# Stopy zwrotu długoterminowe — plan wdrożenia

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nowa strona premium `pages/6_stopy_zwrotu.py` porównująca 2–8 ETF-ów pod względem stóp zwrotu do 30 lat (okresy, lata kalendarzowe, okna kroczące, wzrost kapitału i ryzyko), z opcjonalnym wydłużeniem historii o fundusze proxy i przeliczeniem na PLN.

**Architecture:** Cała logika w czystych funkcjach `data/long_returns.py` (dane miesięczne, doklejanie proxy, PLN, statystyki) + cienka warstwa pobierania z `@st.cache_data`. Trzy nowe wykresy w `components/charts.py`. Strona tylko składa kontrolki, wywołuje moduł i renderuje. Spec: `docs/superpowers/specs/2026-11-11-stopy-zwrotu-dlugoterminowe-design.md`.

**Tech Stack:** Python 3.14, Streamlit 1.55, pandas 2.3 (Cloud: najnowszy, także 3.x), numpy, plotly, yfinance (przez istniejące `data.downloader.download_single`), requests (zależność yfinance), pytest, `streamlit.testing.v1.AppTest`.

**Konwencje repo (przeczytaj przed startem):**
- Testy uruchamiaj z katalogu repo: `python -m pytest tests/... -v`.
- Lokalnie (Norton przechwytuje TLS) przed testami sieciowymi ustaw: `export SSL_CERT_FILE="C:/ProgramData/Norton/Antivirus/wscert.pem" REQUESTS_CA_BUNDLE="$SSL_CERT_FILE" CURL_CA_BUNDLE="$SSL_CERT_FILE"`.
- UI po polsku, bez polskich znaków w identyfikatorach. HTML przez `st.html()`, nie `st.markdown(unsafe_allow_html=True)`.
- Nie używaj `DataFrame.applymap` (usunięte w pandas 3) — tylko `.map`.
- Nie ustawiaj `st.session_state[klucz_widgetu]` po utworzeniu widgetu.
- Nie wywołuj `st.stop()` wewnątrz zakładek.
- Commity: krótki tytuł w trybie rozkazującym, stopka `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. `git add` tylko wymienionych plików (nigdy `-A`). Bez push do czasu Task 12.

---

## Struktura plików

| Plik | Akcja | Odpowiedzialność |
|---|---|---|
| `data/long_returns.py` | Create | Stałe (okresy, mapa proxy), czyste funkcje obliczeń, warstwa pobierania z cache |
| `tests/test_long_returns.py` | Create | Testy jednostkowe modułu (bez sieci) + test jakości proxy (sieć, opt-in) |
| `components/charts.py` | Modify (dopisanie na końcu) | `growth_chart`, `yearly_returns_heatmap`, `rolling_returns_chart` |
| `tests/test_long_returns_charts.py` | Create | Testy struktury figur |
| `pages/6_stopy_zwrotu.py` | Create | Strona: kontrolki, 4 zakładki, notki, stopka |
| `tests/test_stopy_zwrotu_page.py` | Create | Kolejność menu (bez sieci) + smoke AppTest (sieć, opt-in) |
| `components/auth.py` | Modify | `PAGE_INFO[26]` |
| `components/sidebar.py` | Modify | Separatory CSS `nth-child` +1 |
| `app.py` | Modify | Kafelek przed „S&P 500” |
| `CLAUDE.md` | Modify | Lista stron + opis modułu |

---

### Task 1: Szkielet modułu, `to_monthly`, etykiety okresów

**Files:**
- Create: `data/long_returns.py`
- Test: `tests/test_long_returns.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_long_returns.py`:

```python
"""Testy modulu data/long_returns.py (strona 6_stopy_zwrotu)."""

import os

import numpy as np
import pandas as pd
import pytest

from data.long_returns import (
    PERIOD_YEARS,
    period_label,
    to_monthly,
)


def _monthly(values, start="2000-01-31"):
    idx = pd.date_range(start, periods=len(values), freq="ME")
    return pd.Series(values, index=idx, dtype=float)


def test_period_years_constant():
    assert PERIOD_YEARS == (1, 3, 5, 10, 15, 20, 25, 30)


@pytest.mark.parametrize("years,label", [
    (1, "1 rok"), (3, "3 lata"), (5, "5 lat"), (10, "10 lat"),
    (15, "15 lat"), (20, "20 lat"), (22, "22 lata"), (25, "25 lat"), (30, "30 lat"),
])
def test_period_label(years, label):
    assert period_label(years) == label


def test_to_monthly_takes_last_price_and_drops_current_month():
    idx = pd.bdate_range("2026-09-01", "2026-11-11")
    daily = pd.Series(np.arange(len(idx), dtype=float), index=idx)
    m = to_monthly(daily, today=pd.Timestamp("2026-11-11"))
    assert list(m.index) == [pd.Timestamp("2026-09-30"), pd.Timestamp("2026-10-31")]
    assert m.loc["2026-09-30"] == daily.loc[:"2026-09-30"].iloc[-1]
    assert m.loc["2026-10-31"] == daily.loc[:"2026-10-31"].iloc[-1]


def test_to_monthly_keeps_finished_month_when_data_ends_earlier():
    idx = pd.bdate_range("2026-08-01", "2026-09-30")
    daily = pd.Series(1.0, index=idx)
    m = to_monthly(daily, today=pd.Timestamp("2026-11-11"))
    assert m.index[-1] == pd.Timestamp("2026-09-30")


def test_to_monthly_empty():
    assert to_monthly(pd.Series(dtype=float)).empty
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_long_returns.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'data.long_returns'`

- [ ] **Step 3: Write minimal implementation**

`data/long_returns.py`:

```python
"""Dlugoterminowe stopy zwrotu ETF-ow (do 30 lat) — logika strony 6_stopy_zwrotu.

Wszystko na danych miesiecznych (cena z konca miesiaca). Czyste funkcje
na gorze pliku, warstwa pobierania z cache na dole.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

PERIOD_YEARS: tuple[int, ...] = (1, 3, 5, 10, 15, 20, 25, 30)


def period_label(years: int) -> str:
    """Polska etykieta okresu: 1 rok, 3 lata, 5 lat, 22 lata, 25 lat."""
    if years == 1:
        return "1 rok"
    if years % 10 in (2, 3, 4) and years % 100 not in (12, 13, 14):
        return f"{years} lata"
    return f"{years} lat"


def to_monthly(daily: pd.Series, today: pd.Timestamp | None = None) -> pd.Series:
    """Ceny z konca miesiaca (indeks = koniec miesiaca), bez biezacego niepelnego miesiaca."""
    s = daily.dropna()
    if s.empty:
        return s.astype(float)
    m = s.resample("ME").last().dropna()
    ref = pd.Timestamp(today) if today is not None else pd.Timestamp.today()
    current_month_end = ref.normalize() + pd.offsets.MonthEnd(0)
    if len(m) and m.index[-1] >= current_month_end:
        m = m.iloc[:-1]
    return m.astype(float)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_long_returns.py -v`
Expected: PASS (13 tests)

- [ ] **Step 5: Commit**

```bash
git add data/long_returns.py tests/test_long_returns.py
git commit -m "Add long_returns module: monthly resampling and period labels"
```

---

### Task 2: `period_returns` — skumulowana i średnioroczna dla okresów

**Files:**
- Modify: `data/long_returns.py`
- Test: `tests/test_long_returns.py`

- [ ] **Step 1: Write the failing tests** (dopisz do `tests/test_long_returns.py`, rozszerz import o `period_returns`)

```python
from data.long_returns import period_returns  # dopisz do importu na gorze


def _growth(years, annual=0.10, start="1990-12-31"):
    """Szereg rosnacy dokladnie `annual` rocznie, miesiecznie, years*12+1 punktow."""
    n = years * 12 + 1
    monthly = (1 + annual) ** (1 / 12)
    return _monthly(100 * monthly ** np.arange(n), start=start)


def test_period_returns_constant_growth():
    s = _growth(12)  # 12 lat historii
    df = period_returns(s)
    assert list(df.columns) == ["total", "cagr"]
    assert list(df.index) == ["1 rok", "3 lata", "5 lat", "10 lat", "15 lat",
                              "20 lat", "25 lat", "30 lat", "Od startu"]
    for lbl in ["1 rok", "3 lata", "5 lat", "10 lat", "Od startu"]:
        assert df.loc[lbl, "cagr"] == pytest.approx(0.10, abs=1e-9)
    assert df.loc["10 lat", "total"] == pytest.approx(1.10 ** 10 - 1, rel=1e-9)
    for lbl in ["15 lat", "20 lat", "25 lat", "30 lat"]:
        assert np.isnan(df.loc[lbl, "cagr"]) and np.isnan(df.loc[lbl, "total"])


def test_period_returns_since_start_under_one_year_has_no_cagr():
    s = _monthly([100, 101, 102, 103])
    df = period_returns(s)
    assert df.loc["Od startu", "total"] == pytest.approx(0.03)
    assert np.isnan(df.loc["Od startu", "cagr"])


def test_period_returns_empty():
    df = period_returns(pd.Series(dtype=float))
    assert df["cagr"].isna().all()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_long_returns.py -v -k period_returns`
Expected: FAIL — `ImportError: cannot import name 'period_returns'`

- [ ] **Step 3: Implement** (dopisz pod `to_monthly` w `data/long_returns.py`)

```python
SINCE_START = "Od startu"


def period_returns(series_m: pd.Series, years: tuple[int, ...] = PERIOD_YEARS) -> pd.DataFrame:
    """Stopa skumulowana i CAGR dla okresow konczacych sie na ostatnim punkcie szeregu.

    Wiersze: etykiety okresow + 'Od startu'. NaN, gdy historii za malo.
    CAGR 'Od startu' tylko dla historii >= 1 rok.
    """
    s = series_m.dropna()
    rows: dict[str, tuple[float, float]] = {}
    n_months = len(s) - 1
    for y in years:
        w = 12 * y
        if n_months >= w:
            total = s.iloc[-1] / s.iloc[-1 - w] - 1
            rows[period_label(y)] = (total, (1 + total) ** (1 / y) - 1)
        else:
            rows[period_label(y)] = (np.nan, np.nan)
    if n_months >= 1:
        total = s.iloc[-1] / s.iloc[0] - 1
        yrs = n_months / 12
        cagr = (1 + total) ** (1 / yrs) - 1 if yrs >= 1 else np.nan
        rows[SINCE_START] = (total, cagr)
    else:
        rows[SINCE_START] = (np.nan, np.nan)
    return pd.DataFrame.from_dict(rows, orient="index", columns=["total", "cagr"])
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_long_returns.py -v`
Expected: PASS (wszystkie)

- [ ] **Step 5: Commit**

```bash
git add data/long_returns.py tests/test_long_returns.py
git commit -m "Add period_returns: cumulative and CAGR for 1-30 year windows"
```

---

### Task 3: `PROXY_MAP` i `splice_proxy`

**Files:**
- Modify: `data/long_returns.py`
- Test: `tests/test_long_returns.py`

- [ ] **Step 1: Write the failing tests** (rozszerz import o `PROXY_MAP, splice_proxy`)

```python
from data.long_returns import PROXY_MAP, splice_proxy  # dopisz do importu


def test_proxy_map_contents():
    assert PROXY_MAP["SPY"] == "VFINX"
    assert PROXY_MAP["AGG"] == "VBMFX"
    assert "GLD" not in PROXY_MAP and "QQQ" not in PROXY_MAP


def test_splice_proxy_uses_proxy_returns_before_start_and_etf_after():
    proxy = _monthly([50, 55, 60, 66, 70, 77, 80], start="2000-01-31")
    etf = _monthly([200, 210, 231, 240], start="2000-04-30")  # start = 4. miesiac proxy
    spliced, proxy_end = splice_proxy(etf, proxy)
    assert proxy_end == pd.Timestamp("2000-04-30")
    assert spliced.index[0] == pd.Timestamp("2000-01-31")
    # od startu ETF-u poziomy identyczne z ETF-em (brak skoku)
    pd.testing.assert_series_equal(spliced.loc["2000-04-30":], etf, check_names=False, check_freq=False)
    # przed startem stopy zwrotu jak w proxy
    r_sp = spliced.pct_change().loc[:"2000-04-30"].dropna()
    r_px = proxy.pct_change().loc[:"2000-04-30"].dropna()
    np.testing.assert_allclose(r_sp.values, r_px.values)


def test_splice_proxy_no_overlap_returns_etf_unchanged():
    proxy = _monthly([1, 2, 3], start="2010-01-31")  # proxy po starcie ETF-u
    etf = _monthly([10, 11], start="2005-01-31")
    spliced, proxy_end = splice_proxy(etf, proxy)
    assert proxy_end is None
    pd.testing.assert_series_equal(spliced, etf, check_freq=False)


def test_splice_proxy_missing_start_month_in_proxy_returns_etf():
    proxy = pd.Series([1.0, 2.0], index=pd.to_datetime(["2000-01-31", "2000-02-29"]))
    etf = _monthly([10, 11], start="2000-04-30")
    spliced, proxy_end = splice_proxy(etf, proxy)
    assert proxy_end is None
    pd.testing.assert_series_equal(spliced, etf, check_freq=False)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_long_returns.py -v -k "proxy"`
Expected: FAIL — `ImportError: cannot import name 'PROXY_MAP'`

- [ ] **Step 3: Implement** (dopisz do `data/long_returns.py` pod `PERIOD_YEARS`)

```python
# ETF -> stary fundusz indeksowy Vanguard o tej samej ekspozycji (dane yfinance od 1980-1996).
# Para zostaje w mapie tylko, gdy korelacja miesiecznych stop we wspolnym okresie > 0,95
# (test_proxy_quality_network). Bez proxy: QQQ, ACWI, EWJ, EWU, FXI, TIP, GLD, IAU, GSG,
# DBC, VNQI, sektory XL*.
PROXY_MAP: dict[str, str] = {
    "SPY": "VFINX", "VOO": "VFINX",
    "VTI": "VTSMX",
    "IWM": "NAESX",
    "VEA": "VGTSX", "EFA": "VGTSX",
    "EEM": "VEIEX", "VWO": "VEIEX",
    "VGK": "VEURX",
    "AGG": "VBMFX", "BND": "VBMFX",
    "TLT": "VUSTX",
    "IEF": "VFITX",
    "SHY": "VBISX",
    "VNQ": "VGSIX",
}
```

oraz pod `period_returns`:

```python
def splice_proxy(etf_m: pd.Series, proxy_m: pd.Series) -> tuple[pd.Series, pd.Timestamp | None]:
    """Wydluza historie ETF-u o stopy zwrotu proxy sprzed jego startu.

    Proxy skalowane tak, by w pierwszym miesiacu ETF-u mialo jego poziom: brak skoku,
    od startu poziomy = ETF. Zwraca (szereg, miesiac startu ETF-u) albo (ETF, None),
    gdy proxy nie ma danych z miesiaca startu i wczesniej.
    """
    etf = etf_m.dropna()
    proxy = proxy_m.dropna()
    if etf.empty:
        return etf, None
    start = etf.index[0]
    before = proxy[proxy.index <= start]
    if len(before) < 2 or before.index[-1] != start:
        return etf, None
    scaled = before / before.iloc[-1] * etf.iloc[0]
    spliced = pd.concat([scaled.iloc[:-1], etf])
    spliced.name = etf_m.name
    return spliced, start
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_long_returns.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/long_returns.py tests/test_long_returns.py
git commit -m "Add proxy map and splice_proxy (return-based backfill, no level jump)"
```

---

### Task 4: Kurs USD/PLN — parser FRED, łączenie źródeł, przeliczenie

**Files:**
- Modify: `data/long_returns.py`
- Test: `tests/test_long_returns.py`

- [ ] **Step 1: Write the failing tests** (rozszerz import o `parse_fred_csv, combine_fx, convert_to_pln`)

```python
from data.long_returns import parse_fred_csv, combine_fx, convert_to_pln  # dopisz


FRED_SAMPLE = (
    "observation_date,CCUSMA02PLM618N\n"
    "1996-01-01,2.4775\n"
    "1996-02-01,.\n"
    "1996-03-01,2.5310\n"
)


def test_parse_fred_csv_month_end_index_and_skips_missing():
    s = parse_fred_csv(FRED_SAMPLE)
    assert list(s.index) == [pd.Timestamp("1996-01-31"), pd.Timestamp("1996-03-31")]
    assert s.iloc[0] == pytest.approx(2.4775)


def test_combine_fx_appends_only_newer_months():
    fred = _monthly([3.0, 3.1], start="2026-08-31")
    yf_m = _monthly([9.9, 3.2, 3.3], start="2026-08-31")  # sierpien zignorowany
    out = combine_fx(fred, yf_m)
    assert list(out.values) == [3.0, 3.1, 3.3]
    assert out.index[-1] == pd.Timestamp("2026-10-31")


def test_combine_fx_without_fred():
    yf_m = _monthly([3.2, 3.3])
    pd.testing.assert_series_equal(combine_fx(None, yf_m), yf_m, check_freq=False)


def test_convert_to_pln_constant_rate_keeps_returns():
    usd = _monthly([100, 110, 121])
    fx = _monthly([4.0, 4.0, 4.0])
    pln = convert_to_pln(usd, fx)
    np.testing.assert_allclose(pln.pct_change().dropna().values, [0.10, 0.10])


def test_convert_to_pln_compounds_fx_and_drops_months_without_rate():
    usd = _monthly([100, 110, 121])
    fx = _monthly([4.0, 4.2], start="2000-02-29")  # brak kursu za styczen
    pln = convert_to_pln(usd, fx)
    assert list(pln.index) == list(fx.index)
    assert pln.pct_change().iloc[-1] == pytest.approx(1.10 * 1.05 - 1)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_long_returns.py -v -k "fred or fx or pln"`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement** (dopisz do `data/long_returns.py`; na gorze dodaj `import io`)

```python
FRED_USDPLN_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CCUSMA02PLM618N"


def parse_fred_csv(text: str) -> pd.Series:
    """CSV z FRED (observation_date, wartosc) -> Series z indeksem koniec miesiaca."""
    df = pd.read_csv(io.StringIO(text))
    dates = pd.to_datetime(df.iloc[:, 0]) + pd.offsets.MonthEnd(0)
    vals = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    s = pd.Series(vals.values, index=pd.DatetimeIndex(dates), dtype=float).dropna()
    s.name = "USDPLN"
    return s


def combine_fx(fred_m: pd.Series | None, yf_m: pd.Series | None) -> pd.Series | None:
    """Kurs miesieczny: FRED (srednia miesieczna, dluga historia), dalej miesiace z yfinance."""
    if fred_m is None or fred_m.empty:
        return yf_m
    if yf_m is None or yf_m.empty:
        return fred_m
    newer = yf_m[yf_m.index > fred_m.index[-1]]
    return pd.concat([fred_m, newer])


def convert_to_pln(usd_m: pd.Series, fx_m: pd.Series) -> pd.Series:
    """Cena w USD x kurs USD/PLN; tylko miesiace, dla ktorych jest kurs."""
    idx = usd_m.dropna().index.intersection(fx_m.dropna().index)
    out = usd_m.loc[idx] * fx_m.loc[idx]
    out.name = usd_m.name
    return out
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_long_returns.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/long_returns.py tests/test_long_returns.py
git commit -m "Add USD/PLN monthly series: FRED parser, source combining, conversion"
```

---

### Task 5: Stopy roczne i okna kroczące

**Files:**
- Modify: `data/long_returns.py`
- Test: `tests/test_long_returns.py`

- [ ] **Step 1: Write the failing tests** (rozszerz import o `calendar_year_returns, rolling_cagr, rolling_summary`)

```python
from data.long_returns import calendar_year_returns, rolling_cagr, rolling_summary  # dopisz


def test_calendar_year_returns_skips_partial_first_year_and_flags_ytd():
    # start w marcu 2000: rok 2000 niepelny -> pominiety; 2001 pelny; 2002 do marca -> YTD
    idx = pd.date_range("2000-03-31", "2002-03-31", freq="ME")
    s = pd.Series(np.linspace(100, 200, len(idx)), index=idx)
    yearly, ytd_year = calendar_year_returns(s)
    assert list(yearly.index) == [2001, 2002]
    assert yearly.loc[2001] == pytest.approx(s.loc["2001-12-31"] / s.loc["2000-12-31"] - 1)
    assert ytd_year == 2002


def test_calendar_year_returns_full_last_year_has_no_ytd():
    idx = pd.date_range("1999-12-31", "2001-12-31", freq="ME")
    s = pd.Series(np.linspace(100, 150, len(idx)), index=idx)
    yearly, ytd_year = calendar_year_returns(s)
    assert list(yearly.index) == [2000, 2001]
    assert ytd_year is None


def test_rolling_cagr_window_count_and_value():
    s = _growth(6)  # 73 punkty
    r = rolling_cagr(s, 5)
    assert len(r) == 73 - 60
    np.testing.assert_allclose(r.values, 0.10)


def test_rolling_summary():
    r = pd.Series([-0.02, 0.01, 0.03, 0.05, 0.10])
    out = rolling_summary(r)
    assert out["min"] == -0.02 and out["max"] == 0.10
    assert out["median"] == pytest.approx(0.03)
    assert out["pct_negative"] == pytest.approx(0.2)
    assert out["count"] == 5


def test_rolling_summary_empty():
    out = rolling_summary(pd.Series(dtype=float))
    assert out["count"] == 0 and np.isnan(out["median"])
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_long_returns.py -v -k "calendar or rolling"`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement** (dopisz do `data/long_returns.py`)

```python
def calendar_year_returns(series_m: pd.Series) -> tuple[pd.Series, int | None]:
    """Zwroty w latach kalendarzowych. Pierwszy rok tylko, gdy szereg ma grudzien roku poprzedniego.

    Zwraca (Series rok -> zwrot, rok YTD albo None, gdy ostatni miesiac to grudzien).
    """
    s = series_m.dropna()
    if s.empty:
        return pd.Series(dtype=float), None
    year_end = s.groupby(s.index.year).last()
    yearly = (year_end / year_end.shift(1) - 1).dropna()
    yearly.index = yearly.index.astype(int)
    ytd_year = int(s.index[-1].year) if s.index[-1].month != 12 else None
    if ytd_year is not None and ytd_year not in yearly.index:
        ytd_year = None
    return yearly, ytd_year


def rolling_cagr(series_m: pd.Series, years: int) -> pd.Series:
    """CAGR w kroczacym oknie `years` lat; punkt = miesiac konca okna."""
    s = series_m.dropna()
    w = 12 * years
    return ((s / s.shift(w)) ** (1 / years) - 1).dropna()


def rolling_summary(rolling: pd.Series) -> dict:
    """Rozklad kroczacych CAGR: min, p25, median, p75, max, pct_negative, count."""
    r = rolling.dropna()
    if r.empty:
        nan = float("nan")
        return {"min": nan, "p25": nan, "median": nan, "p75": nan, "max": nan,
                "pct_negative": nan, "count": 0}
    return {
        "min": float(r.min()), "p25": float(r.quantile(0.25)), "median": float(r.median()),
        "p75": float(r.quantile(0.75)), "max": float(r.max()),
        "pct_negative": float((r < 0).mean()), "count": int(len(r)),
    }
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_long_returns.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/long_returns.py tests/test_long_returns.py
git commit -m "Add calendar-year and rolling CAGR returns with distribution summary"
```

---

### Task 6: Wyrównanie okresów, zmienność, etykieta „Dane od”

**Files:**
- Modify: `data/long_returns.py`
- Test: `tests/test_long_returns.py`

- [ ] **Step 1: Write the failing tests** (rozszerz import o `align_end, common_window, annual_volatility, data_since_label`)

```python
from data.long_returns import align_end, common_window, annual_volatility, data_since_label  # dopisz


def test_align_end_cuts_to_earliest_last_month():
    a = _monthly([1, 2, 3, 4], start="2026-07-31")
    b = _monthly([1, 2, 3], start="2026-07-31")
    out = align_end({"A": a, "B": b})
    assert out["A"].index[-1] == out["B"].index[-1] == pd.Timestamp("2026-09-30")


def test_common_window_cuts_to_latest_start():
    a = _monthly(range(1, 11), start="2000-01-31")
    b = _monthly(range(1, 6), start="2000-06-30")
    out = common_window({"A": a, "B": b})
    assert out["A"].index[0] == out["B"].index[0] == pd.Timestamp("2000-06-30")
    assert len(out["A"]) == len(out["B"])


def test_annual_volatility():
    s = _monthly([100, 110, 99, 108.9])  # stopy +10%, -10%, +10%
    r = s.pct_change().dropna()
    assert annual_volatility(s) == pytest.approx(r.std(ddof=0) * np.sqrt(12))


def test_data_since_label():
    s = _monthly([1, 2], start="1980-01-31")
    assert data_since_label(s, None, None) == "1980"
    assert data_since_label(s, "VFINX", pd.Timestamp("1993-01-31")) == "1980 (proxy VFINX do 01.1993)"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_long_returns.py -v -k "align or common or volatility or since"`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement** (dopisz do `data/long_returns.py`)

```python
def align_end(series: dict[str, pd.Series]) -> dict[str, pd.Series]:
    """Przycina wszystkie szeregi do najwczesniejszego wspolnego ostatniego miesiaca."""
    valid = {k: v.dropna() for k, v in series.items() if not v.dropna().empty}
    if not valid:
        return {}
    end = min(v.index[-1] for v in valid.values())
    return {k: v[v.index <= end] for k, v in valid.items()}


def common_window(series: dict[str, pd.Series]) -> dict[str, pd.Series]:
    """Wspolny okres: od najpozniejszego startu do najwczesniejszego konca."""
    aligned = align_end(series)
    if not aligned:
        return {}
    start = max(v.index[0] for v in aligned.values())
    return {k: v[v.index >= start] for k, v in aligned.items()}


def annual_volatility(series_m: pd.Series) -> float:
    """Zmiennosc roczna: odchylenie standardowe miesiecznych stop (ddof=0) x sqrt(12)."""
    r = series_m.dropna().pct_change().dropna()
    return float(r.std(ddof=0) * np.sqrt(12)) if len(r) > 1 else float("nan")


def data_since_label(series_m: pd.Series, proxy_ticker: str | None,
                     proxy_end: pd.Timestamp | None) -> str:
    """'1993' albo '1980 (proxy VFINX do 01.1993)'."""
    s = series_m.dropna()
    if s.empty:
        return "—"
    year = str(s.index[0].year)
    if proxy_ticker and proxy_end is not None:
        return f"{year} (proxy {proxy_ticker} do {proxy_end:%m.%Y})"
    return year
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_long_returns.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/long_returns.py tests/test_long_returns.py
git commit -m "Add period alignment, annual volatility and data-since label helpers"
```

---

### Task 7: Warstwa pobierania z cache

**Files:**
- Modify: `data/long_returns.py`
- Test: `tests/test_long_returns.py`

- [ ] **Step 1: Write the failing test** (logika bez sieci — `download_single` podmieniony przez monkeypatch na funkcji niezcache'owanej `_load_monthly_impl`)

```python
import data.long_returns as lr  # dopisz do importow


def test_load_monthly_impl_splices_when_proxy_enabled(monkeypatch):
    days_proxy = pd.bdate_range("1990-01-01", "2000-12-29")
    days_etf = pd.bdate_range("1995-01-02", "2000-12-29")
    fake = {
        "VFINX": pd.Series(np.linspace(10, 50, len(days_proxy)), index=days_proxy),
        "SPY": pd.Series(np.linspace(100, 300, len(days_etf)), index=days_etf),
    }
    monkeypatch.setattr(lr, "download_single", lambda t, period="max": fake.get(t))
    s, proxy_t, end = lr._load_monthly_impl("SPY", True)
    assert proxy_t == "VFINX" and end == pd.Timestamp("1995-01-31")
    assert s.index[0] == pd.Timestamp("1990-01-31")
    s2, proxy_t2, end2 = lr._load_monthly_impl("SPY", False)
    assert proxy_t2 is None and end2 is None and s2.index[0] == pd.Timestamp("1995-01-31")


def test_load_monthly_impl_missing_ticker(monkeypatch):
    monkeypatch.setattr(lr, "download_single", lambda t, period="max": None)
    assert lr._load_monthly_impl("SPY", True) == (None, None, None)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_long_returns.py -v -k load_monthly`
Expected: FAIL — `AttributeError: module 'data.long_returns' has no attribute 'download_single'`

- [ ] **Step 3: Implement** (dopisz na koncu `data/long_returns.py`; importy na gorze pliku: `import requests`, `import streamlit as st`, `from data.downloader import download_single`)

```python
# --- Warstwa pobierania (cache 24 h) ---------------------------------------------


def _load_monthly_impl(ticker: str, use_proxy: bool
                       ) -> tuple[pd.Series | None, str | None, pd.Timestamp | None]:
    """(szereg miesieczny, ticker proxy albo None, koniec odcinka proxy albo None)."""
    daily = download_single(ticker, period="max")
    if daily is None or daily.dropna().empty:
        return None, None, None
    m = to_monthly(daily)
    m.name = ticker
    if not use_proxy or ticker not in PROXY_MAP:
        return m, None, None
    proxy_ticker = PROXY_MAP[ticker]
    proxy_daily = download_single(proxy_ticker, period="max")
    if proxy_daily is None or proxy_daily.dropna().empty:
        return m, None, None
    spliced, end = splice_proxy(m, to_monthly(proxy_daily))
    if end is None:
        return m, None, None
    return spliced, proxy_ticker, end


@st.cache_data(ttl=86400, show_spinner="Pobieram dlugie historie cen...")
def load_monthly(ticker: str, use_proxy: bool):
    return _load_monthly_impl(ticker, use_proxy)


@st.cache_data(ttl=86400, show_spinner="Pobieram kurs USD/PLN...")
def fetch_usdpln_monthly() -> tuple[pd.Series | None, str]:
    """Kurs USD/PLN miesiecznie. Zrodlo: 'fred' (od 1957, dalej doklejony yfinance),
    'yfinance' (od 12.2003, gdy FRED niedostepny) albo 'none'."""
    fred = None
    try:
        resp = requests.get(FRED_USDPLN_URL, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        parsed = parse_fred_csv(resp.text)
        fred = parsed if len(parsed) > 12 else None
    except Exception:
        fred = None
    yf_daily = download_single("USDPLN=X", period="max")
    yf_m = to_monthly(yf_daily) if yf_daily is not None else None
    fx = combine_fx(fred, yf_m)
    if fx is None or fx.empty:
        return None, "none"
    return fx, ("fred" if fred is not None else "yfinance")
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_long_returns.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/long_returns.py tests/test_long_returns.py
git commit -m "Add cached data layer: monthly prices with proxy, USD/PLN from FRED"
```

---

### Task 8: Test jakości proxy (sieć) i przycięcie mapy

**Files:**
- Modify: `data/long_returns.py` (`correlation_with_proxy`, ewentualnie `PROXY_MAP`)
- Test: `tests/test_long_returns.py`

- [ ] **Step 1: Write tests** (rozszerz import o `correlation_with_proxy`)

```python
from data.long_returns import correlation_with_proxy  # dopisz


def test_correlation_with_proxy_identical_returns():
    a = _monthly([100, 110, 99, 120, 118])
    assert correlation_with_proxy(a, a * 3) == pytest.approx(1.0)


def test_correlation_with_proxy_too_short_overlap_is_nan():
    a = _monthly([1, 2], start="2000-01-31")
    b = _monthly([1, 2], start="2010-01-31")
    assert np.isnan(correlation_with_proxy(a, b))


@pytest.mark.skipif(os.environ.get("RUN_NETWORK") != "1", reason="test sieciowy: RUN_NETWORK=1")
@pytest.mark.parametrize("etf,proxy", sorted(PROXY_MAP.items()))
def test_proxy_quality_network(etf, proxy):
    e = lr.to_monthly(lr._yf_max(etf))
    p = lr.to_monthly(lr._yf_max(proxy))
    corr = correlation_with_proxy(e, p)
    assert corr > 0.95, f"{etf} vs {proxy}: korelacja {corr:.3f}"
```

- [ ] **Step 2: Implement** (dopisz do `data/long_returns.py`; `_yf_max` to niezcache'owane pobranie do testu poza Streamlitem)

```python
def correlation_with_proxy(etf_m: pd.Series, proxy_m: pd.Series, min_months: int = 24) -> float:
    """Korelacja miesiecznych stop zwrotu we wspolnym okresie (NaN, gdy < min_months)."""
    r = pd.concat([etf_m.pct_change(), proxy_m.pct_change()], axis=1).dropna()
    if len(r) < min_months:
        return float("nan")
    return float(r.iloc[:, 0].corr(r.iloc[:, 1]))


def _yf_max(ticker: str) -> pd.Series:
    """Pelna historia z yfinance bez cache Streamlita (do testow sieciowych)."""
    import yfinance as yf
    d = yf.download(ticker, period="max", auto_adjust=True, progress=False)["Close"]
    if isinstance(d, pd.DataFrame):
        d = d.iloc[:, 0]
    d = d.dropna()
    if getattr(d.index, "tz", None) is not None:
        d.index = d.index.tz_localize(None)
    return d
```

- [ ] **Step 3: Run unit tests (bez sieci)**

Run: `python -m pytest tests/test_long_returns.py -v`
Expected: PASS, testy sieciowe SKIPPED (15)

- [ ] **Step 4: Run network quality test**

Run:
```bash
export SSL_CERT_FILE="C:/ProgramData/Norton/Antivirus/wscert.pem" REQUESTS_CA_BUNDLE="$SSL_CERT_FILE" CURL_CA_BUNDLE="$SSL_CERT_FILE"
RUN_NETWORK=1 python -m pytest tests/test_long_returns.py -v -k proxy_quality
```
Expected: każda para PASS albo FAIL z komunikatem „X vs Y: korelacja 0,9xx”.

- [ ] **Step 5: Prune failing pairs**

Dla każdej pary FAIL usuń jej wpis z `PROXY_MAP` i dopisz ETF do komentarza „Bez proxy” nad mapą (np. `# VEA, EFA: VGTSX korelacja 0,94 < 0,95 — bez proxy`). Jeśli usunięcie dotyczy `SPY` lub `AGG`, zaktualizuj też `test_proxy_map_contents`. Powtórz Step 4 — wszystkie PASS.

- [ ] **Step 6: Commit**

```bash
git add data/long_returns.py tests/test_long_returns.py
git commit -m "Add proxy quality check (corr > 0.95) and prune failing proxy pairs"
```

(Jeśli żadna para nie odpadła, tytuł: `Add proxy quality check (corr > 0.95); all proxy pairs pass`.) W treści commita wypisz zmierzone korelacje.

---

### Task 9: Wykresy

**Files:**
- Modify: `components/charts.py` (dopisz na końcu)
- Test: `tests/test_long_returns_charts.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_long_returns_charts.py`:

```python
"""Testy struktury wykresow strony 6_stopy_zwrotu."""

import numpy as np
import pandas as pd

from components.charts import growth_chart, rolling_returns_chart, yearly_returns_heatmap


def _m(values, start="2000-01-31"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="ME"), dtype=float)


def test_growth_chart_log_axis_and_dashed_proxy_segment():
    series = {"SPY": _m([100, 110, 121, 133]), "GLD": _m([10, 11, 12, 13])}
    proxy_end = {"SPY": pd.Timestamp("2000-02-29"), "GLD": None}
    fig = growth_chart(series, proxy_end, start_value=10_000, currency="USD")
    assert fig.layout.yaxis.type == "log"
    names = [t.name for t in fig.data]
    assert names.count("SPY") == 2 and names.count("GLD") == 1
    dashes = {(t.name, t.line.dash) for t in fig.data}
    assert ("SPY", "dash") in dashes and ("SPY", "solid") in dashes
    gld = [t for t in fig.data if t.name == "GLD"][0]
    assert gld.y[0] == 10_000


def test_yearly_returns_heatmap_marks_ytd():
    df = pd.DataFrame({"SPY": [0.1, -0.05, 0.02], "AGG": [0.03, 0.01, np.nan]},
                      index=[2024, 2025, 2026])
    fig = yearly_returns_heatmap(df, ytd_year=2026)
    assert list(fig.data[0].y) == ["2024", "2025", "2026 YTD"]
    assert list(fig.data[0].x) == ["SPY", "AGG"]


def test_rolling_returns_chart_one_trace_per_series_plus_zero_line():
    fig = rolling_returns_chart({"SPY": _m([0.1, 0.12]), "AGG": _m([0.03, 0.02])}, years=10)
    assert len(fig.data) == 2
    assert any(s.y0 == 0 for s in fig.layout.shapes)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_long_returns_charts.py -v`
Expected: FAIL — `ImportError: cannot import name 'growth_chart'`

- [ ] **Step 3: Implement** (dopisz na końcu `components/charts.py`)

```python
def growth_chart(series: dict[str, pd.Series], proxy_end: dict[str, pd.Timestamp | None],
                 start_value: float = 10_000, currency: str = "USD",
                 title: str = "") -> go.Figure:
    """Wzrost kapitalu w skali log. Odcinek z proxy (do proxy_end wlacznie) linia przerywana."""
    fig = go.Figure()
    for i, (name, s) in enumerate(series.items()):
        s = s.dropna()
        if s.empty:
            continue
        v = s / s.iloc[0] * start_value
        color = COLORS[i % len(COLORS)]
        end = proxy_end.get(name)
        hover = f"{name}<br>%{{x|%m.%Y}}<br>%{{y:,.0f}} {currency}<extra></extra>"
        if end is not None and v.index[0] < end:
            px = v[v.index <= end]
            fig.add_trace(go.Scatter(x=px.index, y=px.values, name=name, mode="lines",
                                     legendgroup=name, showlegend=False, hovertemplate=hover,
                                     line=dict(color=color, width=2, dash="dash")))
            v = v[v.index >= end]
        fig.add_trace(go.Scatter(x=v.index, y=v.values, name=name, mode="lines",
                                 legendgroup=name, hovertemplate=hover,
                                 line=dict(color=color, width=2, dash="solid")))
    fig.update_layout(**_base_layout(title or f"Wzrost {start_value:,.0f} {currency}".replace(",", " "),
                                     height=480))
    fig.update_yaxes(type="log")
    return fig


def yearly_returns_heatmap(df: pd.DataFrame, ytd_year: int | None = None,
                           title: str = "Stopy zwrotu w latach kalendarzowych (%)") -> go.Figure:
    """Heatmapa rok x ETF. Kolory: czerwony (ujemny) -> tlo -> zielony (dodatni)."""
    vals = df.values.astype(float) * 100
    labels = np.where(np.isnan(vals), "", np.vectorize(lambda v: f"{v:.1f}%")(vals))
    y_labels = [f"{y} YTD" if ytd_year is not None and int(y) == ytd_year else str(y)
                for y in df.index]
    fig = go.Figure(go.Heatmap(
        z=vals, x=[str(c) for c in df.columns], y=y_labels,
        colorscale=[[0, "#EF4444"], [0.5, BG2], [1, "#22C55E"]], zmid=0,
        text=labels, texttemplate="%{text}", textfont=dict(size=10),
        hovertemplate="Rok: %{y}<br>%{x}: %{text}<extra></extra>",
    ))
    fig.update_layout(**_base_layout(title, height=max(400, len(df) * 24)))
    fig.update_xaxes(side="top")
    fig.update_yaxes(autorange="reversed")
    return fig


def rolling_returns_chart(rolling: dict[str, pd.Series], years: int,
                          title: str = "") -> go.Figure:
    """CAGR w kroczacym oknie; punkt = miesiac konca okna; linia zero."""
    fig = go.Figure()
    for i, (name, r) in enumerate(rolling.items()):
        r = r.dropna()
        if r.empty:
            continue
        fig.add_trace(go.Scatter(
            x=r.index, y=r.values * 100, name=name, mode="lines",
            line=dict(color=COLORS[i % len(COLORS)], width=2),
            hovertemplate=f"{name}<br>okno do %{{x|%m.%Y}}<br>%{{y:.1f}}% rocznie<extra></extra>",
        ))
    fig.add_hline(y=0, line=dict(color="#6B7280", width=1, dash="dot"))
    fig.update_layout(**_base_layout(title or f"Kroczacy CAGR — okno {years} lat (%)", height=450))
    return fig
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_long_returns_charts.py tests/test_long_returns.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add components/charts.py tests/test_long_returns_charts.py
git commit -m "Add growth (log, dashed proxy), yearly heatmap and rolling CAGR charts"
```

---

### Task 10: Strona `pages/6_stopy_zwrotu.py`

**Files:**
- Create: `pages/6_stopy_zwrotu.py`
- Modify: `components/auth.py` (`PAGE_INFO`)

- [ ] **Step 1: Dodaj wpis ekranu blokady** w `components/auth.py`, w słowniku `PAGE_INFO` (po wpisie `5:`):

```python
    26: ("\U0001f4cf", "Stopy zwrotu", "Stopy zwrotu ETF-ow do 30 lat: okresy, lata, okna kroczace, PLN i proxy"),
```

- [ ] **Step 2: Utwórz stronę** `pages/6_stopy_zwrotu.py`:

```python
"""Strona 6 (premium, id 26): Stopy zwrotu dlugoterminowe — porownanie ETF-ow do 30 lat."""

import numpy as np
import pandas as pd
import streamlit as st

from components.auth import require_premium
from components.charts import growth_chart, rolling_returns_chart, yearly_returns_heatmap
from components.formatting import fmt_pct
from components.sidebar import get_risk_free, render_footer, setup_sidebar
from data.etf_universe import ALL_TICKERS, ETF_NAMES
from data.long_returns import (
    PERIOD_YEARS, PROXY_MAP, SINCE_START,
    align_end, annual_volatility, calendar_year_returns, common_window,
    convert_to_pln, data_since_label, fetch_usdpln_monthly, load_monthly,
    period_label, period_returns, rolling_cagr, rolling_summary,
)
from data.momentum import calc_stats

st.set_page_config(page_title="Stopy zwrotu", page_icon="📏", layout="wide")
setup_sidebar()
if not require_premium(26):
    st.stop()

st.markdown("# 📏 Stopy zwrotu dlugoterminowe")
st.caption(
    "Porownanie ETF-ow na horyzoncie do 30 lat: stopy skumulowane i srednioroczne (CAGR), "
    "lata kalendarzowe, okna kroczace oraz wzrost kapitalu z miarami ryzyka. Dane miesieczne."
)

DEFAULT = ["SPY", "VEA", "EEM", "AGG", "GLD"]

c1, c2, c3 = st.columns([3, 1.4, 1])
with c1:
    selected = st.multiselect(
        "ETF-y (2-8)", options=ALL_TICKERS, default=DEFAULT, max_selections=8,
        format_func=lambda t: f"{t} — {ETF_NAMES.get(t, t)}", key="lr_selected",
    )
with c2:
    use_proxy = st.toggle("Wydluz historie o fundusze proxy", value=False, key="lr_proxy",
                          help="Przed startem ETF-u stopy zwrotu starego funduszu indeksowego "
                               "na ten sam rynek (np. SPY ← VFINX od 1980).")
with c3:
    currency = st.radio("Waluta", ["USD", "PLN"], horizontal=True, key="lr_ccy")

# --- Dane --------------------------------------------------------------------------
series: dict[str, pd.Series] = {}
proxy_info: dict[str, tuple[str | None, pd.Timestamp | None]] = {}
for t in selected:
    s, proxy_t, proxy_end = load_monthly(t, use_proxy)
    if s is None or len(s) < 13:
        st.warning(f"Brak wystarczajacych danych dla {t} — pomijam.")
        continue
    if use_proxy and t in PROXY_MAP and proxy_t is None:
        st.caption(f"{t}: nie udalo sie doloczyc proxy {PROXY_MAP[t]} — pokazuje prawdziwa historie ETF-u.")
    series[t] = s
    proxy_info[t] = (proxy_t, proxy_end)

if currency == "PLN" and series:
    fx, fx_source = fetch_usdpln_monthly()
    if fx is None:
        st.warning("Nie udalo sie pobrac kursu USD/PLN — pokazuje wyniki w USD.")
        currency = "USD"
    else:
        if fx_source == "yfinance":
            st.info("Kurs USD/PLN z FRED niedostepny — tryb PLN obejmuje dane od grudnia 2003.")
        series = {t: convert_to_pln(s, fx) for t, s in series.items()}
        series = {t: s for t, s in series.items() if len(s) >= 13}

series = align_end(series)

if len(series) < 2:
    st.info("Wybierz co najmniej 2 ETF-y z dostepnymi danymi.")
else:
    end_month = next(iter(series.values())).index[-1]
    st.caption(f"Okresy koncza sie na {end_month:%m.%Y} (ostatni pelny miesiac). Waluta: {currency}.")
    proxy_end_map = {t: proxy_info[t][1] for t in series}

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Tabela okresow", "🗓️ Stopy roczne",
                                      "🔁 Stopy kroczace", "📈 Wzrost i ryzyko"])

    # --- 1. Tabela okresow ---------------------------------------------------------
    with tab1:
        mode = st.radio("Pokaz", ["Srednioroczna (CAGR)", "Skumulowana"], horizontal=True,
                        key="lr_mode")
        col = "cagr" if mode.startswith("Sred") else "total"
        rows = []
        for t, s in series.items():
            pr = period_returns(s)
            row = {"ETF": t}
            for y in PERIOD_YEARS:
                row[period_label(y)] = fmt_pct(pr.loc[period_label(y), col])
            row[SINCE_START] = fmt_pct(pr.loc[SINCE_START, col])
            row["Dane od"] = data_since_label(s, *proxy_info[t])
            rows.append(row)
        st.dataframe(pd.DataFrame(rows).set_index("ETF"), width="stretch")
        st.caption("„—” = historia krotsza niz okres. CAGR „Od startu” liczony dla historii od 1 roku.")

    # --- 2. Stopy roczne -----------------------------------------------------------
    with tab2:
        yearly, ytd_years = {}, set()
        for t, s in series.items():
            y, ytd = calendar_year_returns(s)
            yearly[t] = y
            if ytd is not None:
                ytd_years.add(ytd)
        ydf = pd.DataFrame(yearly).sort_index()
        ytd_year = max(ytd_years) if ytd_years else None
        st.plotly_chart(yearly_returns_heatmap(ydf, ytd_year=ytd_year), width="stretch")
        full = ydf.drop(index=ytd_year) if ytd_year in ydf.index else ydf
        summary = []
        for t in ydf.columns:
            col_full = full[t].dropna()
            if col_full.empty:
                continue
            summary.append({
                "ETF": t,
                "Najlepszy rok": f"{int(col_full.idxmax())}: {fmt_pct(col_full.max())}",
                "Najgorszy rok": f"{int(col_full.idxmin())}: {fmt_pct(col_full.min())}",
                "Lata na plusie": fmt_pct((col_full > 0).mean(), 0).lstrip("+"),
                "Liczba lat": len(col_full),
            })
        if summary:
            st.dataframe(pd.DataFrame(summary).set_index("ETF"), width="stretch")
        st.caption("Pierwszy niepelny rok historii pominiety. Podsumowanie bez roku YTD.")

    # --- 3. Stopy kroczace ---------------------------------------------------------
    with tab3:
        win = st.select_slider("Okno (lata)", options=[1, 3, 5, 10, 15, 20], value=10, key="lr_win")
        rolling, rsum = {}, []
        for t, s in series.items():
            r = rolling_cagr(s, win)
            sm = rolling_summary(r)
            if sm["count"] == 0:
                rsum.append({"ETF": t, "Min": "—", "25%": "—", "Mediana": "—", "75%": "—",
                             "Max": "—", "Okna ze strata": "—",
                             "Liczba okien": f"historia < {period_label(win)}"})
                continue
            rolling[t] = r
            rsum.append({
                "ETF": t, "Min": fmt_pct(sm["min"]), "25%": fmt_pct(sm["p25"]),
                "Mediana": fmt_pct(sm["median"]), "75%": fmt_pct(sm["p75"]),
                "Max": fmt_pct(sm["max"]),
                "Okna ze strata": fmt_pct(sm["pct_negative"], 0).lstrip("+"),
                "Liczba okien": str(sm["count"]),
            })
        if rolling:
            st.plotly_chart(rolling_returns_chart(rolling, win), width="stretch")
        st.dataframe(pd.DataFrame(rsum).set_index("ETF"), width="stretch")
        st.caption(f"Kazdy punkt to CAGR z {period_label(win)} konczacych sie w danym miesiacu. "
                   "Okna nakladaja sie, wiec nie sa niezalezne.")

    # --- 4. Wzrost i ryzyko --------------------------------------------------------
    with tab4:
        same = st.toggle("Wspolny okres", value=True, key="lr_common",
                         help="Przycina wszystkie ETF-y do najpozniejszego startu, zeby porownanie bylo uczciwe.")
        view = common_window(series) if same else series
        rf_decimal = get_risk_free() / 100.0
        st.plotly_chart(growth_chart(view, proxy_end_map, start_value=10_000,
                                     currency="zl" if currency == "PLN" else "USD"),
                        width="stretch")
        risk = []
        for t, s in view.items():
            stats = calc_stats(s, trading_days=12, rf_decimal=rf_decimal)
            risk.append({
                "ETF": t, "Od": f"{s.index[0]:%m.%Y}",
                "CAGR": fmt_pct(stats["CAGR"]),
                "Zmiennosc roczna": fmt_pct(annual_volatility(s)).lstrip("+"),
                "Max drawdown": fmt_pct(stats["Max Drawdown"]),
                "Sharpe": f"{stats['Sharpe']:.2f}".replace(".", ","),
                "Sortino": f"{stats['Sortino']:.2f}".replace(".", ","),
                "Calmar": f"{stats['Calmar']:.2f}".replace(".", ","),
            })
        st.dataframe(pd.DataFrame(risk).set_index("ETF"), width="stretch")
        st.caption("Max drawdown liczony z zamkniec miesiecznych — glebokosc spadkow wewnatrz miesiaca "
                   "jest wieksza. Linia przerywana = odcinek z funduszu proxy. "
                   f"Sharpe/Sortino ze stopa wolna {rf_decimal * 100:.2f}% (biezaca)".replace(".", ",")
                   + ".")

st.caption(
    "Zrodla: Yahoo Finance (ceny skorygowane o dywidendy), FRED/OECD (kurs USD/PLN — srednia miesieczna). "
    "Fundusze proxy maja wyzsze oplaty niz ETF-y, wiec odcinek z proxy jest lekko zanizony. "
    "Wyniki historyczne nie gwarantuja przyszlych."
)

render_footer()
```

- [ ] **Step 3: Sprawdź składnię i importy**

Run: `python -m py_compile pages/6_stopy_zwrotu.py && python -c "import ast,sys; ast.parse(open('pages/6_stopy_zwrotu.py',encoding='utf-8').read())" && echo OK`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add pages/6_stopy_zwrotu.py components/auth.py
git commit -m "Add long-term returns page (premium id 26): periods, years, rolling, growth"
```

---

### Task 11: Menu, kafelek, separatory, test kolejności i smoke AppTest

**Files:**
- Modify: `app.py:28` (lista `cards`), `components/sidebar.py:51-72`, `CLAUDE.md`
- Create: `tests/test_stopy_zwrotu_page.py`

- [ ] **Step 1: Write the failing test** `tests/test_stopy_zwrotu_page.py`:

```python
"""Strona 6_stopy_zwrotu: kolejnosc w menu i smoke test renderowania."""

import os
from pathlib import Path

import pytest
from streamlit.source_util import page_sort_key

PAGES = Path(__file__).resolve().parents[1] / "pages"


def test_menu_order_between_info_and_sp500():
    order = [p.name for p in sorted(PAGES.glob("*.py"), key=page_sort_key)]
    i = order.index("6_stopy_zwrotu.py")
    assert order[i - 1] == "6_info.py"
    assert order[i + 1] == "7_sp500.py"


def test_sidebar_separators_shifted():
    css = (PAGES.parent / "components" / "sidebar.py").read_text(encoding="utf-8")
    for n in (9, 13, 16):
        assert f'a[data-testid="stSidebarNavLink"]:nth-child({n})' in css
    for n in (8, 12, 15):
        assert f'a[data-testid="stSidebarNavLink"]:nth-child({n})' not in css


def test_home_card_before_sp500():
    app = (PAGES.parent / "app.py").read_text(encoding="utf-8")
    assert app.index("pages/6_stopy_zwrotu.py") < app.index("pages/7_sp500.py")


@pytest.mark.skipif(os.environ.get("RUN_NETWORK") != "1", reason="smoke test sieciowy: RUN_NETWORK=1")
@pytest.mark.parametrize("proxy,ccy", [(False, "USD"), (True, "USD"), (True, "PLN")])
def test_page_renders(proxy, ccy):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(PAGES / "6_stopy_zwrotu.py"), default_timeout=300)
    at.session_state["premium"] = True
    at.run()
    assert not at.exception
    at.toggle(key="lr_proxy").set_value(proxy)
    at.radio(key="lr_ccy").set_value(ccy)
    at.run()
    assert not at.exception, at.exception
    assert len(at.tabs) == 4
    assert len(at.dataframe) >= 4
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_stopy_zwrotu_page.py -v`
Expected: `test_menu_order_between_info_and_sp500` PASS (plik istnieje od Task 10), `test_sidebar_separators_shifted` i `test_home_card_before_sp500` FAIL.

- [ ] **Step 3: Przesuń separatory** w `components/sidebar.py` (trzy bloki):

```python
        /* Separator between ETF section (pages 0-6, incl. 6_stopy_zwrotu) and market sections (7-10)
           UWAGA: nth-child(9) = 9. link w sidebar (strona 7_sp500).
           Jesli dodasz/usuniesz strone, zaktualizuj te indeksy! */
        a[data-testid="stSidebarNavLink"]:nth-child(9) {
```

```python
        /* Separator between market sections (7-10) and tools (11-13) */
        a[data-testid="stSidebarNavLink"]:nth-child(13) {
```

```python
        /* Separator between tools (11-13) and analytics (14-25) */
        a[data-testid="stSidebarNavLink"]:nth-child(16) {
```

(Treść reguł `margin-top/padding-top/border-top` bez zmian.)

- [ ] **Step 4: Dodaj kafelek** w `app.py`, w liście `cards` między wpisem `(6, "📖", "O strategii", ...)` a `(7, "🇺🇸", "S&P 500", ...)`:

```python
    (26, "📏", "Stopy zwrotu", "Stopy zwrotu ETF-ow do 30 lat: CAGR, lata kalendarzowe, okna kroczace, PLN", "pages/6_stopy_zwrotu.py"),
```

- [ ] **Step 5: Run tests (bez sieci)**

Run: `python -m pytest tests/ -v`
Expected: PASS wszystkich testów repo (smoke testy sieciowe SKIPPED)

- [ ] **Step 6: Run smoke test (sieć) — obowiązkowo przed pushem**

Run:
```bash
export SSL_CERT_FILE="C:/ProgramData/Norton/Antivirus/wscert.pem" REQUESTS_CA_BUNDLE="$SSL_CERT_FILE" CURL_CA_BUNDLE="$SSL_CERT_FILE"
RUN_NETWORK=1 python -m pytest tests/test_stopy_zwrotu_page.py -v
```
Expected: 6 PASS. Przy błędzie: przeczytaj `at.exception`, napraw w stronie, powtórz.

- [ ] **Step 7: Sprawdź wizualnie lokalnie**

Run: `streamlit run app.py` → w przeglądarce: link „stopy zwrotu” między „info” a „sp500”, separatory nad „sp500”, „portfolio”, „makro”; kafelek „Stopy zwrotu” przed „S&P 500”; na stronie przełącz proxy i PLN — SPY z proxy startuje w 1980, linia przerywana do 01.1993.

- [ ] **Step 8: Zaktualizuj `CLAUDE.md`** — w liście stron dopisz pozycję (w miejscu numeracji stron, przed `7_sp500`):

```markdown
- `pages/6_stopy_zwrotu.py` — **Stopy zwrotu dlugoterminowe** (premium, id gatingu 26; plik `6_` dla kolejnosci w menu przed S&P 500). 4 zakladki: tabela okresow 1–30 lat (CAGR/skumulowana), heatmapa lat kalendarzowych, kroczacy CAGR z rozkladem, wzrost 10 000 (log) + ryzyko. Dane miesieczne. Logika: `data/long_returns.py` (PROXY_MAP ETF→fundusz Vanguard, splice ze stop zwrotu, USD/PLN z FRED `CCUSMA02PLM618N` + yfinance). Separatory sidebar: nth-child(9/13/16).
```

- [ ] **Step 9: Commit**

```bash
git add app.py components/sidebar.py CLAUDE.md tests/test_stopy_zwrotu_page.py
git commit -m "Wire long-term returns page into menu, home grid and sidebar separators"
```

---

### Task 12: Deploy (po akceptacji użytkownika)

- [ ] **Step 1:** Pokaż użytkownikowi `git log --oneline origin/main..HEAD` i wynik testów z Task 11 (Step 5 i 6). Zapytaj o zgodę na push.
- [ ] **Step 2:** Po zgodzie użyj skilla `gem-dashboard-deploy` (push na `origin main`, Streamlit Cloud redeploy).
- [ ] **Step 3:** Po redeployu otwórz `https://gem-dashboard.streamlit.app/stopy_zwrotu` z kodem premium, sprawdź tryb PLN (FRED działa z chmury?) — jeśli pojawia się komunikat „od grudnia 2003”, zanotuj to w MEMORY jako znane ograniczenie.

---

## Self-review (wykonany)

- **Pokrycie specu:** decyzje 1–6 → Task 10/11; mapa proxy + warunek 0,95 → Task 3, 8; doklejanie → Task 3; zakładki 1–4 → Task 10 (+ wykresy Task 9); moduł i funkcje → Task 1–8; obsługa błędów → Task 7 (fallbacki), Task 10 (komunikaty); integracja (app.py, PAGE_INFO, sidebar, CLAUDE.md) → Task 10–11; testy jednostkowe, jakości proxy, AppTest, kolejność menu → Task 1–9, 8, 11.
- **Plan B kolejności menu** ze specu niepotrzebny: `streamlit.source_util.page_sort_key` sortuje po `(numer, nazwa)`, więc `6_info` < `6_stopy_zwrotu` < `7_sp500` — potwierdzone testem w Task 11.
- **Spójność nazw:** `load_monthly` zwraca `(series, proxy_ticker, proxy_end)` — w tej kolejności używane w stronie (`proxy_info[t] = (proxy_t, proxy_end)`, `data_since_label(s, *proxy_info[t])`). `SINCE_START = "Od startu"` używane w Task 2 i 10. `calc_stats` zwraca klucze `CAGR`, `Max Drawdown`, `Sharpe`, `Sortino`, `Calmar` (data/momentum.py:1268).
