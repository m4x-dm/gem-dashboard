"""Analiza techniczna pozycji z portfela: wsparcia/opory, SMA50/200, 52 tyg., RSI.

Spec: docs/superpowers/specs/2026-11-20-moj-portfel-technika-design.md
Czyste funkcje na DataFrame z kolumnami High / Low / Close (indeks: dni sesyjne).
Zdarzenia z ostatnich EVENT_SESSIONS sesji zwracane jako Alert (data/portfolio/alerts.py),
zeby panel "Co sie dzieje" sortowal je razem z wynikami i insiderami.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from data.momentum import calc_rsi
from data.portfolio.alerts import Alert

LEVEL_WINDOW = 126      # ~6 miesiecy sesji do wyznaczania poziomow
PIVOT_K = 5             # szczyt/dolek = ekstremum w oknie +-5 sesji
CLUSTER_PCT = 0.015     # punkty blizej niz 1,5% -> ten sam poziom
MIN_TOUCHES = 2         # poziom = co najmniej 2 testy
BREAK_PCT = 0.01        # przebicie = zamkniecie dalej niz 1% za poziomem
EVENT_SESSIONS = 10     # okno zdarzen
RSI_HI, RSI_LO = 70.0, 30.0
YEAR = 252


def _pivots(values: np.ndarray, k: int, high: bool) -> list[float]:
    """Ekstrema lokalne: scisle wieksze (mniejsze) od k sesji przed i >= (<=) k sesji po."""
    out = []
    for i in range(k, len(values) - k):
        v, left, right = values[i], values[i - k:i], values[i + 1:i + k + 1]
        if np.isnan(v):
            continue
        if high and v > np.nanmax(left) and v >= np.nanmax(right):
            out.append(float(v))
        if not high and v < np.nanmin(left) and v <= np.nanmin(right):
            out.append(float(v))
    return out


def levels(high: pd.Series, low: pd.Series, k: int = PIVOT_K,
           window: int = LEVEL_WINDOW) -> list[tuple[float, int]]:
    """Poziomy wsparcia/oporu z lokalnych szczytow i dolkow: [(cena, liczba testow)], rosnaco."""
    h = high.astype(float).to_numpy()[-window:]
    lo = low.astype(float).to_numpy()[-window:]
    pts = sorted(_pivots(h, k, True) + _pivots(lo, k, False))
    groups: list[list[float]] = []
    for p in pts:
        if groups and p <= np.mean(groups[-1]) * (1 + CLUSTER_PCT):
            groups[-1].append(p)
        else:
            groups.append([p])
    return [(float(np.mean(g)), len(g)) for g in groups if len(g) >= MIN_TOUCHES]


def _clean(ohlc: pd.DataFrame) -> pd.DataFrame:
    return ohlc[["High", "Low", "Close"]].astype(float).dropna(subset=["Close"])


def snapshot_row(ohlc: pd.DataFrame) -> dict:
    """Stan techniczny na dzis: kurs, najblizszy opor/wsparcie, SMA50/200, RSI, odleglosc od 52-tyg. max."""
    d = _clean(ohlc)
    nan = float("nan")
    if d.empty:
        return {"price": nan, "res": None, "sup": None, "sma50": nan, "sma200": nan, "rsi": nan,
                "from_high52": nan}
    c = d["Close"]
    price = float(c.iloc[-1])
    lv = [p for p, _ in levels(d["High"], d["Low"])]
    above, below = [p for p in lv if p > price], [p for p in lv if p < price]
    rsi = calc_rsi(c).iloc[-1] if len(c) > 15 else nan
    return {
        "price": price,
        "res": min(above) if above else None,
        "sup": max(below) if below else None,
        "sma50": float(c.tail(50).mean()) if len(c) >= 50 else nan,
        "sma200": float(c.tail(200).mean()) if len(c) >= 200 else nan,
        "rsi": float(rsi) if rsi == rsi else nan,
        "from_high52": price / float(c.tail(YEAR).max()) - 1 if len(c) >= YEAR else nan,
    }


def last_cross(a: pd.Series, b, n: int) -> tuple[pd.Timestamp, str] | None:
    """Ostatnie przeciecie a z b w ostatnich n sesjach: (data, 'up' | 'down') albo None."""
    b = pd.Series(b, index=a.index) if np.isscalar(b) else b
    diff = (a - b).dropna().tail(n + 1)
    hit = None
    vals, idx = diff.to_numpy(), diff.index
    for i in range(1, len(vals)):
        if vals[i - 1] <= 0 < vals[i]:
            hit = (idx[i], "up")
        elif vals[i - 1] >= 0 > vals[i]:
            hit = (idx[i], "down")
    return hit


def events(ticker: str, ohlc: pd.DataFrame, ccy: str = "") -> list[Alert]:
    """Zdarzenia techniczne z ostatnich EVENT_SESSIONS sesji, najnowsze jedno na rodzaj."""
    d = _clean(ohlc)
    out: list[Alert] = []
    n = EVENT_SESSIONS
    if len(d) < n + 2 * PIVOT_K + 2:
        return out
    c = d["Close"]

    # Przebicie poziomu: poziomy z danych SPRZED okna (samo wybicie nie tworzy poziomu).
    lv = [p for p, _ in levels(d["High"].iloc[:-n], d["Low"].iloc[:-n])]
    last = None
    win = c.iloc[-(n + 1):]
    for i in range(1, len(win)):
        p0, p1, day = win.iloc[i - 1], win.iloc[i], win.index[i]
        for L in lv:
            if p0 <= L * (1 + BREAK_PCT) < p1:
                last = (day, "up", L, p1)
            elif p0 >= L * (1 - BREAK_PCT) > p1:
                last = (day, "down", L, p1)
    if last:
        day, way, L, p1 = last
        out.append(Alert(day, ticker, "tech_level", "pos" if way == "up" else "neg",
                         "przebity opór {level} ({pct})" if way == "up" else "przebite wsparcie {level} ({pct})",
                         {"level": L, "pct": p1 / L - 1, "ccy": ccy}))

    if len(c) >= 200:
        sma50, sma200 = c.rolling(50).mean(), c.rolling(200).mean()
        x = last_cross(sma50, sma200, n)
        if x:
            out.append(Alert(x[0], ticker, "tech_cross", "pos" if x[1] == "up" else "neg",
                             "złoty krzyż (SMA50 > SMA200)" if x[1] == "up" else "śmiertelny krzyż (SMA50 < SMA200)",
                             {}))
        x = last_cross(c, sma200, n)
        if x:
            out.append(Alert(x[0], ticker, "tech_sma200", "pos" if x[1] == "up" else "neg",
                             "kurs powyżej SMA200" if x[1] == "up" else "kurs poniżej SMA200", {}))

    if len(c) >= YEAR:
        hi, lo = c.rolling(YEAR).max(), c.rolling(YEAR).min()
        tail = c.tail(n)
        new_hi = tail[tail >= hi.tail(n)]
        new_lo = tail[tail <= lo.tail(n)]
        if not new_hi.empty or not new_lo.empty:
            d_hi = new_hi.index[-1] if not new_hi.empty else None
            d_lo = new_lo.index[-1] if not new_lo.empty else None
            if d_lo is None or (d_hi is not None and d_hi >= d_lo):
                out.append(Alert(d_hi, ticker, "tech_52w", "pos", "nowe 52-tyg. maksimum", {}))
            else:
                out.append(Alert(d_lo, ticker, "tech_52w", "neg", "nowe 52-tyg. minimum", {}))

    rsi = calc_rsi(c)
    hits = []                                   # (data, strefa): wejscie > 70 albo < 30
    up = last_cross(rsi, RSI_HI, n)
    if up and up[1] == "up":
        hits.append((up[0], "hi"))
    down = last_cross(rsi, RSI_LO, n)
    if down and down[1] == "down":
        hits.append((down[0], "lo"))
    if hits:
        dt, zone = max(hits, key=lambda h: h[0])
        out.append(Alert(dt, ticker, "tech_rsi", "neutral",
                         "RSI {rsi} — wykupienie" if zone == "hi" else "RSI {rsi} — wyprzedanie",
                         {"rsi": float(rsi.loc[dt]), "zone": zone}))
    return out


def fetch_ohlc(tickers: tuple[str, ...], period: str = "2y") -> dict[str, pd.DataFrame]:
    """Kursy High/Low/Close dla tickerow Yahoo — JEDNO yf.download (dziala na Streamlit Cloud).

    Blad sieci / brak danych tickera -> brak klucza w wyniku.
    """
    if not tickers:
        return {}
    try:
        import yfinance as yf
        data = yf.download(" ".join(tickers), period=period, auto_adjust=True, progress=False,
                           threads=True, timeout=30, group_by="column")
    except Exception:
        return {}
    if data is None or data.empty:
        return {}
    out = {}
    for t in tickers:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                df = pd.DataFrame({k: data[k][t] for k in ("High", "Low", "Close")})
            else:
                df = data[["High", "Low", "Close"]].copy()
        except KeyError:
            continue
        idx = pd.DatetimeIndex(df.index)
        if idx.tz is not None:
            idx = idx.tz_localize(None)
        df.index = idx.normalize()
        df = df.dropna(subset=["Close"])
        if not df.empty:
            out[t] = df
    return out
