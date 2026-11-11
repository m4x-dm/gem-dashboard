"""Dlugoterminowe stopy zwrotu ETF-ow (do 30 lat) — logika strony 6_stopy_zwrotu.

Wszystko na danych miesiecznych (cena z konca miesiaca). Czyste funkcje
na gorze pliku, warstwa pobierania z cache na dole.
"""

from __future__ import annotations

import io

import numpy as np
import pandas as pd

PERIOD_YEARS: tuple[int, ...] = (1, 3, 5, 10, 15, 20, 25, 30)

# ETF -> stary fundusz indeksowy Vanguard o tej samej ekspozycji (dane yfinance od 1980-1996).
# Para zostaje w mapie tylko, gdy korelacja miesiecznych stop we wspolnym okresie > 0,95
# (test_proxy_quality_network). Bez proxy: QQQ, ACWI, EWJ, EWU, FXI, TIP, GLD, IAU, GSG,
# DBC, VNQI, sektory XL*.
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
    "SHY": "VBISX",
    "VNQ": "VGSIX",
}


def period_label(years: int) -> str:
    """Polska etykieta okresu: 1 rok, 3 lata, 5 lat, 22 lata, 25 lat."""
    if years == 1:
        return "1 rok"
    if years % 10 in (2, 3, 4) and years % 100 not in (12, 13, 14):
        return f"{years} lata"
    return f"{years} lat"


def to_monthly(daily: pd.Series, today: pd.Timestamp | None = None) -> pd.Series:
    """Ceny z konca miesiaca (indeks = koniec miesiaca), bez biezacego niepelnego miesiaca."""
    s = daily.dropna()
    if s.empty:
        return s.astype(float)
    m = s.resample("ME").last().dropna()
    ref = pd.Timestamp(today) if today is not None else pd.Timestamp.today()
    current_month_end = ref.normalize() + pd.offsets.MonthEnd(0)
    if len(m) and m.index[-1] >= current_month_end:
        m = m.iloc[:-1]
    return m.astype(float)


SINCE_START = "Od startu"


def period_returns(series_m: pd.Series, years: tuple[int, ...] = PERIOD_YEARS) -> pd.DataFrame:
    """Stopa skumulowana i CAGR dla okresow konczacych sie na ostatnim punkcie szeregu.

    Wiersze: etykiety okresow + 'Od startu'. NaN, gdy historii za malo.
    CAGR 'Od startu' tylko dla historii >= 1 rok.
    """
    s = series_m.dropna()
    rows: dict[str, tuple[float, float]] = {}
    n_months = len(s) - 1
    for y in years:
        w = 12 * y
        if n_months >= w:
            total = s.iloc[-1] / s.iloc[-1 - w] - 1
            rows[period_label(y)] = (total, (1 + total) ** (1 / y) - 1)
        else:
            rows[period_label(y)] = (np.nan, np.nan)
    if n_months >= 1:
        total = s.iloc[-1] / s.iloc[0] - 1
        yrs = n_months / 12
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
    etf = etf_m.dropna()
    proxy = proxy_m.dropna()
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


FRED_USDPLN_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CCUSMA02PLM618N"


def parse_fred_csv(text: str) -> pd.Series:
    """CSV z FRED (observation_date, wartosc) -> Series z indeksem koniec miesiaca."""
    df = pd.read_csv(io.StringIO(text))
    dates = pd.to_datetime(df.iloc[:, 0]) + pd.offsets.MonthEnd(0)
    vals = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    s = pd.Series(vals.values, index=pd.DatetimeIndex(dates), dtype=float).dropna()
    s.name = "USDPLN"
    return s


def combine_fx(fred_m: pd.Series | None, yf_m: pd.Series | None) -> pd.Series | None:
    """Kurs miesieczny: FRED (srednia miesieczna, dluga historia), dalej miesiace z yfinance."""
    if fred_m is None or fred_m.empty:
        return yf_m
    if yf_m is None or yf_m.empty:
        return fred_m
    newer = yf_m[yf_m.index > fred_m.index[-1]]
    return pd.concat([fred_m, newer])


def convert_to_pln(usd_m: pd.Series, fx_m: pd.Series) -> pd.Series:
    """Cena w USD x kurs USD/PLN; tylko miesiace, dla ktorych jest kurs."""
    idx = usd_m.dropna().index.intersection(fx_m.dropna().index)
    out = usd_m.loc[idx] * fx_m.loc[idx]
    out.name = usd_m.name
    return out


def calendar_year_returns(series_m: pd.Series) -> tuple[pd.Series, int | None]:
    """Zwroty w latach kalendarzowych. Pierwszy rok tylko, gdy szereg ma grudzien roku poprzedniego.

    Zwraca (Series rok -> zwrot, rok YTD albo None, gdy ostatni miesiac to grudzien).
    """
    s = series_m.dropna()
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
    s = series_m.dropna()
    w = 12 * years
    return ((s / s.shift(w)) ** (1 / years) - 1).dropna()


def rolling_summary(rolling: pd.Series) -> dict:
    """Rozklad kroczacych CAGR: min, p25, median, p75, max, pct_negative, count."""
    r = rolling.dropna()
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
    return {k: v[v.index <= end] for k, v in valid.items()}


def common_window(series: dict[str, pd.Series]) -> dict[str, pd.Series]:
    """Wspolny okres: od najpozniejszego startu do najwczesniejszego konca."""
    aligned = align_end(series)
    if not aligned:
        return {}
    start = max(v.index[0] for v in aligned.values())
    return {k: v[v.index >= start] for k, v in aligned.items()}


def annual_volatility(series_m: pd.Series) -> float:
    """Zmiennosc roczna: odchylenie standardowe miesiecznych stop (ddof=0) x sqrt(12)."""
    r = series_m.dropna().pct_change().dropna()
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
