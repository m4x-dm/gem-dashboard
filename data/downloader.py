"""Pobieranie danych z yfinance z fallbackiem na stooq.com i CoinGecko."""

import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta


# --- Period → days mapping (reused across functions) ---
PERIOD_DAYS = {
    "1mo": 30, "2mo": 60, "3mo": 90, "6mo": 180, "1y": 365,
    "2y": 730, "3y": 1095, "5y": 1825, "7y": 2555, "10y": 3650,
    "15y": 5475, "20y": 7300, "max": 999999,
}


def _track_source(ticker: str, source: str):
    """Zapisuje zrodlo danych w session_state."""
    if "_data_sources" not in st.session_state:
        st.session_state["_data_sources"] = {}
    st.session_state["_data_sources"][ticker] = source


def _track_failure(ticker: str):
    """Zapisuje ticker, ktorego nie udalo sie pobrac."""
    if "_data_failures" not in st.session_state:
        st.session_state["_data_failures"] = []
    if ticker not in st.session_state["_data_failures"]:
        st.session_state["_data_failures"].append(ticker)


def _yfinance_single(ticker: str, period: str = "15y") -> pd.Series | None:
    """Pobiera cene zamkniecia z yfinance."""
    try:
        data = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        if data.empty:
            return None
        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        s = close.dropna()
        return s if len(s) > 0 else None
    except Exception:
        return None


def _stooq_fallback(ticker: str, period: str = "15y") -> pd.Series | None:
    """Fallback na stooq.com — dziala dla US/ETF (suffix .us) i GPW."""
    try:
        # Okresl symbol stooq
        if ticker in STOOQ_TICKERS:
            sym = STOOQ_TICKERS[ticker]
        elif ticker.endswith(".WA"):
            sym = ticker.replace(".WA", "").lower()
        elif not ticker.startswith("^") and "-" not in ticker and "=" not in ticker:
            sym = f"{ticker.lower()}.us"
        else:
            return None

        url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
        df = pd.read_csv(url)
        if df.empty or "Close" not in df.columns or "Date" not in df.columns:
            return None
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"]).set_index("Date").sort_index()

        if df.empty:
            return None

        days = PERIOD_DAYS.get(period, 5475)
        if days < 999999:
            cutoff = pd.Timestamp.now() - timedelta(days=days)
            df = df[df.index >= cutoff]

        s = df["Close"].dropna()
        return s if len(s) > 0 else None
    except Exception:
        return None


def _coingecko_fallback(ticker: str, period: str = "15y") -> pd.Series | None:
    """Fallback na CoinGecko free API dla kryptowalut."""
    if not ticker.endswith("-USD"):
        return None
    try:
        from data.crypto_universe import COINGECKO_IDS
    except ImportError:
        return None

    coin_id = COINGECKO_IDS.get(ticker)
    if not coin_id:
        return None

    days = min(PERIOD_DAYS.get(period, 5475), 2000)  # CoinGecko max ~2000 dni
    if days >= 999999:
        days = 2000

    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        resp = requests.get(url, params={"vs_currency": "usd", "days": days},
                            timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        prices_raw = data.get("prices", [])
        if not prices_raw:
            return None

        df = pd.DataFrame(prices_raw, columns=["timestamp", "price"])
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms").dt.normalize()
        df = df.drop_duplicates(subset=["date"], keep="last").set_index("date").sort_index()
        s = df["price"].dropna()
        return s if len(s) > 0 else None
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner="Pobieram dane rynkowe...")
def download_prices(tickers: list[str], period: str = "15y") -> pd.DataFrame:
    """Pobiera ceny zamknięcia dla listy tickerów. Zwraca DataFrame z kolumnami = tickery."""
    tickers_str = " ".join(tickers)
    data = yf.download(tickers_str, period=period, auto_adjust=True, progress=False)

    if isinstance(data.columns, pd.MultiIndex):
        prices = data["Close"]
    else:
        # Pojedynczy ticker
        prices = data[["Close"]]
        prices.columns = [tickers[0]]

    prices = prices.dropna(how="all")

    # Track sources for tickers that have data
    for t in tickers:
        if t in prices.columns and prices[t].dropna().shape[0] > 0:
            _track_source(t, "yfinance")

    # Fallback for missing tickers
    missing = [t for t in tickers if t not in prices.columns or prices[t].dropna().shape[0] == 0]
    for t in missing:
        s = _stooq_fallback(t, period)
        if s is not None:
            prices[t] = s
            _track_source(t, "stooq")
            continue
        s = _coingecko_fallback(t, period)
        if s is not None:
            prices[t] = s
            _track_source(t, "coingecko")
            continue
        _track_failure(t)

    return prices


@st.cache_data(ttl=21600, show_spinner="Pobieram stopę wolną od ryzyka...")
def get_risk_free_rate() -> float | None:
    """Pobiera aktualną stopę wolną od ryzyka (13-week T-bill, ^IRX). Zwraca % annualized."""
    try:
        data = yf.download("^IRX", period="5d", auto_adjust=True, progress=False)
        if data.empty:
            return None
        last = data["Close"].dropna().iloc[-1]
        if isinstance(last, pd.Series):
            last = last.iloc[0]
        return float(last)
    except Exception:
        return None


STOOQ_TICKERS = {"WIG20": "wig20", "mWIG40": "mwig40", "sWIG80": "swig80"}


@st.cache_data(ttl=3600, show_spinner="Pobieram dane ze Stooq...")
def download_stooq(symbol: str, period: str = "15y") -> pd.Series | None:
    """Pobiera cenę zamknięcia indeksu GPW ze stooq.com. Zwraca Series z DatetimeIndex."""
    stooq_sym = STOOQ_TICKERS.get(symbol)
    if not stooq_sym:
        return None
    try:
        url = f"https://stooq.com/q/d/l/?s={stooq_sym}&i=d"
        df = pd.read_csv(url)
        if df.empty or "Close" not in df.columns or "Date" not in df.columns:
            return None
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"]).set_index("Date").sort_index()

        if df.empty:
            return None

        days = PERIOD_DAYS.get(period, 5475)
        if days < 999999:
            cutoff = pd.Timestamp.now() - timedelta(days=days)
            df = df[df.index >= cutoff]

        return df["Close"].dropna()
    except (KeyError, ValueError) as e:
        st.warning(f"Blad pobierania danych ze Stooq ({symbol}): {e}")
        return None
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def download_single(ticker: str, period: str = "15y") -> pd.Series | None:
    """Pobiera cenę zamknięcia z lancuchem fallback: yfinance → stooq → CoinGecko."""
    # 1. yfinance
    s = _yfinance_single(ticker, period)
    if s is not None:
        _track_source(ticker, "yfinance")
        return s

    # 2. stooq fallback
    s = _stooq_fallback(ticker, period)
    if s is not None:
        _track_source(ticker, "stooq")
        return s

    # 3. CoinGecko fallback
    s = _coingecko_fallback(ticker, period)
    if s is not None:
        _track_source(ticker, "coingecko")
        return s

    _track_failure(ticker)
    return None
