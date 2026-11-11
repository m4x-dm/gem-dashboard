"""Testy modulu data/long_returns.py (strona 6_stopy_zwrotu)."""

import os

import numpy as np
import pandas as pd
import pytest

from data.long_returns import (
    PERIOD_YEARS,
    PROXY_MAP,
    period_label,
    period_returns,
    splice_proxy,
    to_monthly,
)


def _monthly(values, start="2000-01-31"):
    idx = pd.date_range(start, periods=len(values), freq="ME")
    return pd.Series(values, index=idx, dtype=float)


def test_period_years_constant():
    assert PERIOD_YEARS == (1, 3, 5, 10, 15, 20, 25, 30)


@pytest.mark.parametrize("years,label", [
    (1, "1 rok"), (3, "3 lata"), (5, "5 lat"), (10, "10 lat"),
    (15, "15 lat"), (20, "20 lat"), (22, "22 lata"), (25, "25 lat"), (30, "30 lat"),
])
def test_period_label(years, label):
    assert period_label(years) == label


def test_to_monthly_takes_last_price_and_drops_current_month():
    idx = pd.bdate_range("2026-09-01", "2026-11-11")
    daily = pd.Series(np.arange(len(idx), dtype=float), index=idx)
    m = to_monthly(daily, today=pd.Timestamp("2026-11-11"))
    assert list(m.index) == [pd.Timestamp("2026-09-30"), pd.Timestamp("2026-10-31")]
    assert m.loc["2026-09-30"] == daily.loc[:"2026-09-30"].iloc[-1]
    assert m.loc["2026-10-31"] == daily.loc[:"2026-10-31"].iloc[-1]


def test_to_monthly_keeps_finished_month_when_data_ends_earlier():
    idx = pd.bdate_range("2026-08-01", "2026-09-30")
    daily = pd.Series(1.0, index=idx)
    m = to_monthly(daily, today=pd.Timestamp("2026-11-11"))
    assert m.index[-1] == pd.Timestamp("2026-09-30")


def test_to_monthly_empty():
    assert to_monthly(pd.Series(dtype=float)).empty


def _growth(years, annual=0.10, start="1990-12-31"):
    """Szereg rosnacy dokladnie `annual` rocznie, miesiecznie, years*12+1 punktow."""
    n = years * 12 + 1
    monthly = (1 + annual) ** (1 / 12)
    return _monthly(100 * monthly ** np.arange(n), start=start)


def test_period_returns_constant_growth():
    s = _growth(12)  # 12 lat historii
    df = period_returns(s)
    assert list(df.columns) == ["total", "cagr"]
    assert list(df.index) == ["1 rok", "3 lata", "5 lat", "10 lat", "15 lat",
                              "20 lat", "25 lat", "30 lat", "Od startu"]
    for lbl in ["1 rok", "3 lata", "5 lat", "10 lat", "Od startu"]:
        assert df.loc[lbl, "cagr"] == pytest.approx(0.10, abs=1e-9)
    assert df.loc["10 lat", "total"] == pytest.approx(1.10 ** 10 - 1, rel=1e-9)
    for lbl in ["15 lat", "20 lat", "25 lat", "30 lat"]:
        assert np.isnan(df.loc[lbl, "cagr"]) and np.isnan(df.loc[lbl, "total"])


def test_period_returns_since_start_under_one_year_has_no_cagr():
    s = _monthly([100, 101, 102, 103])
    df = period_returns(s)
    assert df.loc["Od startu", "total"] == pytest.approx(0.03)
    assert np.isnan(df.loc["Od startu", "cagr"])


def test_period_returns_empty():
    df = period_returns(pd.Series(dtype=float))
    assert df["cagr"].isna().all()


def test_proxy_map_contents():
    assert PROXY_MAP["SPY"] == "VFINX"
    assert PROXY_MAP["AGG"] == "VBMFX"
    assert "GLD" not in PROXY_MAP and "QQQ" not in PROXY_MAP


def test_splice_proxy_uses_proxy_returns_before_start_and_etf_after():
    proxy = _monthly([50, 55, 60, 66, 70, 77, 80], start="2000-01-31")
    etf = _monthly([200, 210, 231, 240], start="2000-04-30")  # start = 4. miesiac proxy
    spliced, proxy_end = splice_proxy(etf, proxy)
    assert proxy_end == pd.Timestamp("2000-04-30")
    assert spliced.index[0] == pd.Timestamp("2000-01-31")
    # od startu ETF-u poziomy identyczne z ETF-em (brak skoku)
    pd.testing.assert_series_equal(spliced.loc["2000-04-30":], etf, check_names=False, check_freq=False)
    # przed startem stopy zwrotu jak w proxy
    r_sp = spliced.pct_change().loc[:"2000-04-30"].dropna()
    r_px = proxy.pct_change().loc[:"2000-04-30"].dropna()
    np.testing.assert_allclose(r_sp.values, r_px.values)


def test_splice_proxy_no_overlap_returns_etf_unchanged():
    proxy = _monthly([1, 2, 3], start="2010-01-31")  # proxy po starcie ETF-u
    etf = _monthly([10, 11], start="2005-01-31")
    spliced, proxy_end = splice_proxy(etf, proxy)
    assert proxy_end is None
    pd.testing.assert_series_equal(spliced, etf, check_freq=False)


def test_splice_proxy_missing_start_month_in_proxy_returns_etf():
    proxy = pd.Series([1.0, 2.0], index=pd.to_datetime(["2000-01-31", "2000-02-29"]))
    etf = _monthly([10, 11], start="2000-04-30")
    spliced, proxy_end = splice_proxy(etf, proxy)
    assert proxy_end is None
    pd.testing.assert_series_equal(spliced, etf, check_freq=False)
