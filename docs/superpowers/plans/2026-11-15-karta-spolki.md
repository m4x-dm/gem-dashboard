# Karta spółki — plan wdrożenia

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strona „Karta spółki” (`views/spolki/karta.py`, `?t=TICKER`) z nagłówkiem i 6 zakładkami (Przegląd free; Finanse, Wyniki, Akcjonariat, Dywidendy, Konkurencja Premium), zastępująca zakładki per-spółka na stronach S&P 500 / GPW.

**Architecture:** Logika danych w `data/company.py` (czyste funkcje + cienkie wrappery z `@st.cache_data`), UI zakładek w pakiecie `components/company/` (każdy moduł `render(ticker, market)`), strona-szkielet czyta `st.query_params["t"]`. Nawigacja do karty wyłącznie przez `nav.go_company(ticker)` / `nav.company_link(ticker)`; stary mechanizm `*_deep_dive_ticker` / `*_pending_view` / `*_finanse_*` usunięty.

**Tech Stack:** Python 3.14, Streamlit 1.55 (`st.navigation`, `st.query_params`, `st.switch_page(query_params=)`, `st.segmented_control`, `st.fragment`, `AppTest`), pandas, numpy, plotly, yfinance.

**Spec:** `docs/superpowers/specs/2026-11-15-karta-spolki-design.md`

**Konwencje wykonania:**
- Repo `C:\Users\m4x\Desktop\AI\gem-dashboard`, gałąź `company-card`. Git Bash; Python `venv/Scripts/python.exe`; testy `venv/Scripts/python.exe -m pytest -q` (stan wyjściowy: 305 passed, 41 skipped).
- Strony w `views/` (NIGDY nie tworzyć `pages/`). Strona nie woła `st.set_page_config` / `setup_sidebar()`; H1 bez emoji; tokeny kolorów z `components.constants` (zakaz `#C9A84C`, `#141929` — `tests/test_theme.py`); karty przez `components.cards.card_html`; `st.html` wycina `<svg>` (sparkline = `_sparkline_svg`).
- W zakładkach `st.stop()` zakazane (`return`); każdy `st.plotly_chart` / widget z unikalnym `key=` (prefiks zakładki: `kov_`, `kfi_`, `kre_`, `kow_`, `kdv_`, `kpe_`).
- Nie usuwać importów z `# noqa: F401`; helpery używane w `@st.fragment` na poziomie modułu; nie przypisywać `st.session_state[klucz_widgetu]` po utworzeniu widgetu (callback `on_change` może).
- W AppTest `streamlit_local_storage.LocalStorage` wisi — stubować (wzorzec: `tests/test_pages_smoke.py`, `tests/test_pulpit_offline.py`).
- Sieć lokalnie: `export SSL_CERT_FILE='C:\Users\m4x\.certs\ca-bundle-norton.pem' REQUESTS_CA_BUNDLE='C:\Users\m4x\.certs\ca-bundle-norton.pem' CURL_CA_BUNDLE='C:\Users\m4x\.certs\ca-bundle-norton.pem'` (Norton TLS).
- Zrzuty: `C:\Users\m4x\AppData\Local\Temp\claude\157479cf4eb3ddb9\a6022027-2515-4497-85e7-c873a9aed13b\scratchpad\shot.py URL OUT.png W H WAIT` (CDP, czeka na render; uruchamiać pojedynczo). Premium do zrzutów: tymczasowy nieśledzony `_preview_premium.py` w root repo (`st.session_state["premium"]=True; st.session_state["_auth_retries"]=3; exec(open("app.py",encoding="utf-8").read())`), usunąć przed commitem.
- Selektywny `git add` (nigdy: `okładka.png`, `screen2.png`, `screen3.png`, `docs/superpowers/plans/2026-06-02-finanse-kwartalne.md`, `data/cache/`, `_preview_premium.py`). Commity ze stopką `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Struktura plików

| Plik | Odpowiedzialność |
|---|---|
| `data/company.py` (nowy) | czyste: `momentum_profile`, `dividend_summary`, `dividend_after_tax`, `sector_peers`, `peer_table`, `LOWER_IS_BETTER`; wrappery: `company_profile`, `dividend_history`, `sector_caps` |
| `components/nav.py` | + `PageDef("karta", …)` jako 1. w „Spółki”; + `go_company`, `company_link` |
| `views/spolki/karta.py` (nowy) | szkielet: ticker z URL, wyszukiwarka, nagłówek, zakładki, gating |
| `components/company/__init__.py` | pusty |
| `components/company/header.py` | nagłówek |
| `components/company/overview.py` | Przegląd |
| `components/company/finance.py` | Finanse (F11) |
| `components/company/results.py` | Wyniki (F13 sub-taby 1–4) |
| `components/company/ownership.py` | Akcjonariat (F15) |
| `components/company/dividends.py` | Dywidendy |
| `components/company/peers.py` | Konkurencja |
| `views/spolki/sp500.py`, `views/spolki/gpw.py` | − zakładka Finanse, − deep dive; + „Otwórz kartę spółki” |
| `views/spolki/kalendarz_wynikow.py`, `views/spolki/insiderzy.py`, `views/start/pulpit.py`, `components/financials_ui.py` | przejścia → `nav.go_company` |
| `tests/test_company_data.py`, `tests/test_karta_offline.py` (nowe), `tests/test_nav.py`, `tests/test_pages_smoke.py` | testy |

---

### Task 1: Czyste funkcje danych `data/company.py`

**Files:** Create `data/company.py`, `tests/test_company_data.py`

- [ ] **Step 1: Testy**

`tests/test_company_data.py`:
```python
"""data/company.py — czyste funkcje karty spolki (offline)."""
import numpy as np
import pandas as pd
import pytest

from data import company as co


def _prices(n=300, tickers=("AAA", "BBB", "CCC"), seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2025-01-01", periods=n)
    data = {t: 100 * np.cumprod(1 + rng.normal(0.0005 * (i + 1), 0.01, n)) for i, t in enumerate(tickers)}
    return pd.DataFrame(data, index=idx)


# --- momentum_profile -------------------------------------------------------

def test_momentum_profile_rank_and_returns():
    p = _prices()
    prof = co.momentum_profile("CCC", p, rf=4.0)
    assert prof["of"] == 3
    assert 1 <= prof["rank"] <= 3
    for k in ("r1m", "r3m", "r6m", "r12m"):
        assert k in prof


def test_momentum_profile_unknown_ticker():
    assert co.momentum_profile("ZZZ", _prices(), rf=4.0) is None


def test_momentum_profile_short_history():
    p = _prices(n=120)
    assert co.momentum_profile("AAA", p, rf=4.0) is None


# --- dividend_summary -------------------------------------------------------

def _divs():
    dates = pd.to_datetime(["2019-05-10", "2020-05-11", "2021-05-10", "2022-05-10",
                            "2023-05-10", "2024-05-10", "2025-05-12"])
    return pd.Series([1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6], index=dates)


def test_dividend_summary_basic():
    s = co.dividend_summary(_divs(), price=40.0, info={"dividendYield": 0.04, "payoutRatio": 0.5},
                            today=pd.Timestamp("2026-11-15"))
    assert s["pays"] is True
    assert s["yield"] == pytest.approx(0.04)
    assert s["payout"] == pytest.approx(0.5)
    assert s["years_paid"] == 7          # 2019..2025 bez przerw
    # cagr5: 2025 (1.6) vs 2020 (1.1)
    assert s["cagr5"] == pytest.approx((1.6 / 1.1) ** (1 / 5) - 1)
    assert list(s["annual"].index)[-1] == 2025
    assert len(s["last8"]) == 7


def test_dividend_summary_yield_fallback_from_ttm():
    divs = pd.Series([0.5, 0.5], index=pd.to_datetime(["2026-03-01", "2026-09-01"]))
    s = co.dividend_summary(divs, price=50.0, info={}, today=pd.Timestamp("2026-11-15"))
    assert s["yield"] == pytest.approx(1.0 / 50.0)


def test_dividend_summary_yield_percent_normalised():
    # yfinance >= 0.2.5x zwraca dividendYield w procentach (np. 0.41 = 0,41%)
    s = co.dividend_summary(_divs(), price=40.0, info={"dividendYield": 4.0},
                            today=pd.Timestamp("2026-11-15"))
    assert s["yield"] == pytest.approx(0.04)


def test_dividend_summary_no_dividends():
    assert co.dividend_summary(pd.Series(dtype=float), price=10.0, info={},
                               today=pd.Timestamp("2026-11-15")) == {"pays": False}


# --- dividend_after_tax -----------------------------------------------------

@pytest.mark.parametrize("market,account,rate", [
    ("GPW", "zwykle", 0.19), ("GPW", "ike", 0.0), ("GPW", "ikze", 0.0),
    ("SP500", "zwykle", 0.19), ("SP500", "ike", 0.15), ("SP500", "ikze", 0.15),
])
def test_dividend_after_tax(market, account, rate):
    r = co.dividend_after_tax(10_000, 0.05, market, account)
    assert r["gross"] == pytest.approx(500.0)
    assert r["tax"] == pytest.approx(500.0 * rate)
    assert r["net"] == pytest.approx(500.0 * (1 - rate))
    assert r["note"]


# --- sector_peers -----------------------------------------------------------

def test_sector_peers_nearest_log_cap():
    caps = pd.Series({"X": 100e9, "A": 90e9, "B": 120e9, "C": 1e9, "D": 3000e9, "E": 80e9, "F": 50e9})
    assert co.sector_peers("X", caps, n=3) == ["A", "B", "E"]


def test_sector_peers_small_sector():
    caps = pd.Series({"X": 10e9, "A": 5e9})
    assert co.sector_peers("X", caps, n=5) == ["A"]


def test_sector_peers_missing_cap_returns_largest():
    caps = pd.Series({"A": 5e9, "B": 50e9, "C": 20e9})
    assert co.sector_peers("X", caps, n=2) == ["B", "C"]


# --- peer_table -------------------------------------------------------------

def test_peer_table_median_row():
    rows = {
        "X": {"market_cap": 100e9, "pe": 20.0, "fwd_pe": 18.0, "ev_ebitda": 12.0, "roe": 0.2,
              "profit_margin": 0.1, "revenue_growth": 0.05, "dividend_yield": 0.01, "mom12": 0.3},
        "A": {"market_cap": 80e9, "pe": 10.0, "fwd_pe": None, "ev_ebitda": 8.0, "roe": 0.1,
              "profit_margin": 0.2, "revenue_growth": 0.1, "dividend_yield": None, "mom12": 0.1},
    }
    df = co.peer_table(rows)
    assert list(df.index) == ["X", "A", "Mediana grupy"]
    assert df.loc["Mediana grupy", "P/E"] == pytest.approx(15.0)
    assert df.loc["Mediana grupy", "Forward P/E"] == pytest.approx(18.0)
    assert np.isnan(df.loc["A", "Forward P/E"])
    assert set(co.LOWER_IS_BETTER) == {"P/E", "Forward P/E", "EV/EBITDA"}
```

- [ ] **Step 2: Uruchom — FAIL** (`ImportError: cannot import name 'company'`)

Run: `venv/Scripts/python.exe -m pytest tests/test_company_data.py -q`

- [ ] **Step 3: Implementacja czystych funkcji**

`data/company.py`:
```python
"""Karta spolki — logika danych (bez UI).

Czyste funkcje przyjmuja dane jako argumenty (testy offline).
Wrappery pobierajace (company_profile, dividend_history, sector_caps) — Task 2.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from data.momentum import build_ranking

LOWER_IS_BETTER = ("P/E", "Forward P/E", "EV/EBITDA")

PEER_COLUMNS = {
    "Kapitalizacja": "market_cap",
    "P/E": "pe",
    "Forward P/E": "fwd_pe",
    "EV/EBITDA": "ev_ebitda",
    "ROE": "roe",
    "Marża netto": "profit_margin",
    "Wzrost przychodów": "revenue_growth",
    "Stopa dywidendy": "dividend_yield",
    "Momentum 12M": "mom12",
}

_MIN_HISTORY = 273  # 12-1 momentum (jak ranking akcji)


def _f(x) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return np.nan
    return v if np.isfinite(v) else np.nan


def momentum_profile(ticker: str, prices: pd.DataFrame, rf: float, skip_month: bool = True) -> dict | None:
    """Miejsce w rankingu momentum (ta sama regula co ranking akcji, 12-1) + stopy 1/3/6/12M."""
    if ticker not in prices.columns or prices[ticker].dropna().shape[0] < _MIN_HISTORY:
        return None
    ranking = build_ranking(prices, rf, skip_month=skip_month).dropna(subset=["Wynik"])
    if ticker not in ranking.index:
        return None
    ranking = ranking.sort_values("Wynik", ascending=False)
    row = ranking.loc[ticker]
    return {
        "rank": int(list(ranking.index).index(ticker)) + 1,
        "of": int(len(ranking)),
        "r1m": _f(row.get("1M")), "r3m": _f(row.get("3M")),
        "r6m": _f(row.get("6M")), "r12m": _f(row.get("12M")),
    }


def _norm_yield(y) -> float:
    """yfinance raz zwraca 0.004 (ulamek), raz 0.4 (procent) — normalizuj do ulamka."""
    v = _f(y)
    if np.isnan(v):
        return np.nan
    return v / 100 if v > 0.25 else v


def dividend_summary(divs: pd.Series, price: float | None, info: dict, today: pd.Timestamp) -> dict:
    if divs is None or len(divs.dropna()) == 0:
        return {"pays": False}
    divs = divs.dropna().sort_index()
    divs.index = pd.to_datetime(divs.index).tz_localize(None) if getattr(divs.index, "tz", None) else pd.to_datetime(divs.index)
    today = pd.Timestamp(today).normalize()

    y = _norm_yield(info.get("dividendYield"))
    if np.isnan(y) and price and price > 0:
        ttm = divs[divs.index > today - pd.DateOffset(years=1)].sum()
        y = ttm / price if ttm > 0 else np.nan

    annual = divs.groupby(divs.index.year).sum()
    last_full = today.year - 1
    annual = annual[annual.index <= last_full]
    years_paid = 0
    yr = last_full
    while yr in annual.index and annual.loc[yr] > 0:
        years_paid += 1
        yr -= 1

    cagr5 = None
    if last_full in annual.index and (last_full - 5) in annual.index and annual.loc[last_full - 5] > 0:
        cagr5 = (annual.loc[last_full] / annual.loc[last_full - 5]) ** (1 / 5) - 1

    return {
        "pays": True,
        "yield": y,
        "payout": _f(info.get("payoutRatio")),
        "years_paid": years_paid,
        "cagr5": cagr5,
        "annual": annual.tail(10),
        "last8": divs.tail(8),
    }


_TAX = {
    ("GPW", "zwykle"): (0.19, "Podatek Belki 19% pobiera dom maklerski."),
    ("GPW", "ike"): (0.0, "Na IKE dywidendy z polskich spolek sa wolne od podatku."),
    ("GPW", "ikze"): (0.0, "Na IKZE dywidendy z polskich spolek sa wolne od podatku (podatek przy wyplacie z IKZE)."),
    ("SP500", "zwykle"): (0.19, "15% pobiera USA (z formularzem W-8BEN), 4% doplaca sie w Polsce — razem 19%."),
    ("SP500", "ike"): (0.15, "Na IKE nadal 15% pobiera USA (W-8BEN); polskiego podatku brak."),
    ("SP500", "ikze"): (0.15, "Na IKZE nadal 15% pobiera USA (W-8BEN); polskiego podatku brak."),
}


def dividend_after_tax(amount: float, yield_: float, market: str, account: str = "zwykle") -> dict:
    rate, note = _TAX[(market, account)]
    gross = float(amount) * float(yield_)
    tax = gross * rate
    return {"gross": gross, "tax": tax, "net": gross - tax, "note": note}


def sector_peers(ticker: str, caps: pd.Series, n: int = 5) -> list[str]:
    caps = caps.dropna()
    caps = caps[caps > 0]
    others = caps.drop(labels=[ticker], errors="ignore")
    if ticker not in caps.index:
        return list(others.sort_values(ascending=False).head(n).index)
    dist = (np.log(others) - np.log(caps.loc[ticker])).abs()
    return list(dist.sort_values(kind="stable").head(n).index)


def peer_table(rows: dict[str, dict]) -> pd.DataFrame:
    data = {t: {col: _f(r.get(key)) for col, key in PEER_COLUMNS.items()} for t, r in rows.items()}
    df = pd.DataFrame.from_dict(data, orient="index", columns=list(PEER_COLUMNS))
    df.loc["Mediana grupy"] = df.median(numeric_only=True, skipna=True)
    return df
```

- [ ] **Step 4: Uruchom — PASS** (`venv/Scripts/python.exe -m pytest tests/test_company_data.py -q` → wszystkie zielone; jeśli `test_sector_peers_nearest_log_cap` daje inną kolejność, przelicz odległości log: A 0,105, B 0,182, E 0,223, F 0,693 — oczekiwane `["A","B","E"]`).

- [ ] **Step 5: Commit** — `git add data/company.py tests/test_company_data.py` → „Add pure data functions for the company card”.

---

### Task 2: Wrappery pobierające w `data/company.py`

**Files:** Modify `data/company.py`; Test `tests/test_company_data.py`

- [ ] **Step 1: Test (offline, z monkeypatch)** — dopisz:
```python
def test_sector_caps_uses_info(monkeypatch):
    import data.company as c
    fake = {"AAA": {"marketCap": 10}, "BBB": {"marketCap": None}, "CCC": {}}
    monkeypatch.setattr(c, "_fetch_info", lambda t: fake.get(t, {}))
    monkeypatch.setattr(c, "_sector_members", lambda market, sector: ["AAA", "BBB", "CCC"])
    caps = c.sector_caps.__wrapped__("SP500", "Tech")
    assert caps.to_dict() == {"AAA": 10.0}


def test_company_profile_fields(monkeypatch):
    import data.company as c
    monkeypatch.setattr(c, "_fetch_info", lambda t: {"longBusinessSummary": "x", "beta": 1.2,
                                                     "fiftyTwoWeekLow": 1, "fiftyTwoWeekHigh": 2,
                                                     "exchange": "NMS", "currency": "USD"})
    p = c.company_profile.__wrapped__("AAA")
    assert p == {"summary": "x", "beta": 1.2, "low52": 1.0, "high52": 2.0, "exchange": "NMS", "currency": "USD"}
```
(`st.cache_data` udostępnia `__wrapped__` — sprawdź w 1.55: `hasattr(fn, "__wrapped__")`; jeśli brak, wywołaj `c.sector_caps.clear()` i funkcję bezpośrednio).

- [ ] **Step 2: FAIL** — brak funkcji.
- [ ] **Step 3: Implementacja** — dopisz na końcu `data/company.py`:
```python
import streamlit as st
from concurrent.futures import ThreadPoolExecutor

from data.financials import _fetch_info  # noqa: E402 — cache 24h, curl_cffi session


def _sector_members(market: str, sector: str) -> list[str]:
    if market == "GPW":
        from data.gpw_universe import GPW_SECTOR_MAP as m
    else:
        from data.sp500_universe import SP500_SECTOR_MAP as m
    return [t for t, s in m.items() if s == sector]


def sector_of(ticker: str, market: str) -> str | None:
    if market == "GPW":
        from data.gpw_universe import GPW_SECTOR_MAP as m
    else:
        from data.sp500_universe import SP500_SECTOR_MAP as m
    return m.get(ticker)


@st.cache_data(ttl=86400, show_spinner=False)
def sector_caps(market: str, sector: str) -> pd.Series:
    members = _sector_members(market, sector)

    def cap(t):
        try:
            return t, _f((_fetch_info(t) or {}).get("marketCap"))
        except Exception:
            return t, np.nan

    with ThreadPoolExecutor(max_workers=8) as ex:
        pairs = list(ex.map(cap, members))
    s = pd.Series(dict(pairs), dtype=float).dropna()
    return s[s > 0]


@st.cache_data(ttl=86400, show_spinner=False)
def company_profile(ticker: str) -> dict:
    info = _fetch_info(ticker) or {}
    return {
        "summary": info.get("longBusinessSummary"),
        "beta": None if np.isnan(_f(info.get("beta"))) else _f(info.get("beta")),
        "low52": None if np.isnan(_f(info.get("fiftyTwoWeekLow"))) else _f(info.get("fiftyTwoWeekLow")),
        "high52": None if np.isnan(_f(info.get("fiftyTwoWeekHigh"))) else _f(info.get("fiftyTwoWeekHigh")),
        "exchange": info.get("exchange"),
        "currency": info.get("currency"),
    }


@st.cache_data(ttl=86400, show_spinner=False)
def dividend_history(ticker: str) -> pd.Series:
    import yfinance as yf
    from data.financials import _get_yf_session
    try:
        d = yf.Ticker(ticker, session=_get_yf_session()).dividends
    except Exception:
        return pd.Series(dtype=float)
    if d is None or len(d) == 0:
        return pd.Series(dtype=float)
    d.index = pd.to_datetime(d.index).tz_localize(None) if d.index.tz is not None else pd.to_datetime(d.index)
    return d.astype(float)
```
(Importy przenieś na górę pliku przy commicie, jeśli linter/konwencja tego wymaga — kolejność bez znaczenia funkcjonalnego.)
- [ ] **Step 4: PASS** + pełna suita offline.
- [ ] **Step 5: Commit** „Add cached fetchers for company card (profile, dividends, sector caps)”.

---

### Task 3: Rejestr i nawigacja do karty

**Files:** Modify `components/nav.py`, `tests/test_nav.py`; Create `views/spolki/karta.py` (zaślepka)

- [ ] **Step 1: Testy** w `tests/test_nav.py`:
```python
def test_karta_first_in_spolki_and_free():
    spolki = [p for p in nav.PAGES if p.section == "Spółki"]
    assert spolki[0].key == "karta"
    assert nav.get("karta").free is True
    assert nav.get("karta").path == "views/spolki/karta.py"


def test_company_nav_helpers_exist():
    assert callable(nav.go_company) and callable(nav.company_link)
```
(oraz zaktualizuj `test_page_count` 24 → 25).
- [ ] **Step 2: FAIL.**
- [ ] **Step 3:** W `PAGES` dodaj przed `sp500`:
```python
    PageDef("karta", "views/spolki/karta.py", "Karta spółki", ":material/badge:", "Spółki", True,
            "Jedna spolka: przeglad, finanse, wyniki, akcjonariat, dywidendy, konkurencja"),
```
Na końcu `components/nav.py`:
```python
def go_company(ticker: str) -> None:
    """Otwiera Karte spolki dla tickera (ticker w adresie: ?t=...)."""
    st.switch_page(get("karta").path, query_params={"t": ticker})


def company_link(ticker: str, label: str | None = None, **kwargs) -> None:
    p = get("karta")
    st.page_link(p.path, label=label or ticker, query_params={"t": ticker}, **kwargs)
```
Zaślepka `views/spolki/karta.py`:
```python
import streamlit as st
from components.sidebar import render_footer

st.markdown("# Karta spółki")
st.info("W przebudowie")
render_footer()
```
- [ ] **Step 4: PASS** (cała suita; `test_every_page_file_is_registered` zielony).
- [ ] **Step 5: Commit** „Register company card page and add go_company navigation”.

---

### Task 4: Szkielet strony + nagłówek

**Files:** Rewrite `views/spolki/karta.py`; Create `components/company/__init__.py` (pusty), `components/company/header.py`; Create `tests/test_karta_offline.py`

- [ ] **Step 1: Test offline** `tests/test_karta_offline.py`:
```python
"""Karta spolki przez router — offline (dane podstawione)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")
PAGE = "views/spolki/karta.py"


class _FakeLS:
    def __init__(self, *a, **k): pass
    def getItem(self, *a, **k): return None
    def setItem(self, *a, **k): return None


def _series(n=400, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2025-01-01", periods=n)
    return pd.Series(100 * np.cumprod(1 + rng.normal(0.0005, 0.01, n)), index=idx)


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    import streamlit_local_storage
    import data.downloader as dl
    import data.financials as fin
    import data.company as co
    monkeypatch.setattr(streamlit_local_storage, "LocalStorage", _FakeLS)
    monkeypatch.setattr(dl, "download_single", lambda t, period="15y": _series())
    monkeypatch.setattr(dl, "download_prices",
                        lambda ts, period="15y": pd.DataFrame({t: _series(seed=i) for i, t in enumerate(ts[:30])}))
    monkeypatch.setattr(co, "universe_prices",
                        lambda u, period="2y": pd.DataFrame({t: _series(seed=i) for i, t in enumerate(("AAPL", "CDR.WA", *u[:30]))}))
    monkeypatch.setattr(fin, "get_ratios_snapshot", lambda t: {"pe": 20.0, "fwd_pe": 18.0, "market_cap": 1e12,
                                                               "dividend_yield": 0.5, "name": "Apple Inc.",
                                                               "current_price": 100.0, "currency": "USD"})
    monkeypatch.setattr(fin, "get_analyst_recos", lambda t: {})
    monkeypatch.setattr(fin, "fetch_earnings_dates", lambda t: None)
    monkeypatch.setattr(co, "company_profile", lambda t: {"summary": "Opis.", "beta": 1.1, "low52": 80.0,
                                                          "high52": 120.0, "exchange": "NMS", "currency": "USD"})
    monkeypatch.setattr(co, "dividend_history", lambda t: pd.Series(dtype=float))
    monkeypatch.setattr(co, "sector_caps", lambda m, s: pd.Series({"AAPL": 1e12, "MSFT": 9e11}))


def _run(premium: bool, t: str | None):
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["premium"] = premium
    at.session_state["_auth_retries"] = 3
    if t is not None:
        at.query_params["t"] = t
    at.switch_page(PAGE).run()
    return at


def _html(at):
    return " ".join(e.proto.body for e in at.get("html"))


def test_free_shows_overview_and_five_teasers():
    at = _run(False, "AAPL")
    assert not at.exception, at.exception
    assert len(at.tabs) >= 6
    assert _html(at).count("🔒") == 5


def test_premium_renders_all_tabs():
    at = _run(True, "AAPL")
    assert not at.exception, at.exception
    assert _html(at).count("🔒") == 0


def test_unknown_ticker_message():
    at = _run(False, "XXX")
    assert not at.exception
    assert any("Nie znaleziono spółki" in str(m.value) for m in at.markdown + at.warning + at.info)


def test_no_ticker_shows_search():
    at = _run(False, None)
    assert not at.exception
    assert at.selectbox(key="karta_search") is not None
```
(Jeśli `at.query_params` nie istnieje w 1.55 jako mutowalny słownik, ustaw przez `at.query_params = {"t": t}` — sprawdź w `streamlit/testing/v1/app_test.py`; zanotuj w raporcie.)

- [ ] **Step 2: FAIL** (zaślepka nie ma zakładek).

- [ ] **Step 3: `components/company/header.py`**:
```python
"""Naglowek karty spolki: ticker, nazwa, sektor, gielda, cena + zmiana dnia, watchlista."""
import pandas as pd
import streamlit as st

from components.cards import card_html  # noqa: F401  (spojny styl w pozostalych modulach)
from components.constants import TEXT, MUTED, GREEN, RED
from data import company as co
from data.downloader import download_single
from data.gpw_universe import GPW_NAMES
from data.sp500_universe import SP500_NAMES

EXCHANGE = {"SP500": "NYSE / NASDAQ", "GPW": "GPW"}


def company_name(ticker: str, market: str) -> str:
    return (GPW_NAMES if market == "GPW" else SP500_NAMES).get(ticker, ticker)


def render(ticker: str, market: str) -> None:
    s = download_single(ticker, period="1y")
    price = chg = None
    if s is not None and len(s.dropna()) >= 2:
        s = s.dropna()
        price, chg = float(s.iloc[-1]), float(s.iloc[-1] / s.iloc[-2] - 1)
    ccy = "zł" if market == "GPW" else "$"
    sector = co.sector_of(ticker, market) or ""
    pill = ""
    if chg is not None:
        col, bg = (GREEN, "rgba(52,211,153,.12)") if chg >= 0 else (RED, "rgba(248,113,113,.12)")
        pill = (f'<span style="background:{bg};color:{col};padding:2px 9px;border-radius:999px;'
                f'font-size:12px">{chg*100:+.2f}% dziś</span>')
    price_txt = f"{price:,.2f} {ccy}".replace(",", " ").replace(".", ",") if price is not None else "—"
    st.html(
        f'<div style="display:flex;align-items:flex-end;gap:16px;margin:4px 0 10px">'
        f'<div><div style="font-size:26px;font-weight:700;color:{TEXT}">{ticker}</div>'
        f'<div style="color:{MUTED};font-size:14px">{company_name(ticker, market)} · {sector} · {EXCHANGE[market]}</div></div>'
        f'<div style="margin-left:auto;text-align:right"><div style="font-size:26px;font-weight:650;'
        f'color:{TEXT};font-variant-numeric:tabular-nums">{price_txt}</div>{pill}</div></div>'
    )
```
(Watchlista ☆ w nagłówku: przycisk `st.button("Dodaj do watchlisty" / "Usuń z watchlisty", key="karta_wl")` widoczny tylko gdy `is_premium()`; używa `components.watchlist.toggle_ticker(LocalStorage(), ticker)` + `st.rerun()`. Free: `st.caption("Watchlista w Premium")`. Dodaj to w `render` po `st.html` — import `from components.auth import is_premium` i `LocalStorage` wewnątrz gałęzi Premium, żeby free nie tworzył komponentu.)

- [ ] **Step 4: `views/spolki/karta.py`**:
```python
"""Karta spolki — jedna spolka (S&P 500 / GPW), ticker w adresie ?t=TICKER."""
import streamlit as st

from components import nav
from components.auth import is_premium, premium_teaser
from components.company import header
from components.sidebar import render_footer
from data.financials import _detect_market
from data.gpw_universe import GPW_NAMES
from data.sp500_universe import SP500_NAMES

TABS = ["Przegląd", "Finanse", "Wyniki", "Akcjonariat", "Dywidendy", "Konkurencja"]
TEASERS = {
    "Finanse": "Wskaźniki, konsensus EPS, historia wyników i rekomendacje analityków.",
    "Wyniki": "Wyniki kwartalne vs prognozy, rachunek zysków i strat, bilans, przepływy.",
    "Akcjonariat": "Główni akcjonariusze, fundusze, transakcje insiderów.",
    "Dywidendy": "Historia wypłat, stopa, wzrost dywidendy i kalkulator dochodu po podatku.",
    "Konkurencja": "Porównanie wskaźników z 5 najbliższymi spółkami z sektora.",
}
NAMES = {**SP500_NAMES, **GPW_NAMES}


def _on_pick():
    t = st.session_state.get("karta_search")
    if t:
        st.query_params["t"] = t


def _search(current: str | None) -> None:
    options = [""] + sorted(NAMES, key=lambda t: NAMES[t])
    st.selectbox("Szukaj spółki (S&P 500 i GPW)", options,
                 index=options.index(current) if current in options else 0,
                 key="karta_search", on_change=_on_pick,
                 format_func=lambda t: "Wpisz nazwę lub ticker…" if not t else f"{t} — {NAMES[t]}")


def _render_tab(name: str, ticker: str, market: str) -> None:
    from components.company import overview, finance, results, ownership, dividends, peers
    mod = {"Przegląd": overview, "Finanse": finance, "Wyniki": results,
           "Akcjonariat": ownership, "Dywidendy": dividends, "Konkurencja": peers}[name]
    try:
        mod.render(ticker, market)
    except Exception:
        st.caption(f"{name}: dane chwilowo niedostępne")


ticker = (st.query_params.get("t") or "").upper().strip() or None
st.markdown("# Karta spółki")
_search(ticker)

if ticker is None:
    st.caption("Wybierz spółkę, aby zobaczyć jej kartę.")
elif ticker not in NAMES:
    st.warning(f"Nie znaleziono spółki {ticker} w S&P 500 ani na GPW.")
else:
    market = _detect_market(ticker)
    header.render(ticker, market)
    tabs = st.tabs(TABS)
    for name, tab in zip(TABS, tabs):
        with tab:
            if name == "Przegląd" or is_premium():
                _render_tab(name, ticker, market)
            else:
                premium_teaser(name, TEASERS[name])

render_footer()
```
Na tym etapie utwórz moduły zakładek jako minimalne zaślepki (każdy plik `components/company/<x>.py` z `def render(ticker, market): st.caption("W przebudowie")` i `import streamlit as st`), żeby import działał — Task 5–8 je wypełnią. `NAMES` sprawdza universe; `_detect_market` zwraca `"SP500"`/`"GPW"`.
- [ ] **Step 5: PASS** `tests/test_karta_offline.py` + suita. **Step 6: Commit** „Company card page skeleton with header, tabs and premium gating”.

---

### Task 5: Przegląd (`components/company/overview.py`)

**Files:** Modify `components/company/overview.py`; Test `tests/test_karta_offline.py` (już pokrywa render)

Zawartość (spec „Przegląd”, makieta A `.superpowers/brainstorm/10355-1794775015/content/karta-przeglad.html`):
- [ ] **Step 1:** `render(ticker, market)`:
  1. `c_chart, c_kv = st.columns([2, 1])`.
  2. Wykres: `rng = st.segmented_control("Okres", ["1M","6M","1R","5L","Max"], default="1R", key="kov_range", label_visibility="collapsed")`; mapowanie na `period` dla `download_single` (`1M→"1mo"`, `6M→"6mo"`, `1R→"1y"`, `5L→"5y"`, `Max→"max"`); `go.Figure(go.Scatter(x=s.index, y=s, mode="lines", line=dict(color=GREEN if s.iloc[-1]>=s.iloc[0] else RED, width=1.8)))` z `fig.update_layout(**_base_layout(height=320))`, `st.plotly_chart(fig, key="kov_price", width="stretch")`.
  3. Panel kluczowych danych (`card_html`): z `get_ratios_snapshot(ticker)` i `co.company_profile(ticker)`: Kapitalizacja (`format_large_number` z `components.financials_ui` lub lokalny formatter), `P/E · Forward P/E`, `EV/EBITDA` — **gdy `market=="GPW"` i `ticker in GPW_BANKS` → wiersz `P/B` z `price_to_book`**, Stopa dywidendy (`co._norm_yield`), Beta, zakres 52 tyg. z markerem (div `position:relative` + marker `left:{(price-low)/(high-low)*100:.0f}%`).
  4. Trzy karty w `st.columns(3)`: **Analitycy** (`get_analyst_recos`; brak → „Brak pokrycia analityków”; pasek min–cena–cel–max jak w makiecie), **Kalendarz** (`fetch_earnings_dates(ticker)` → najbliższa przyszła data; ostatni ex-dividend z `co.dividend_history` (ostatnia data); ostatni beat/miss z `get_earnings_history(ticker, n_quarters=1)` `surprise_pct`), **Momentum GEM** — miejsce z `mov_slot = st.container()` (pusty kontener w 3. kolumnie).
  5. „O spółce”: `summary` przycięte do 300 znaków + `st.expander("Rozwiń opis")` z pełnym tekstem; `None` → pomiń sekcję.
  6. Na końcu `with mov_slot: _momentum_fragment(ticker, market)` — moduł-level `@st.fragment def _momentum_fragment(ticker, market)`: universe `ALL_SP500_TICKERS` / `ALL_GPW_TICKERS`, `prices = co.universe_prices(tuple(universe), "2y")` (zbiorczy `yf.download` bez fallbacku per ticker, cache 1 h; `download_prices` przy zimnym cache trwał ~3 min), `rf = get_risk_free()`, `prof = co.momentum_profile(ticker, prices, rf)`; `None` → „Za krótka historia notowań”; inaczej „#{rank} z {of} w {S&P 500|GPW}” + 4 kafle 1M/3M/6M/12M (kolor GREEN/RED).
  Każdy blok w `try/except` → `st.caption("…: dane chwilowo niedostępne")`.
- [ ] **Step 2:** Testy offline zielone; zrzut free `http://localhost:8596/karta?t=AAPL` (1440x1800, wait 90) i `?t=PKO.WA` (bank → P/B) — obejrzeć, poprawić.
- [ ] **Step 3: Commit** „Company card: overview tab”.

---

### Task 6: Finanse / Wyniki / Akcjonariat (przeniesienie)

**Files:** Modify `components/company/finance.py`, `results.py`, `ownership.py`

- [ ] **Step 1: `finance.py`** — przenieś ciało fragmentu `_finanse_fragment` z `views/spolki/sp500.py` (zakładka `tab7`, linie od `snap = get_ratios_snapshot(ticker)` do kart `analyst_recos_card(recos)`) **bez selectboxa spółki** (ticker z parametru), z `is_bank = market == "GPW" and ticker in GPW_BANKS` (tak jak w `views/spolki/gpw.py`). Nagłówki bez emoji.
- [ ] **Step 2: `results.py`** — `st.tabs(["Beat/miss", "Rachunek zysków i strat", "Bilans", "Przepływy"])` wołające `financials_ui._render_beat_miss_tab`, `_render_income_statement_tab`, `_render_balance_sheet_tab`, `_render_cashflow_tab` (ticker z parametru). Nad zakładkami 4 metryki z nagłówka dawnego `render_sprawozdania_deep_dive` (EPS ostatni vs est, beat streak, Forward Q+1 EPS, Forward Q+1 Revenue) — przenieś ten blok jako funkcję `_summary_metrics(ticker)`.
- [ ] **Step 3: `ownership.py`** — `financials_ui._render_insiders_tab(ticker)`; dla `market=="GPW"` zachowaj istniejącą notę o ograniczonych danych (jest w `_render_insiders_tab`).
- [ ] **Step 4:** testy offline (premium) zielone; zrzut premium `?t=AAPL` każdej z 3 zakładek (kliknięcie zakładki nie jest możliwe w `shot.py` — wystarczy, że AppTest premium przechodzi; wizualnie sprawdź w Task 10).
- [ ] **Step 5: Commit** „Company card: finance, results and ownership tabs”.

---

### Task 7: Dywidendy (`components/company/dividends.py`)

- [ ] **Step 1:** `render(ticker, market)`:
```python
divs = co.dividend_history(ticker)
info = _fetch_info(ticker) or {}          # from data.financials import _fetch_info
price = (get_ratios_snapshot(ticker) or {}).get("current_price")
s = co.dividend_summary(divs, price, info, today=pd.Timestamp.now())
if not s["pays"]:
    st.info("Spółka nie wypłaca dywidendy.")
    return
```
Kafle (4 × `card_html`): Stopa dywidendy (`fmt_pct`), Wskaźnik wypłaty, Lata z rzędu, Wzrost 5 lat (CAGR; `None` → „—”). Wykres słupkowy `s["annual"]` (`go.Bar`, kolor GOLD, `_base_layout(height=260)`, `key="kdv_annual"`). Tabela `s["last8"]` (data `%d.%m.%Y`, kwota, waluta z `company_profile`). Kalkulator: `amount = st.number_input("Kwota inwestycji", min_value=0.0, value=10000.0, step=1000.0, key="kdv_amount")`, `acc = st.segmented_control("Konto", ["Zwykłe","IKE","IKZE"], default="Zwykłe", key="kdv_acc")` → `co.dividend_after_tax(amount, s["yield"], market, {"Zwykłe":"zwykle","IKE":"ike","IKZE":"ikze"}[acc])` → 3 wartości (brutto/podatek/netto) + `st.caption(note)`. Gdy `s["yield"]` NaN → kalkulator ukryty z notą „Brak aktualnej stopy dywidendy”.
- [ ] **Step 2:** testy (dopisz w `tests/test_karta_offline.py` wariant z `dividend_history` zwracającym 6 lat wypłat i premium → brak wyjątku). Zrzut premium `?t=PZU.WA` (płaci dywidendę) i `?t=AMZN` (nie płaci).
- [ ] **Step 3: Commit** „Company card: dividends tab with after-tax calculator”.

---

### Task 8: Konkurencja (`components/company/peers.py`)

- [ ] **Step 1:** `render(ticker, market)`:
  - `sector = co.sector_of(ticker, market)`; brak → „Brak przypisanego sektora”.
  - `with st.spinner("Pobieram kapitalizacje sektora…"): caps = co.sector_caps(market, sector)`.
  - `default = co.sector_peers(ticker, caps, n=5)`; `options = [t for t in co._sector_members(market, sector) if t != ticker]`; `chosen = st.multiselect("Porównaj z", options, default=default, max_selections=8, key=f"kpe_sel_{ticker}", format_func=lambda t: f"{t} — {name(t)}")`.
  - `rows = {t: {**get_ratios_snapshot(t), "mom12": mom12.get(t)} for t in [ticker, *chosen]}`, gdzie `mom12` = kolumna `12M` z `latest_returns(co.universe_prices(tuple(universe), "2y"), skip_month=True)` (wspólny cache z fragmentem momentum; NIE `download_prices`); `co._norm_yield` dla `dividend_yield`.
  - `df = co.peer_table(rows)`; render jako `st.html` tabela (nie `st.dataframe`, żeby kolorować komórki): wiersz `ticker` pogrubiony z tłem `BG_HOVER`; wiersz „Mediana grupy” MUTED; komórka zielona gdy lepsza od mediany (dla `LOWER_IS_BETTER` niższa), czerwona gdy gorsza, „—” dla NaN; formaty: Kapitalizacja → `format_large_number`, procenty (ROE, Marża netto, Wzrost przychodów, Stopa dywidendy, Momentum 12M) → `fmt_pct`, mnożniki → `"{:.1f}"`. Owinąć w `<div style="overflow-x:auto">` (telefon).
- [ ] **Step 2:** testy offline premium zielone; zrzut premium `?t=AAPL` i `?t=CDR.WA`.
- [ ] **Step 3: Commit** „Company card: peers tab”.

---

### Task 9: Migracja stron rynków i przejść do karty

**Files:** `views/spolki/sp500.py`, `views/spolki/gpw.py`, `views/spolki/kalendarz_wynikow.py`, `views/spolki/insiderzy.py`, `views/start/pulpit.py`, `components/financials_ui.py`, `tests/test_nav.py`

- [ ] **Step 1: Test** w `tests/test_nav.py`:
```python
@pytest.mark.parametrize("needle", ["deep_dive_ticker", "pending_view", "_finanse_ticker", "_finanse_default"])
def test_no_legacy_deep_dive_state(needle):
    hits = [p.relative_to(ROOT).as_posix() for p in list((ROOT / "views").rglob("*.py")) + list((ROOT / "components").rglob("*.py"))
            if needle in p.read_text(encoding="utf-8")]
    assert hits == []
```
- [ ] **Step 2: FAIL** (lista plików: sp500, gpw, kalendarz_wynikow, insiderzy, pulpit).
- [ ] **Step 3: sp500.py / gpw.py:**
  - usuń z `st.tabs([...])` pozycję „💰 Finanse” i cały blok `with tab7:` (fragment F11) — zmienne zakładek przenumeruj (8 → 7);
  - w „📈 Sprawozdania Q” zostaw tylko `render_sprawozdania_screener(...)`; usuń radio/przełączanie na deep dive, `default_index`, `pending`, `render_sprawozdania_deep_dive` i obsługę `*_pending_view` na górze pliku (blok `_pending_dd_ticker`);
  - w zakładce Ranking (tab1) pod tabelą: `pick = st.selectbox("Spółka", ranking.index, key="sp_card_pick", format_func=...)` + `if st.button("Otwórz kartę spółki", key="sp_card_btn"): nav.go_company(pick)` (GPW: klucze `gpw_card_*`);
  - w Screeningu (tab6, F12) zamień przycisk „💰 Pokaż w Finanse” na „Otwórz kartę spółki” → `nav.go_company(selected)`; usuń ustawianie `sp_finanse_*` / `gpw_finanse_*`.
- [ ] **Step 4: financials_ui.py** — w `render_sprawozdania_screener` przycisk „Pokaż szczegóły” → `nav.go_company(selected)` (import `from components import nav` wewnątrz funkcji, by uniknąć cykli). `render_sprawozdania_deep_dive` usuń (już nieużywany), zostaw `_render_*_tab` (używane przez `components/company/`).
- [ ] **Step 5: kalendarz_wynikow.py / insiderzy.py** — `_navigate_to_deep_dive(ticker)` zastąp wywołaniem `nav.go_company(ticker)` (ETF/UNKNOWN: zostaw ostrzeżenie); usuń ustawianie kluczy sesji.
- [ ] **Step 6: pulpit.py** — `_on_search` ustawia tylko `st.session_state["_pulpit_go"] = choice` i czyści `pulpit_search`; po selectboxie: `target = st.session_state.pop("_pulpit_go", None); if target: nav.go_company(target)`. Caption pod wyszukiwarką (free): „Przegląd spółki za darmo, pozostałe zakładki w Premium.” — zaktualizuj asercję w `tests/test_pulpit_offline.py`.
- [ ] **Step 7:** `venv/Scripts/python.exe -m pytest -q` zielone; `grep -rn "deep_dive\|pending_view\|_finanse_" views components` → tylko nazwy funkcji `_render_*` (bez stanu sesji).
- [ ] **Step 8: Commit** „Route all company drill-downs to the company card; drop per-company tabs from market pages”.

---

### Task 10: Smoke, zrzuty, dokumentacja

- [ ] **Step 1:** `tests/test_pages_smoke.py` — dopisz:
```python
@pytest.mark.parametrize("ticker", ["AAPL", "CDR.WA"])
def test_karta_renders_with_premium(ticker):
    at = AppTest.from_file(APP, default_timeout=900)
    at.session_state["premium"] = True
    at.session_state["_auth_retries"] = 3
    at.query_params["t"] = ticker
    at.switch_page("views/spolki/karta.py").run()
    assert not at.exception, f"{ticker}: {at.exception}"
```
Uruchom pełny smoke: `RUN_NETWORK=1 venv/Scripts/python.exe -m pytest tests/test_pages_smoke.py -q` (z certyfikatami Norton; ~12 min) — wszystkie zielone.
- [ ] **Step 2:** Zrzuty do akceptacji użytkownika (free i premium, 1440 i 390 px): `karta?t=AAPL`, `karta?t=PKO.WA`, `karta` (bez tickera), `spolki-sp500`… (strona S&P 500: `sp500`) — zapisz w scratchpadzie, wymień ścieżki w raporcie.
- [ ] **Step 3:** `CLAUDE.md` projektu: w „Project Structure” dodaj `data/company.py`, `components/company/`, `views/spolki/karta.py`; w „Nawigacja” zastąp opis deep dive przez `nav.go_company(ticker)` / `?t=`; w opisach F11/F13/F15 dopisz „(od 2026-11-15 w Karcie spółki)”.
- [ ] **Step 4: Commit** „Smoke tests and docs for the company card”.
- [ ] **Step 5:** Merge do `main` i push — **dopiero po wyraźnej zgodzie użytkownika** (skill `gem-dashboard-deploy`; merge commit bez stopki Co-Authored-By zgodnie ze skillem).
