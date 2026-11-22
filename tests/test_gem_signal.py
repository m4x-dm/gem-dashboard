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


def _px_12m(rets: dict, n: int = 300) -> pd.DataFrame:
    """Ceny liniowe od 100 tak, by czyste 12M (t / t-252) = zadany zwrot."""
    idx = pd.bdate_range("2024-01-01", periods=n)
    out = {}
    for t, r in rets.items():
        start = 100.0
        end = start * (1 + r)
        step = (end - start) / 252
        out[t] = [start + step * max(i - (n - 253), 0) for i in range(n)]
    return pd.DataFrame(out, index=idx)


def test_absolute_filter_on_winner_not_qqq():
    # XI 2026: QQQ +1,9% < T-bill 4,1%, ale VEA +9,4% > T-bill → VEA, nie AGG
    px = _px_12m({"QQQ": 0.019, "VEA": 0.094, "EEM": 0.019, "ACWI": 0.052, "AGG": 0.0})
    sig = gem_classic_signal(px, 4.1)
    assert sig["signal"] == "VEA"


def test_agg_when_best_equity_below_rf():
    px = _px_12m({"QQQ": 0.01, "VEA": 0.03, "EEM": -0.05, "ACWI": 0.02, "AGG": 0.0})
    assert gem_classic_signal(px, 4.1)["signal"] == "AGG"


def test_backtest_uses_same_rule_as_signal():
    from data.momentum import backtest_gem
    px = _px_12m({"QQQ": 0.019, "VEA": 0.094, "EEM": 0.019, "ACWI": 0.052, "AGG": 0.0}, n=320)
    res = backtest_gem(px, 4.1)
    assert res["signals"][-1][1] == "VEA"
