"""Dlugoterminowe stopy zwrotu ETF-ow (do 30 lat) — logika strony 6_stopy_zwrotu.

Wszystko na danych miesiecznych (cena z konca miesiaca). Czyste funkcje
na gorze pliku, warstwa pobierania z cache na dole.
"""

from __future__ import annotations

import io

import numpy as np
import pandas as pd
import requests
import streamlit as st

from data.downloader import download_single

PERIOD_YEARS: tuple[int, ...] = (1, 3, 5, 10, 15, 20, 25, 30)
SINCE_START = "Od startu"
FRED_USDPLN_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CCUSMA02PLM618N"

# ETF -> stary fundusz indeksowy Vanguard o tej samej ekspozycji (dane yfinance od 1980-1996).
# Para zostaje w mapie tylko, gdy korelacja miesiecznych stop we wspolnym okresie > 0,95
# (test_proxy_quality_network). Bez proxy: QQQ, ACWI, EWJ, EWU, FXI, TIP, GLD, IAU, GSG,
# DBC, VNQI, sektory XL*.
# SHY: VBISX korelacja 0,886 < 0,95 — bez proxy.
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
    "VNQ": "VGSIX",
}


def _clean(s: pd.Series) -> pd.Series:
    """dropna, tylko wartosci > 0, sort po indeksie, bez duplikatow indeksu (zostaje ostatni)."""
    s = s.dropna()
    s = s[s > 0].sort_index()
    return s[~s.index.duplicated(keep="last")].astype(float)


def period_label(years: int) -> str:
    """Polska etykieta okresu: 1 rok, 3 lata, 5 lat, 22 lata, 25 lat."""
    if years == 1:
        return "1 rok"
    if years % 10 in (2, 3, 4) and years % 100 not in (12, 13, 14):
        return f"{years} lata"
    return f"{years} lat"


def to_monthly(daily: pd.Series, today: pd.Timestamp | None = None) -> pd.Series:
    """Ceny z konca miesiaca (indeks = koniec miesiaca).

    Miesiac `today` jest zawsze odrzucany (niepelny).
    """
    s = daily.dropna()
    if getattr(s.index, "tz", None) is not None:
        s = s.tz_localize(None)
    if s.empty:
        return s.astype(float)
    m = s.resample("ME").last().dropna()
    ref = pd.Timestamp(today) if today is not None else pd.Timestamp.today()
    current_month_end = ref.normalize() + pd.offsets.MonthEnd(0)
    if len(m) and m.index[-1] >= current_month_end:
        m = m.iloc[:-1]
    return m.astype(float)


def period_returns(series_m: pd.Series, years: tuple[int, ...] = PERIOD_YEARS) -> pd.DataFrame:
    """Stopa skumulowana i CAGR dla okresow konczacych sie na ostatnim punkcie szeregu.

    Wiersze: etykiety okresow + 'Od startu'. NaN, gdy historii za malo.
    CAGR 'Od startu' tylko dla historii >= 1 rok.
    """
    s = _clean(series_m)
    rows: dict[str, tuple[float, float]] = {}
    for y in years:
        if len(s) >= 2:
            start = s.index[-1] - pd.offsets.MonthEnd(12 * y)
            if start in s.index:
                total = s.iloc[-1] / s.loc[start] - 1
                rows[period_label(y)] = (total, (1 + total) ** (1 / y) - 1)
                continue
        rows[period_label(y)] = (np.nan, np.nan)
    if len(s) >= 2:
        total = s.iloc[-1] / s.iloc[0] - 1
        yrs = (s.index[-1].to_period("M") - s.index[0].to_period("M")).n / 12
        cagr = (1 + total) ** (1 / yrs) - 1 if yrs >= 1 else np.nan
        rows[SINCE_START] = (total, cagr)
    else:
        rows[SINCE_START] = (np.nan, np.nan)
    return pd.DataFrame.from_dict(rows, orient="index", columns=["total", "cagr"])


def splice_proxy(etf_m: pd.Series, proxy_m: pd.Series) -> tuple[pd.Series, pd.Timestamp | None]:
    """Wydluza historie ETF-u o stopy zwrotu proxy sprzed jego startu.

    Proxy skalowane tak, by w pierwszym miesiacu ETF-u mialo jego poziom: brak skoku,
    od startu poziomy = ETF. Zwraca (szereg, miesiac startu ETF-u) albo (ETF, None),
    gdy proxy nie ma danych z miesiaca startu i wczesniej.
    """
    etf = _clean(etf_m)
    proxy = _clean(proxy_m)
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


def parse_fred_csv(text: str) -> pd.Series:
    """CSV z FRED (observation_date, wartosc) -> Series z indeksem koniec miesiaca."""
    df = pd.read_csv(io.StringIO(text))
    dates = pd.to_datetime(df.iloc[:, 0]) + pd.offsets.MonthEnd(0)
    vals = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    s = pd.Series(vals.values, index=pd.DatetimeIndex(dates), dtype=float).dropna()
    s = s[s > 0]
    s.name = "USDPLN"
    return s


def combine_fx(fred_m: pd.Series | None, yf_m: pd.Series | None) -> pd.Series | None:
    """Kurs miesieczny: FRED (srednia miesieczna, dluga historia), dalej miesiace z yfinance.

    Uwaga: FRED to srednia z miesiaca, yfinance to kurs z konca miesiaca — na styku
    jest niewielki uskok.
    """
    if fred_m is None or fred_m.empty:
        return yf_m
    if yf_m is None or yf_m.empty:
        return fred_m
    newer = yf_m[yf_m.index > fred_m.index[-1]]
    return pd.concat([fred_m, newer])


def convert_to_pln(usd_m: pd.Series, fx_m: pd.Series) -> pd.Series:
    """Cena w USD x kurs USD/PLN; tylko miesiace, dla ktorych jest kurs."""
    usd = _clean(usd_m)
    fx = _clean(fx_m)
    idx = usd.index.intersection(fx.index)
    out = usd.loc[idx] * fx.loc[idx]
    out.name = usd_m.name
    return out


def calendar_year_returns(series_m: pd.Series) -> tuple[pd.Series, int | None]:
    """Zwroty w latach kalendarzowych. Pierwszy rok tylko, gdy szereg ma grudzien roku poprzedniego.

    Zwraca (Series rok -> zwrot, rok YTD albo None, gdy ostatni miesiac to grudzien).
    """
    s = _clean(series_m)
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
    s = _clean(series_m)
    w = 12 * years
    base = s.reindex(s.index - pd.offsets.MonthEnd(w))
    r = (s / base.values) ** (1 / years) - 1
    return r.replace([np.inf, -np.inf], np.nan).dropna()


def rolling_summary(rolling: pd.Series) -> dict:
    """Rozklad kroczacych CAGR: min, p25, median, p75, max, pct_negative, count."""
    r = rolling.replace([np.inf, -np.inf], np.nan).dropna()
    if r.empty:
        nan = float("nan")
        return {"min": nan, "p25": nan, "median": nan, "p75": nan, "max": nan,
                "pct_negative": nan, "count": 0}
    return {
        "min": float(r.min()), "p25": float(r.quantile(0.25)), "median": float(r.median()),
        "p75": float(r.quantile(0.75)), "max": float(r.max()),
        "pct_negative": float((r < 0).mean()), "count": int(len(r)),
    }


def align_end(series: dict[str, pd.Series]) -> dict[str, pd.Series]:
    """Przycina wszystkie szeregi do najwczesniejszego wspolnego ostatniego miesiaca."""
    valid = {k: v.dropna() for k, v in series.items() if not v.dropna().empty}
    if not valid:
        return {}
    end = min(v.index[-1] for v in valid.values())
    cut = {k: v[v.index <= end] for k, v in valid.items()}
    return {k: v for k, v in cut.items() if not v.empty}


def common_window(series: dict[str, pd.Series]) -> dict[str, pd.Series]:
    """Wspolny okres: od najpozniejszego startu do najwczesniejszego konca ({} gdy brak nakladania)."""
    valid = {k: v.dropna() for k, v in series.items() if not v.dropna().empty}
    if not valid:
        return {}
    start = max(v.index[0] for v in valid.values())
    end = min(v.index[-1] for v in valid.values())
    if start > end:
        return {}
    return {k: v[(v.index >= start) & (v.index <= end)] for k, v in valid.items()}


def annual_volatility(series_m: pd.Series) -> float:
    """Zmiennosc roczna: odchylenie standardowe miesiecznych stop (ddof=0) x sqrt(12)."""
    r = _clean(series_m).asfreq("ME").pct_change(fill_method=None).dropna()
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


def correlation_with_proxy(etf_m: pd.Series, proxy_m: pd.Series, min_months: int = 24) -> float:
    """Korelacja miesiecznych stop zwrotu we wspolnym okresie (NaN, gdy < min_months)."""
    r = pd.concat([_clean(etf_m).pct_change(fill_method=None),
                   _clean(proxy_m).pct_change(fill_method=None)], axis=1).dropna()
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
