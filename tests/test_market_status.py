"""Czyste funkcje Pulpitu — bez sieci, na syntetycznych danych."""
import numpy as np
import pandas as pd
import pytest

from data import market_status as ms


def _series(values, start="2026-01-01"):
    idx = pd.bdate_range(start, periods=len(values))
    return pd.Series(values, index=idx, dtype=float)


# --- compute_regime -------------------------------------------------------

def test_regime_risk_on():
    up = _series(np.linspace(100, 130, 80))
    down = _series(np.linspace(100, 80, 80))
    data = {"SPY": up, "^TNX": up, "GC=F": down, "DX-Y.NYB": down, "CL=F": up}
    r = ms.compute_regime(data)
    assert r["label"] == "Risk-On"
    assert r["score"] == pytest.approx(100.0)


def test_regime_risk_off():
    up = _series(np.linspace(100, 130, 80))
    down = _series(np.linspace(100, 80, 80))
    data = {"SPY": down, "^TNX": down, "GC=F": up, "DX-Y.NYB": up, "CL=F": down}
    assert ms.compute_regime(data)["label"] == "Risk-Off"


def test_regime_no_data_is_neutral():
    r = ms.compute_regime({})
    assert r["label"] == "Neutralny"
    assert r["score"] == pytest.approx(50.0)


def test_regime_ignores_short_series():
    short = _series(np.linspace(100, 130, 10))
    assert ms.compute_regime({"SPY": short})["label"] == "Neutralny"


# --- signal_since / next_rebalance_date ------------------------------------

def test_signal_since_returns_last_change():
    signals = [(pd.Timestamp("2025-01-31"), "QQQ"), (pd.Timestamp("2026-08-29"), "VEA")]
    assert ms.signal_since(signals) == (pd.Timestamp("2026-08-29"), "VEA")


def test_signal_since_empty():
    assert ms.signal_since([]) is None


def test_next_rebalance_is_first_business_day_next_month():
    assert ms.next_rebalance_date(pd.Timestamp("2026-11-15")) == pd.Timestamp("2026-12-01")


def test_next_rebalance_skips_weekend():
    # 1 sierpnia 2026 to sobota -> poniedzialek 3 sierpnia
    assert ms.next_rebalance_date(pd.Timestamp("2026-07-20")) == pd.Timestamp("2026-08-03")


# --- daily_change / top_movers ----------------------------------------------

def test_daily_change_uses_last_two_valid_rows():
    prices = pd.DataFrame({"A": [10.0, 11.0], "B": [20.0, 18.0], "C": [np.nan, 5.0]},
                          index=pd.bdate_range("2026-11-12", periods=2))
    chg = ms.daily_change(prices)
    assert chg["A"] == pytest.approx(0.10)
    assert chg["B"] == pytest.approx(-0.10)
    assert "C" not in chg.index  # brak poprzedniej wartosci


def test_daily_change_drops_inf():
    prices = pd.DataFrame({"A": [0.0, 5.0]}, index=pd.bdate_range("2026-11-12", periods=2))
    assert ms.daily_change(prices).empty


def test_top_movers_split():
    chg = pd.Series({"A": 0.05, "B": -0.04, "C": 0.01, "D": -0.10, "E": 0.20})
    gainers, losers = ms.top_movers(chg, n=2)
    assert list(gainers.index) == ["E", "A"]
    assert list(losers.index) == ["D", "B"]


# --- pulpit_earnings_tickers -------------------------------------------------

def test_earnings_tickers_watchlist_first_and_dedup():
    out = ms.pulpit_earnings_tickers({"CDR.WA", "AAPL"})
    assert out[:2] == sorted(["CDR.WA", "AAPL"])
    assert len(out) == len(set(out))
    assert "MSFT" in out


def test_next_rebalance_skips_new_years_day():
    # 1 stycznia 2027 to piatek (swieto) -> poniedzialek 4 stycznia
    assert ms.next_rebalance_date(pd.Timestamp("2026-12-15")) == pd.Timestamp("2027-01-04")
