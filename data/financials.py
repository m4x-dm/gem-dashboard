"""Pobieranie wskaznikow finansowych + konsensus analitykow z yfinance.

Cache 24h (financials zmieniaja sie rzadko, oszczedza Yahoo rate-limit).
Wszystkie funkcje wrapped w try/except — fail = None / empty (graceful).

Uzywane przez tab "Finanse spolki" w pages/7_sp500.py + pages/8_gpw.py.
"""

import time

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

from data.gpw_universe import GPW_BANKS


# ---------------------------------------------------------------------------
# curl_cffi session — browser TLS fingerprint impersonate.
# Yahoo Finance blokuje requests z domyslnym TLS fingerprint Python'a
# (Streamlit Cloud GCP IPs). curl_cffi impersonate="chrome" naladuje
# pelen Chrome TLS handshake — yfinance natywnie wspiera ten pattern
# przez session arg (NIE requests.Session ktore poprzednio nie dzialalo).
# ---------------------------------------------------------------------------

_yf_session = None


def _get_yf_session():
    """Lazy-init curl_cffi session z Chrome TLS impersonate.

    Fallback do None (= domyslny yfinance) gdy curl_cffi nie jest dostepny
    (np. lokalny dev bez tej biblioteki).
    """
    global _yf_session
    if _yf_session is None:
        try:
            from curl_cffi import requests as cffi_requests
            _yf_session = cffi_requests.Session(impersonate="chrome")
        except ImportError:
            _yf_session = False  # marker: tried, niedostepne
    return _yf_session if _yf_session is not False else None


# ---------------------------------------------------------------------------
# Fetch functions (cached 24h)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=86400, show_spinner=False)
def _fetch_info(ticker: str) -> dict:
    """Wspolny helper — fetch yfinance Ticker.info raz dla danego tickera.

    Uzywany przez get_ratios_snapshot + get_analyst_recos (oba potrzebuja info).
    Dzieki cache TTL 24h — 1 API call zamiast 2 per ticker.

    Strategia anti-rate-limit:
    1. curl_cffi session z impersonate="chrome" (browser TLS fingerprint)
       — Yahoo blokuje default Python TLS na Streamlit Cloud GCP IPs.
    2. 3 proby z exponential backoff (0.5s -> 1.5s -> 4.5s).
    3. Sanity check: zwroc {} gdy info bez kluczowych pol (lazy dict
       Yahoo przy rate-limit).
    """
    session = _get_yf_session()
    for attempt in range(3):
        try:
            ticker_obj = yf.Ticker(ticker, session=session) if session else yf.Ticker(ticker)
            info = ticker_obj.info
            if info and isinstance(info, dict):
                if (info.get("regularMarketPrice") is not None
                        or info.get("currentPrice") is not None
                        or info.get("trailingEps") is not None):
                    return info
        except Exception:
            pass
        if attempt < 2:
            time.sleep(0.5 * (3 ** attempt))
    return {}


@st.cache_data(ttl=86400, show_spinner=False)
def get_ratios_snapshot(ticker: str) -> dict:
    """Pobiera 12 kluczowych wskaznikow z yfinance Ticker.info.

    Zwraca dict z kluczami: pe, fwd_pe, ev_ebitda, ebitda, roe, roa,
    profit_margin, gross_margin, fcf, debt_to_equity, price_to_book,
    dividend_yield, market_cap, current_price, name.

    Brakujace pola = None. Pusty dict gdy ticker nieznany / API fail.
    """
    info = _fetch_info(ticker)
    if not info:
        return {}

    # Sanity check: ticker nieznany jesli brak nawet ceny / EPS
    if info.get("regularMarketPrice") is None and info.get("currentPrice") is None \
            and info.get("trailingEps") is None:
        return {}

    return {
        "pe": info.get("trailingPE"),
        "fwd_pe": info.get("forwardPE"),
        "ev_ebitda": info.get("enterpriseToEbitda"),
        "ebitda": info.get("ebitda"),
        "roe": info.get("returnOnEquity"),
        "roa": info.get("returnOnAssets"),
        "profit_margin": info.get("profitMargins"),
        "gross_margin": info.get("grossMargins"),
        "fcf": info.get("freeCashflow"),
        "debt_to_equity": info.get("debtToEquity"),
        "price_to_book": info.get("priceToBook"),
        "dividend_yield": info.get("dividendYield"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "market_cap": info.get("marketCap"),
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "name": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "currency": info.get("currency"),
    }


@st.cache_data(ttl=86400, show_spinner=False)
def get_forward_consensus(ticker: str) -> pd.DataFrame | None:
    """Forward konsensus EPS analitykow.

    Returns DF z kolumnami: avg, low, high, num_analysts, growth.
    Index: period label ("Q0", "Q+1", "FY", "FY+1").

    None gdy brak danych lub 0 analitykow.
    """
    try:
        df = yf.Ticker(ticker).earnings_estimate
    except Exception:
        return None

    if df is None or df.empty:
        return None

    # yfinance period index: "0q", "+1q", "0y", "+1y"
    period_map = {"0q": "Q0", "+1q": "Q+1", "0y": "FY", "+1y": "FY+1"}
    out = df.copy()
    out.index = [period_map.get(str(p), str(p)) for p in out.index]

    # Standardize column names
    rename = {
        "avg": "avg",
        "low": "low",
        "high": "high",
        "numberOfAnalysts": "num_analysts",
        "growth": "growth",
        "yearAgoEps": "year_ago_eps",
    }
    out = out.rename(columns={c: rename[c] for c in out.columns if c in rename})

    # Drop rows z 0 analitykow (czesto 0y/+1y dla mniej znanych spolek)
    if "num_analysts" in out.columns:
        out = out[out["num_analysts"].fillna(0) > 0]

    if out.empty:
        return None

    return out


@st.cache_data(ttl=86400, show_spinner=False)
def get_earnings_history(ticker: str, n_quarters: int = 8) -> pd.DataFrame | None:
    """Historia earnings: actual vs estimate dla ostatnich N kwartalow.

    Returns DF z kolumnami: eps_estimate, eps_actual, surprise_pct.
    Index: quarter label (np. "2025Q3").

    None gdy brak danych.
    """
    try:
        df = yf.Ticker(ticker).earnings_history
    except Exception:
        return None

    if df is None or df.empty:
        return None

    out = df.copy()

    # yfinance kolumny: epsEstimate, epsActual, epsDifference, surprisePercent, quarter
    rename = {
        "epsEstimate": "eps_estimate",
        "epsActual": "eps_actual",
        "surprisePercent": "surprise_pct",
    }
    out = out.rename(columns={c: rename[c] for c in out.columns if c in rename})

    # Jesli brak surprise_pct - liczymy lokalnie
    if "surprise_pct" not in out.columns and \
            "eps_estimate" in out.columns and "eps_actual" in out.columns:
        est = out["eps_estimate"].replace(0, np.nan)
        out["surprise_pct"] = (out["eps_actual"] - out["eps_estimate"]) / est.abs() * 100

    # Zostaw tylko interesujace kolumny + ostatnie N kwartalow
    keep = [c for c in ["eps_estimate", "eps_actual", "surprise_pct"] if c in out.columns]
    if not keep:
        return None
    out = out[keep].dropna(how="all").tail(n_quarters)

    if out.empty:
        return None

    return out


@st.cache_data(ttl=86400, show_spinner=False)
def get_analyst_recos(ticker: str) -> dict:
    """Rekomendacje analitykow + target prices.

    Zwraca dict z kluczami: target_mean, target_median, target_high,
    target_low, recommendation_key, num_analysts, current_price, upside_pct,
    currency.

    Pusty dict gdy brak analitykow / API fail.
    """
    info = _fetch_info(ticker)
    if not info:
        return {}

    num_analysts = info.get("numberOfAnalystOpinions") or 0
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    target_mean = info.get("targetMeanPrice")

    # Brak analitykow -> nic do pokazania
    if num_analysts == 0 and target_mean is None:
        return {}

    upside_pct = None
    if target_mean is not None and current_price and current_price > 0:
        upside_pct = (target_mean / current_price - 1) * 100

    return {
        "target_mean": target_mean,
        "target_median": info.get("targetMedianPrice"),
        "target_high": info.get("targetHighPrice"),
        "target_low": info.get("targetLowPrice"),
        "recommendation_key": info.get("recommendationKey"),
        "num_analysts": num_analysts,
        "current_price": current_price,
        "upside_pct": upside_pct,
        "currency": info.get("currency"),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_bank(ticker: str) -> bool:
    """Sprawdza czy ticker to bank GPW (lookup w GPW_BANKS set).

    Banki: ukryj EBITDA / EV-EBITDA / FCF (nie ma sensu dla bankow).
    """
    return ticker in GPW_BANKS


def _quarter_label(date) -> str:
    """Konwertuje datę raportu na label "QX'YY".

    "2026-03-31" -> "Q1'26", "2025-12-31" -> "Q4'25".
    NaT/None -> "".
    """
    if date is None or pd.isna(date):
        return ""
    ts = pd.Timestamp(date)
    q = (ts.month - 1) // 3 + 1
    yy = ts.year % 100
    return f"Q{q}'{yy:02d}"


def _compute_beat_streak(df: pd.DataFrame) -> int:
    """Liczy ile kolejnych OSTATNICH kwartalow EPS pobil estimate.

    df: DataFrame z kolumnami eps_estimate, eps_actual,
        posortowany rosnaco po dacie (najnowszy na dole).
    Returns: int 0-N (max dlugosc df).
    """
    if df is None or df.empty:
        return 0
    if "eps_estimate" not in df.columns or "eps_actual" not in df.columns:
        return 0
    streak = 0
    # Iterujemy od najnowszego (dol DF) w gore
    for _, row in df.iloc[::-1].iterrows():
        est = row["eps_estimate"]
        act = row["eps_actual"]
        if pd.isna(est) or pd.isna(act):
            break
        if act > est:
            streak += 1
        else:
            break
    return streak


def format_currency(value: float | None, ticker: str) -> str:
    """Formatuje wartosc waluty wedlug suffix tickera.

    .WA suffix -> PLN, inaczej USD. None -> "—".
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "—"
    if isinstance(value, float) and np.isinf(value):
        return "—"
    is_pln = ticker.endswith(".WA")
    symbol = "zl" if is_pln else "$"
    return f"{symbol}{value:,.2f}"


def format_large_number(value: float | None) -> str:
    """Skrocone formatowanie duzych liczb: $4.4T / 160B / 101M / 25K.

    None / inf / NaN -> "—".
    """
    if value is None:
        return "—"
    try:
        if np.isnan(value) or np.isinf(value):
            return "—"
    except (TypeError, ValueError):
        return "—"

    abs_v = abs(value)
    if abs_v >= 1e12:
        return f"{value / 1e12:.2f}T"
    if abs_v >= 1e9:
        return f"{value / 1e9:.2f}B"
    if abs_v >= 1e6:
        return f"{value / 1e6:.1f}M"
    if abs_v >= 1e3:
        return f"{value / 1e3:.1f}K"
    return f"{value:.2f}"


# ---------------------------------------------------------------------------
# Bulk fetch dla tab Screening (pages 7_sp500 + 8_gpw)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=86400, show_spinner="Pobieram dane fundamentalne universe...")
def bulk_fetch_universe(tickers_tuple: tuple[str, ...]) -> dict[str, dict]:
    """Bulk fetch danych fundamentalnych dla calego subset universe.

    Reuses _fetch_info (cache TTL 24h) — pierwsze wywolanie 30-60s dla 100
    tickerów, kolejne wywolania w 24h instant (cache hit per ticker).

    Args:
        tickers_tuple: tuple zamiast list — zeby cache key byl hashable.
            UWAGA: NIE prefix '_' — Streamlit cache_data ignoruje argumenty
            z '_' prefix (cross-call collision: SP500 cache zwracany dla GPW!).

    Returns:
        dict[ticker, {info dict}] — brak rekordu gdy ticker zwrocil 404/timeout.
    """
    out: dict[str, dict] = {}
    tickers = list(tickers_tuple)
    for t in tickers:
        info = _fetch_info(t)  # cached per ticker — drugi run instant
        if not info:
            continue
        # Sanity check: yfinance zwraca dict nawet dla nieistniejacych tickerów
        # (z 404 w HTTP error). Skip jesli brak kluczowych pol.
        if (info.get("regularMarketPrice") is None
                and info.get("currentPrice") is None
                and info.get("trailingEps") is None):
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
    """Konwersja bulk_fetch_universe wynik -> DataFrame screen-ready.

    Dodaje 2 pochodne kolumny:
        - upside_pct = (target_mean / current_price - 1) * 100
        - is_buy = recommendation_key in {"strong_buy", "buy", "outperform"}

    Returns pusty DataFrame gdy bulk = {}.
    """
    if not bulk:
        return pd.DataFrame()
    df = pd.DataFrame(bulk).T  # ticker = index
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
