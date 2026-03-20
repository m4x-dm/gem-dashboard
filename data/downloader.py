"""Pobieranie danych z yfinance z cache Streamlit."""

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


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

        # Filtruj wg period (przyblizony mapping)
        period_days = {
            "1mo": 30, "2mo": 60, "3mo": 90, "6mo": 180, "1y": 365,
            "2y": 730, "3y": 1095, "5y": 1825, "7y": 2555, "10y": 3650,
            "15y": 5475, "20y": 7300, "max": 999999,
        }
        days = period_days.get(period, 5475)
        if days < 999999:
            cutoff = pd.Timestamp.now() - timedelta(days=days)
            df = df[df.index >= cutoff]

        return df["Close"].dropna()
    except (KeyError, ValueError) as e:
        import streamlit as st
        st.warning(f"Blad pobierania danych ze Stooq ({symbol}): {e}")
        return None
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def download_single(ticker: str, period: str = "15y") -> pd.Series | None:
    """Pobiera cenę zamknięcia dla jednego tickera."""
    try:
        data = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        if data.empty:
            return None
        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        return close.dropna()
    except Exception:
        return None
