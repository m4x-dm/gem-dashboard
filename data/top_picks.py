"""Silnik Top Picks (F18) — regula selekcji, log, equity, symulacja.

Czysty Python: ten modul NIE importuje streamlita, zeby dalo sie go
odpalic w GitHub Action i w testach bez runtime'u Streamlita.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from data.momentum import latest_returns, rank_based_score

# Wersja reguly — podbij przy KAZDEJ zmianie parametrow ponizej.
# Snapshoty z roznymi wersjami nie sa ze soba porownywalne.
RULE_VERSION = 1

DEFAULT_WEIGHTS = {"12M": 0.40, "6M": 0.30, "3M": 0.20, "1M": 0.10}
MIN_HISTORY = 273        # okno momentum 12-1 (13 miesiecy)
TURNOVER_WINDOW = 60     # sesji do mediany obrotu
MIN_TURNOVER = {
    "sp500": 50_000_000.0,   # USD
    "gpw": 5_000_000.0,      # PLN
}


@dataclass(frozen=True)
class Scorer:
    """Wymienna funkcja rankingujaca dla select_picks().

    Attributes:
        name: identyfikator do logow i komunikatow bledow
        supports_asof: czy scorer potrafi policzyc ranking NA DANY DZIEN.
            False dla scorerow fundamentalnych — yfinance zwraca stan na dzis
            niezaleznie od zadanej daty, wiec uzycie ich w simulate_rule()
            dalo by lookahead bias. simulate_rule() to sprawdza i odmawia.
        fn: (eligible_tickers, prices_do_asof, asof) -> Series ticker -> score.
            Wyzszy score = lepiej. NaN i braki sa pomijane.
    """
    name: str
    supports_asof: bool
    fn: Callable[[list[str], pd.DataFrame, pd.Timestamp], pd.Series]


def _momentum_scores(eligible: list[str], px: pd.DataFrame,
                     asof: pd.Timestamp) -> pd.Series:
    """Regula F18: rank_based_score na zwrotach 12M/6M/3M/1M z anti_1m."""
    rets = latest_returns(px[eligible])
    return rank_based_score(rets, weights=DEFAULT_WEIGHTS, anti_1m=True)


MOMENTUM_SCORER = Scorer(name="momentum", supports_asof=True, fn=_momentum_scores)

_DATA_DIR = Path(__file__).parent
HISTORY_PATH = _DATA_DIR / "top_picks_history.json"
SIM_PATH = _DATA_DIR / "top_picks_sim.json"


def _eligible(prices: pd.DataFrame, volumes: pd.DataFrame,
              asof, min_turnover: float) -> list[str]:
    """Tickery spelniajace filtr historii i plynnosci NA DZIEN asof.

    Plynnosc = mediana z TURNOVER_WINDOW ostatnich sesji z close * volume.
    """
    asof = pd.Timestamp(asof)
    px = prices.loc[:asof]
    vol = volumes.loc[:asof]
    out = []
    for ticker in px.columns:
        series = px[ticker].dropna()
        if len(series) < MIN_HISTORY:
            continue
        if ticker not in vol.columns:
            continue
        turnover = (px[ticker] * vol[ticker]).dropna().iloc[-TURNOVER_WINDOW:]
        if len(turnover) < TURNOVER_WINDOW // 2:
            continue
        if float(turnover.median()) < min_turnover:
            continue
        out.append(ticker)
    return out


def select_picks(prices: pd.DataFrame, volumes: pd.DataFrame,
                 groups: dict[str, str], asof,
                 top_n: int = 5, max_per_group: int = 2,
                 min_turnover: float = 0.0,
                 scorer: Scorer | None = None) -> list[dict]:
    """Wybiera top_n spolek na dzien asof.

    1. filtr historii (>= MIN_HISTORY sesji) i plynnosci (mediana obrotu 60d)
    2. scorer.fn() -> ranking (domyslnie MOMENTUM_SCORER)
    3. schodzenie po rankingu z limitem max_per_group na grupe
    4. rowne wagi

    Args:
        prices: ceny close (kolumny = tickery)
        volumes: wolumeny w tym samym ukladzie
        groups: ticker -> grupa (sektor GICS dla SP500, sektor dla GPW)
        asof: data, NA KTORA liczymy — dane po niej sa ignorowane
        top_n: ile pozycji w portfelu
        max_per_group: ile maksymalnie spolek z jednej grupy
        min_turnover: prog mediany dziennego obrotu (w walucie notowania)
        scorer: wymienna regula rankingujaca; None = MOMENTUM_SCORER

    Returns:
        Lista dictow gotowa do serializacji do JSON. Pusta, gdy brak kandydatow.
    """
    scorer = scorer or MOMENTUM_SCORER
    asof = pd.Timestamp(asof)
    px = prices.loc[:asof]
    if px.empty:
        return []

    eligible = _eligible(prices, volumes, asof, min_turnover)
    if not eligible:
        return []

    scores = scorer.fn(eligible, px, asof)
    if scores is None or len(scores) == 0:
        return []
    scores = scores.dropna().sort_values(ascending=False)

    picks: list[dict] = []
    counts: dict[str, int] = {}
    for ticker, score in scores.items():
        if ticker not in px.columns:
            continue
        group = groups.get(ticker, "?")
        if counts.get(group, 0) >= max_per_group:
            continue
        series = px[ticker].dropna()
        if series.empty:
            continue
        picks.append({
            "ticker": ticker,
            "group": group,
            "score": round(float(score), 4),
            "entry_price": round(float(series.iloc[-1]), 4),
            "entry_date": series.index[-1].strftime("%Y-%m-%d"),
            "weight": 0.0,
        })
        counts[group] = counts.get(group, 0) + 1
        if len(picks) == top_n:
            break

    if picks:
        weight = 1.0 / len(picks)
        for pick in picks:
            pick["weight"] = weight
    return picks


# ====== Persystencja loga ======

def load_history(path: Path | None = None) -> dict:
    """Wczytuje log typow. Zwraca pusty dict, gdy pliku nie ma lub jest uszkodzony."""
    path = Path(path) if path else HISTORY_PATH
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def append_snapshot(month_key: str, payload: dict, path: Path | None = None) -> bool:
    """Dopisuje snapshot dla miesiaca. NIE nadpisuje istniejacego klucza.

    Log jest append-only celowo: sekcja "Wyniki live" traci sens, jesli
    historia da sie po cichu poprawic.

    Returns:
        True gdy dopisano, False gdy klucz juz istnial.
    """
    path = Path(path) if path else HISTORY_PATH
    history = load_history(path)
    if month_key in history:
        return False
    history[month_key] = payload
    ordered = {k: history[k] for k in sorted(history)}
    path.write_text(json.dumps(ordered, indent=2, ensure_ascii=False), encoding="utf-8")
    return True


# ====== Wyniki live ======

def portfolio_equity(history: dict, prices: pd.DataFrame, market: str,
                     start_capital: float = 10000.0) -> pd.Series:
    """Krzywa kapitalu equal-weight odtworzona z loga typow.

    Kazdy snapshot obowiazuje od swojego asof do asof nastepnego snapshotu
    (ostatni — do konca dostepnych cen). Ceny wejscia bierzemy z ramki `prices`,
    nie z pola entry_price: dzieki temu splity i korekty dywidendowe sa spojne
    w calej serii (yfinance zwraca ceny skorygowane wstecz).

    Returns:
        Series indeksowana data. Pusta, gdy log nie ma wpisow dla rynku.
    """
    keys = sorted(history)
    segments = []
    for i, key in enumerate(keys):
        picks = history[key].get(market) or []
        if not picks:
            continue
        start = pd.Timestamp(history[key]["asof"])
        if i + 1 < len(keys):
            end = pd.Timestamp(history[keys[i + 1]]["asof"])
        else:
            end = prices.index[-1]
        segments.append((start, end, picks))

    if not segments:
        return pd.Series(dtype=float)

    chunks: list[pd.Series] = []
    capital = start_capital
    for start, end, picks in segments:
        window = prices.loc[(prices.index >= start) & (prices.index <= end)]
        tickers = [p["ticker"] for p in picks if p["ticker"] in window.columns]
        if window.empty or not tickers:
            continue
        relative = window[tickers].divide(window[tickers].iloc[0], axis=1).ffill()
        weights = pd.Series({p["ticker"]: p["weight"] for p in picks if p["ticker"] in tickers})
        weights = weights / weights.sum()
        segment = (relative * weights).sum(axis=1) * capital
        if chunks:
            segment = segment.iloc[1:]   # data styku nalezy do poprzedniego segmentu
        if segment.empty:
            continue
        chunks.append(segment)
        capital = float(segment.iloc[-1])

    return pd.concat(chunks) if chunks else pd.Series(dtype=float)


# ====== Symulacja reguly ======

def _month_end_sessions(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    """Ostatnia realna sesja kazdego miesiaca z indeksu."""
    series = pd.Series(index, index=index)
    return list(series.groupby([index.year, index.month]).last())


def simulate_rule(prices: pd.DataFrame, volumes: pd.DataFrame,
                  groups: dict[str, str], start,
                  min_turnover: float = 0.0,
                  top_n: int = 5, max_per_group: int = 2,
                  transaction_cost: float = 0.001,
                  tax_belka: float = 0.19,
                  start_capital: float = 10000.0,
                  scorer: Scorer | None = None) -> pd.Series:
    """Symuluje regule F18 miesiac po miesiacu, uzywajac tego samego select_picks().

    Swiadomie NIE uzywa backtest_rotation() z momentum.py — tamta funkcja nie zna
    limitu sektorowego ani filtru plynnosci, wiec liczylaby inna regule niz log.

    UWAGA: wynik ma survivorship bias — universe jest dzisiejsze. Nie jest to
    track record i UI musi to komunikowac wprost.

    Dziala wylacznie ze scorerami majacymi supports_asof=True. Scorery
    fundamentalne sa forward-only i podnosza ValueError.

    Koszty: transaction_cost skalowany turnoverem (frakcja wymienionych pozycji),
    Belka naliczana od dodatniego zysku segmentu, rowniez skalowana turnoverem.
    """
    scorer = scorer or MOMENTUM_SCORER
    if not scorer.supports_asof:
        raise ValueError(
            f"Scorer '{scorer.name}' ma supports_asof=False — nie potrafi policzyc "
            "rankingu na historyczna date. Symulacja uzylaby dzisiejszych danych "
            "na kazdej dacie wstecz (lookahead bias). Ta strategia jest forward-only."
        )
    prices = prices.ffill()
    window = prices.loc[pd.Timestamp(start):]
    month_ends = _month_end_sessions(window.index)
    if len(month_ends) < 2:
        return pd.Series(dtype=float)

    dates: list[pd.Timestamp] = []
    equity: list[float] = []
    capital = start_capital
    previous: list[str] = []

    for i in range(len(month_ends) - 1):
        t0, t1 = month_ends[i], month_ends[i + 1]
        picks = select_picks(prices, volumes, groups, t0,
                             top_n=top_n, max_per_group=max_per_group,
                             min_turnover=min_turnover, scorer=scorer)
        if not picks:
            dates.append(t1)
            equity.append(capital)
            continue

        tickers = [p["ticker"] for p in picks]
        segment_ret = (prices.loc[t1, tickers] / prices.loc[t0, tickers] - 1).dropna()
        if segment_ret.empty:
            dates.append(t1)
            equity.append(capital)
            continue

        gross = float(segment_ret.mean())
        turnover = 1.0 if not previous else len(set(tickers) - set(previous)) / len(tickers)
        cost = transaction_cost * turnover
        gain = capital * gross
        tax = tax_belka * max(gain, 0.0) * turnover
        capital = capital * (1.0 + gross - cost) - tax

        previous = tickers
        dates.append(t1)
        equity.append(capital)

    return pd.Series(equity, index=pd.DatetimeIndex(dates))
