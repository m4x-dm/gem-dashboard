"""Pobieranie danych z yfinance z fallbackiem na stooq.com i CoinGecko."""

import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from io import StringIO
from pathlib import Path
from datetime import datetime, timedelta

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
_CACHE_DIR = Path(__file__).parent / "cache"


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
    """Pobiera cene zamkniecia z yfinance.

    UWAGA (2026-04): Yahoo aggressively rate-limituje single-ticker calls.
    yf.download(TICKER, ...) oraz yf.Ticker(TICKER).history() zwracaja puste dane.
    Workaround: zawsze wywoluj bulk mode z companion tickerem (SPY/QQQ) i wyciagaj
    tylko interesujaca kolumne.
    """
    try:
        companion = "SPY" if ticker != "SPY" else "QQQ"
        data = yf.download(f"{ticker} {companion}", period=period,
                           auto_adjust=True, progress=False, group_by="ticker")
        if data.empty:
            return None
        if isinstance(data.columns, pd.MultiIndex):
            level0 = data.columns.get_level_values(0)
            if ticker in level0:
                close = data[ticker]["Close"]
            elif "Close" in level0 and ticker in data["Close"].columns:
                close = data["Close"][ticker]
            else:
                return None
        else:
            close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        s = close.dropna()
        if hasattr(s.index, "tz") and s.index.tz is not None:
            s.index = s.index.tz_localize(None)
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
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text))
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
                            headers=_HEADERS, timeout=10)
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

    # Normalize timezone — yfinance returns tz-aware, stooq/CoinGecko tz-naive
    if hasattr(prices.index, "tz") and prices.index.tz is not None:
        prices.index = prices.index.tz_localize(None)

    # Track sources for tickers that have data
    for t in tickers:
        if t in prices.columns and prices[t].dropna().shape[0] > 0:
            _track_source(t, "yfinance")

    # Fallback for missing tickers
    missing = [t for t in tickers if t not in prices.columns or prices[t].dropna().shape[0] == 0]
    for t in missing:
        # 1. Retry yfinance individually (bulk download sometimes fails for some tickers)
        s = _yfinance_single(t, period)
        if s is not None:
            prices[t] = s
            _track_source(t, "yfinance")
            continue
        # 2. stooq fallback
        s = _stooq_fallback(t, period)
        if s is not None:
            prices[t] = s
            _track_source(t, "stooq")
            continue
        # 3. CoinGecko fallback
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

# Zrodlo LIVE dla indeksow GPW: ETF-y Beta notowane na GPW, ciagniete przez
# yfinance. Powod: stooq.com i stooq.pl od 2026-08 oddaja blokade HTML zamiast
# CSV, a data/cache/*.csv zamarzly na 2026-04-16 (cicha degradacja).
#
# ETF-y sa TOTAL RETURN (z dywidendami), tak samo jak ceny spolek pobierane
# z auto_adjust=True. Wczesniejszy benchmark byl price index, wiec systematycznie
# zawyzal przewage strategii o ok. 2,2-2,6 p.p. rocznie.
#
# Korelacja dziennych zwrotow z odpowiednim indeksem (pomiar 2026-08-31):
#   ETFBW20TR.WA 0,922 (0,993 na ostatnich 2 latach)  historia od 2019-01-07
#   ETFBM40TR.WA 0,960                                 historia od 2019-09-05
#   ETFBS80TR.WA 0,913                                 historia od 2021-12-14
GPW_INDEX_ETF = {
    "WIG20": "ETFBW20TR.WA",
    "mWIG40": "ETFBM40TR.WA",
    "sWIG80": "ETFBS80TR.WA",
}

# Po ilu dniach bez nowej sesji benchmark uznajemy za nieswiezy.
BENCHMARK_MAX_AGE_DAYS = 14


def _clean_index_series(series: pd.Series | None) -> pd.Series | None:
    """Sortuje po dacie, usuwa NaN i duplikaty. None dla pustej serii."""
    if series is None or len(series) == 0:
        return None
    out = pd.Series(series).dropna()
    if out.empty:
        return None
    out.index = pd.to_datetime(out.index)
    if getattr(out.index, "tz", None) is not None:
        out.index = out.index.tz_localize(None)
    out = out[~out.index.duplicated(keep="last")].sort_index()
    return out if len(out) else None


def splice_series(hist: pd.Series | None,
                  live: pd.Series | None) -> pd.Series | None:
    """Skleja historie z cache z seria live (ETF) na wspolnej dacie - chain-linking.

    ETF-y siegaja 2019, a symulacje potrzebuja wczesniejszej historii. Czesc
    live jest przeskalowana wspolczynnikiem tak, zeby na dacie styku zgadzala
    sie z historia - dzieki temu nie ma skoku, a zwroty po styku sa dokladnie
    takie jak w oryginalnej serii live.

    Zwraca live bez zmian, gdy nie ma czego skleic (brak historii, brak
    wspolnych dat, albo live siega dalej wstecz niz historia).
    """
    hist = _clean_index_series(hist)
    live = _clean_index_series(live)

    if hist is None and live is None:
        return None
    if live is None:
        return hist
    if hist is None:
        return live
    if live.index[0] <= hist.index[0]:
        return live

    common = hist.index.intersection(live.index)
    if len(common) == 0:
        return live

    join = None
    for candidate in common:
        value = float(live.loc[candidate])
        if value != 0.0 and pd.notna(value):
            join = candidate
            break
    if join is None:
        return live

    scale = float(hist.loc[join]) / float(live.loc[join])
    tail = live.loc[join:].iloc[1:] * scale
    out = pd.concat([hist.loc[:join], tail])
    return _clean_index_series(out)


def benchmark_status(series: pd.Series | None,
                     max_age_days: int = BENCHMARK_MAX_AGE_DAYS) -> dict:
    """Sprawdza, czy benchmark jest swiezy.

    Cicha degradacja jest gorsza od braku danych: plaska linia z zamrozonego
    cache wyglada jak prawdziwy benchmark. UI ma na czym oprzec ostrzezenie.
    """
    series = _clean_index_series(series)
    if series is None:
        return {"stale": True, "last_date": None, "age_days": None}
    last = pd.Timestamp(series.index[-1]).normalize()
    age = int((pd.Timestamp.now().normalize() - last).days)
    return {
        "stale": age > max_age_days,
        "last_date": last.date().isoformat(),
        "age_days": age,
    }


def _load_stooq_csv(stooq_sym: str, period: str) -> pd.Series | None:
    """Laduje dane indeksu GPW z lokalnego CSV cache (fallback gdy stooq.com niedostepny)."""
    csv_path = _CACHE_DIR / f"{stooq_sym}.csv"
    if not csv_path.exists():
        return None
    try:
        df = pd.read_csv(csv_path)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"]).set_index("Date").sort_index()
        if df.empty:
            return None
        days = PERIOD_DAYS.get(period, 5475)
        if days < 999999:
            cutoff = pd.Timestamp.now() - timedelta(days=days)
            df = df[df.index >= cutoff]
        result = df["Close"].dropna()
        return result if len(result) > 0 else None
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner="Pobieram benchmark GPW...")
def download_gpw_index(symbol: str, period: str = "15y") -> pd.Series | None:
    """Pobiera benchmark indeksu GPW: ETF przez yfinance + historia z cache.

    Kolejnosc: ETF Beta (live, total return) sklejony z lokalnym CSV dla
    okresu sprzed startu ETF-a. Gdy ETF-a nie ma, zostaje sam cache - wtedy
    dane sa nieswieze i _track_source oznacza je sufiksem "-stale".

    stooq.com zostal usuniety z lancucha: od 2026-08 oddaje blokade HTML
    zamiast CSV na obu domenach, wiec kosztowal 15 s timeoutu i zawsze
    konczyl sie fallbackiem.
    """
    stooq_sym = STOOQ_TICKERS.get(symbol)
    if not stooq_sym:
        return None

    hist = _load_stooq_csv(stooq_sym, period)

    live = None
    etf = GPW_INDEX_ETF.get(symbol)
    if etf:
        try:
            live = _yfinance_single(etf, period)
        except Exception:
            live = None

    result = splice_series(hist, live)
    if result is None:
        _track_failure(symbol)
        return None

    if live is not None and hist is not None:
        source = "etf+cache"
    elif live is not None:
        source = "etf"
    else:
        source = "cache"
    if benchmark_status(result)["stale"]:
        source += "-stale"
    _track_source(symbol, source)
    return result


# Alias wsteczny: strony 4, 8 i 9 wolaja te funkcje pod stara nazwa.
download_stooq = download_gpw_index


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
