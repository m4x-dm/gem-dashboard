"""Silnik Top Picks (F18) — regula selekcji, log, equity, symulacja.

Czysty Python: ten modul NIE importuje streamlita, zeby dalo sie go
odpalic w GitHub Action i w testach bez runtime'u Streamlita.
"""

from __future__ import annotations

import json
from pathlib import Path

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
                 min_turnover: float = 0.0) -> list[dict]:
    """Wybiera top_n spolek na dzien asof wg reguly F18.

    1. filtr historii (>= MIN_HISTORY sesji) i plynnosci (mediana obrotu 60d)
    2. latest_returns() -> rank_based_score() (12M 40 / 6M 30 / 3M 20 / 1M 10, anti_1m)
    3. schodzenie po rankingu z limitem max_per_group na grupe
    4. rowne wagi

    Args:
        prices: ceny close (kolumny = tickery)
        volumes: wolumeny w tym samym ukladzie
        groups: ticker -> grupa (sektor GICS dla SP500, indeks dla GPW)
        asof: data, NA KTORA liczymy — dane po niej sa ignorowane
        top_n: ile pozycji w portfelu
        max_per_group: ile maksymalnie spolek z jednej grupy
        min_turnover: prog mediany dziennego obrotu (w walucie notowania)

    Returns:
        Lista dictow gotowa do serializacji do JSON. Pusta, gdy brak kandydatow.
    """
    asof = pd.Timestamp(asof)
    px = prices.loc[:asof]
    if px.empty:
        return []

    eligible = _eligible(prices, volumes, asof, min_turnover)
    if not eligible:
        return []

    rets = latest_returns(px[eligible])
    scores = rank_based_score(rets, weights=DEFAULT_WEIGHTS, anti_1m=True).dropna()
    scores = scores.sort_values(ascending=False)

    picks: list[dict] = []
    counts: dict[str, int] = {}
    for ticker, score in scores.items():
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
