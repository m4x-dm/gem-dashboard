"""data/company.py — czyste funkcje karty spolki (offline)."""
import numpy as np
import pandas as pd
import pytest

from data import company as co


def _prices(n=300, tickers=("AAA", "BBB", "CCC"), seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2025-01-01", periods=n)
    data = {t: 100 * np.cumprod(1 + rng.normal(0.0005 * (i + 1), 0.01, n)) for i, t in enumerate(tickers)}
    return pd.DataFrame(data, index=idx)


# --- momentum_profile -------------------------------------------------------

def test_momentum_profile_rank_and_returns():
    p = _prices()
    prof = co.momentum_profile("CCC", p, rf=4.0)
    assert prof["of"] == 3
    assert 1 <= prof["rank"] <= 3
    for k in ("r1m", "r3m", "r6m", "r12m"):
        assert k in prof


def test_momentum_profile_unknown_ticker():
    assert co.momentum_profile("ZZZ", _prices(), rf=4.0) is None


def test_momentum_profile_short_history():
    p = _prices(n=120)
    assert co.momentum_profile("AAA", p, rf=4.0) is None


# --- dividend_summary -------------------------------------------------------

def _divs():
    dates = pd.to_datetime(["2019-05-10", "2020-05-11", "2021-05-10", "2022-05-10",
                            "2023-05-10", "2024-05-10", "2025-05-12"])
    return pd.Series([1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6], index=dates)


def test_dividend_summary_basic():
    s = co.dividend_summary(_divs(), price=40.0, info={"dividendYield": 0.04, "payoutRatio": 0.5},
                            today=pd.Timestamp("2026-11-15"))
    assert s["pays"] is True
    assert s["yield"] == pytest.approx(0.04)
    assert s["payout"] == pytest.approx(0.5)
    assert s["years_paid"] == 7          # 2019..2025 bez przerw
    # cagr5: 2025 (1.6) vs 2020 (1.1)
    assert s["cagr5"] == pytest.approx((1.6 / 1.1) ** (1 / 5) - 1)
    assert list(s["annual"].index)[-1] == 2025
    assert len(s["last8"]) == 7


def test_dividend_summary_yield_fallback_from_ttm():
    divs = pd.Series([0.5, 0.5], index=pd.to_datetime(["2026-03-01", "2026-09-01"]))
    s = co.dividend_summary(divs, price=50.0, info={}, today=pd.Timestamp("2026-11-15"))
    assert s["yield"] == pytest.approx(1.0 / 50.0)


def test_dividend_summary_yield_percent_normalised():
    # yfinance >= 0.2.5x zwraca dividendYield w procentach (np. 0.41 = 0,41%)
    s = co.dividend_summary(_divs(), price=40.0, info={"dividendYield": 4.0},
                            today=pd.Timestamp("2026-11-15"))
    assert s["yield"] == pytest.approx(0.04)


def test_dividend_summary_no_dividends():
    assert co.dividend_summary(pd.Series(dtype=float), price=10.0, info={},
                               today=pd.Timestamp("2026-11-15")) == {"pays": False}


# --- dividend_after_tax -----------------------------------------------------

@pytest.mark.parametrize("market,account,rate", [
    ("GPW", "zwykle", 0.19), ("GPW", "ike", 0.0), ("GPW", "ikze", 0.0),
    ("SP500", "zwykle", 0.19), ("SP500", "ike", 0.15), ("SP500", "ikze", 0.15),
])
def test_dividend_after_tax(market, account, rate):
    r = co.dividend_after_tax(10_000, 0.05, market, account)
    assert r["gross"] == pytest.approx(500.0)
    assert r["tax"] == pytest.approx(500.0 * rate)
    assert r["net"] == pytest.approx(500.0 * (1 - rate))
    assert r["note"]


# --- sector_peers -----------------------------------------------------------

def test_sector_peers_nearest_log_cap():
    caps = pd.Series({"X": 100e9, "A": 90e9, "B": 120e9, "C": 1e9, "D": 3000e9, "E": 80e9, "F": 50e9})
    assert co.sector_peers("X", caps, n=3) == ["A", "B", "E"]


def test_sector_peers_small_sector():
    caps = pd.Series({"X": 10e9, "A": 5e9})
    assert co.sector_peers("X", caps, n=5) == ["A"]


def test_sector_peers_missing_cap_returns_largest():
    caps = pd.Series({"A": 5e9, "B": 50e9, "C": 20e9})
    assert co.sector_peers("X", caps, n=2) == ["B", "C"]


# --- peer_table -------------------------------------------------------------

def test_peer_table_median_row():
    rows = {
        "X": {"market_cap": 100e9, "pe": 20.0, "fwd_pe": 18.0, "ev_ebitda": 12.0, "roe": 0.2,
              "profit_margin": 0.1, "revenue_growth": 0.05, "dividend_yield": 0.01, "mom12": 0.3},
        "A": {"market_cap": 80e9, "pe": 10.0, "fwd_pe": None, "ev_ebitda": 8.0, "roe": 0.1,
              "profit_margin": 0.2, "revenue_growth": 0.1, "dividend_yield": None, "mom12": 0.1},
    }
    df = co.peer_table(rows)
    assert list(df.index) == ["X", "A", "Mediana grupy"]
    assert df.loc["Mediana grupy", "P/E"] == pytest.approx(15.0)
    assert df.loc["Mediana grupy", "Forward P/E"] == pytest.approx(18.0)
    assert np.isnan(df.loc["A", "Forward P/E"])
    assert set(co.LOWER_IS_BETTER) == {"P/E", "Forward P/E", "EV/EBITDA"}


# --- wrappery (offline, monkeypatch) ---------------------------------------

def test_sector_caps_uses_info(monkeypatch):
    import data.company as c
    fake = {"AAA": {"marketCap": 10}, "BBB": {"marketCap": None}, "CCC": {}}
    monkeypatch.setattr(c, "_fetch_info", lambda t: fake.get(t, {}))
    monkeypatch.setattr(c, "_sector_members", lambda market, sector: ["AAA", "BBB", "CCC"])
    caps = c.sector_caps.__wrapped__("SP500", "Tech")
    assert caps.to_dict() == {"AAA": 10.0}


def test_company_profile_fields(monkeypatch):
    import data.company as c
    monkeypatch.setattr(c, "_fetch_info", lambda t: {"longBusinessSummary": "x", "beta": 1.2,
                                                     "fiftyTwoWeekLow": 1, "fiftyTwoWeekHigh": 2,
                                                     "exchange": "NMS", "currency": "USD"})
    p = c.company_profile.__wrapped__("AAA")
    assert p == {"summary": "x", "beta": 1.2, "low52": 1.0, "high52": 2.0, "exchange": "NMS", "currency": "USD"}
