"""Sygnal GEM (ETF) liczy czyste 12M, ranking akcji zostaje na 12-1 skip-month."""
import numpy as np
import pandas as pd

from data.momentum import gem_classic_signal, latest_returns


def _prices() -> pd.DataFrame:
    # 300 sesji: EEM rosnie mocniej do t-21, potem traci 20%; QQQ rosnie rowno.
    n = 300
    idx = pd.bdate_range("2025-01-01", periods=n)
    qqq = np.linspace(100, 125, n)
    eem = np.linspace(100, 150, n)
    eem[-21:] = eem[-22] * 0.80
    flat = np.full(n, 100.0)
    return pd.DataFrame({"QQQ": qqq, "VEA": flat, "EEM": eem, "ACWI": flat, "AGG": flat}, index=idx)


def test_latest_returns_skip_month_default_is_12_1():
    px = _prices()
    rets = latest_returns(px)
    expected = px["EEM"].iloc[-22] / px["EEM"].iloc[-274] - 1
    assert abs(rets.loc["EEM", "12M"] - expected) < 1e-12


def test_latest_returns_no_skip_is_plain_252():
    px = _prices()
    rets = latest_returns(px, skip_month=False)
    expected = px["EEM"].iloc[-1] / px["EEM"].iloc[-253] - 1
    assert abs(rets.loc["EEM", "12M"] - expected) < 1e-12


def test_gem_signal_uses_plain_12m():
    px = _prices()
    # 12-1 wybralby EEM (spadek w ostatnim miesiacu pominiety), czyste 12M wybiera QQQ
    assert latest_returns(px).loc["EEM", "12M"] > latest_returns(px).loc["QQQ", "12M"]
    sig = gem_classic_signal(px, risk_free_annual=0.0)
    assert sig["signal"] == "QQQ"
    assert abs(sig["eem_12m"] - (px["EEM"].iloc[-1] / px["EEM"].iloc[-253] - 1)) < 1e-12
