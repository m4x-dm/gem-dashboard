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
