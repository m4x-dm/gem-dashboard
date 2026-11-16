"""Karta spolki — logika danych (bez UI).

Czyste funkcje przyjmuja dane jako argumenty (testy offline).
Wrappery pobierajace (company_profile, dividend_history, sector_caps) na koncu pliku.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import streamlit as st

from data.financials import _fetch_info  # noqa: F401 — cache 24h, curl_cffi session; testy go podmieniaja
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
    """Yahoo `dividendYield` jest w PROCENTACH (0.44 = 0,44%) — zwraca ulamek."""
    v = _f(y)
    return np.nan if np.isnan(v) else v / 100


def dividend_summary(divs: pd.Series, price: float | None, info: dict, today: pd.Timestamp) -> dict:
    if divs is None or len(divs.dropna()) == 0:
        return {"pays": False}
    divs = divs.dropna().sort_index()
    divs.index = pd.to_datetime(divs.index).tz_localize(None) if getattr(divs.index, "tz", None) else pd.to_datetime(divs.index)
    today = pd.Timestamp(today).normalize()

    y = np.nan
    ttm = divs[divs.index > today - pd.DateOffset(years=1)].sum()
    if price is not None and np.isfinite(price) and price > 0 and ttm > 0:
        y = ttm / price
    if np.isnan(y):
        y = _f(info.get("trailingAnnualDividendYield"))   # zawsze ulamek
    if np.isnan(y):
        y = _norm_yield(info.get("dividendYield"))

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


# --- wrappery pobierajace (cache 24h) ---------------------------------------

def _sector_map(market: str) -> dict[str, str]:
    if market == "GPW":
        from data.gpw_universe import GPW_SECTOR_MAP as m
    else:
        from data.sp500_universe import SP500_SECTOR_MAP as m
    return m


def _sector_members(market: str, sector: str) -> list[str]:
    return [t for t, s in _sector_map(market).items() if s == sector]


def sector_of(ticker: str, market: str) -> str | None:
    return _sector_map(market).get(ticker)


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


def _opt(x):
    v = _f(x)
    return None if np.isnan(v) else v


@st.cache_data(ttl=86400, show_spinner=False)
def company_profile(ticker: str) -> dict:
    info = _fetch_info(ticker) or {}
    return {
        "summary": info.get("longBusinessSummary"),
        "beta": _opt(info.get("beta")),
        "low52": _opt(info.get("fiftyTwoWeekLow")),
        "high52": _opt(info.get("fiftyTwoWeekHigh")),
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


@st.cache_data(ttl=3600, show_spinner=False)
def universe_prices(universe: tuple[str, ...], period: str = "2y") -> pd.DataFrame:
    """Ceny zamkniecia calego universe jednym zapytaniem (bez fallbacku per ticker) — do rankingu momentum na karcie."""
    import yfinance as yf
    data = yf.download(" ".join(universe), period=period, auto_adjust=True, progress=False, threads=True, timeout=30)
    if data is None or data.empty:
        return pd.DataFrame()
    prices = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data[["Close"]]
    prices = prices.dropna(how="all")
    if getattr(prices.index, "tz", None) is not None:
        prices.index = prices.index.tz_localize(None)
    return prices
