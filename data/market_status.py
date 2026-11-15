"""Dane Pulpitu — czyste funkcje (testowalne offline) + cienkie wrappery pobierajace."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from data.gpw_universe import GPW_CATEGORIES

# Kafelki "Wskazniki rynku": (ticker yfinance, etykieta)
MARKET_TILES = [
    ("^VIX", "VIX"),
    ("^GSPC", "S&P 500"),
    ("ETFBW20TR.WA", "WIG20 (ETF Beta)"),
    ("PLN=X", "USD/PLN"),
    ("GC=F", "Złoto"),
    ("BTC-USD", "Bitcoin"),
]

REGIME_TICKERS = {"SPY": "S&P 500", "^TNX": "Obligacje (10Y yield)", "GC=F": "Zloto",
                  "DX-Y.NYB": "Dolar (DXY)", "CL=F": "Ropa WTI"}

# Waga i kierunek: +1 = wzrost 3M oznacza risk-on, -1 = wzrost oznacza risk-off
_REGIME_RULES = {"SPY": (2, +1), "^TNX": (1, +1), "GC=F": (1, -1), "DX-Y.NYB": (1, -1), "CL=F": (1, +1)}

MEGA_CAPS_US = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AVGO", "TSLA", "JPM", "LLY", "V", "WMT"]


def compute_regime(series_by_ticker: dict[str, pd.Series]) -> dict:
    """Risk-On/Off z momentum 3M (63 sesje) — logika 1:1 z dawnego Podsumowania."""
    on = off = 0
    for ticker, s in series_by_ticker.items():
        rule = _REGIME_RULES.get(ticker)
        if rule is None or s is None or len(s) <= 63:
            continue
        weight, direction = rule
        mom = s.iloc[-1] / s.iloc[-63] - 1
        if not np.isfinite(mom):
            continue
        if (mom > 0) == (direction > 0):
            on += weight
        else:
            off += weight
    total = on + off
    score = on / total * 100 if total > 0 else 50.0
    if score >= 65:
        label, desc = "Risk-On", "Srodowisko sprzyjajace akcjom"
    elif score <= 35:
        label, desc = "Risk-Off", "Awersja do ryzyka — rozwazyc obligacje"
    else:
        label, desc = "Neutralny", "Mieszane sygnaly miedzy klasami aktywow"
    return {"label": label, "desc": desc, "score": float(score)}


def signal_since(signals: list[tuple[pd.Timestamp, str]]) -> tuple[pd.Timestamp, str] | None:
    """Ostatnia zmiana sygnalu z backtest_gem(...)['signals']."""
    return tuple(signals[-1]) if signals else None


def next_rebalance_date(today: pd.Timestamp) -> pd.Timestamp:
    """Pierwszy dzien roboczy (pon–pt) nastepnego miesiaca."""
    first = (pd.Timestamp(today).normalize() + pd.offsets.MonthBegin(1))
    while first.weekday() >= 5:
        first += pd.Timedelta(days=1)
    return first


def daily_change(prices: pd.DataFrame) -> pd.Series:
    """Zmiana ostatniej sesji per kolumna; pomija braki i inf."""
    out = {}
    for col in prices.columns:
        s = prices[col].dropna()
        if len(s) < 2:
            continue
        chg = s.iloc[-1] / s.iloc[-2] - 1
        if np.isfinite(chg):
            out[col] = float(chg)
    return pd.Series(out, dtype=float)


def top_movers(changes: pd.Series, n: int = 5) -> tuple[pd.Series, pd.Series]:
    s = changes.dropna()
    return s.sort_values(ascending=False).head(n), s.sort_values().head(n)


def pulpit_earnings_tickers(watchlist: set[str]) -> list[str]:
    """Watchlista (posortowana) + mega-capy USA + WIG20, bez duplikatow."""
    ordered = sorted(watchlist) + MEGA_CAPS_US + list(GPW_CATEGORIES["WIG20"].keys())
    seen, out = set(), []
    for t in ordered:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def market_movers(universe: tuple[str, ...]) -> pd.Series:
    """Zmiana dzienna dla calego universe — cache 1 h wspolny dla wszystkich uzytkownikow."""
    from data.downloader import download_prices
    prices = download_prices(list(universe), period="5d")
    return daily_change(prices)
