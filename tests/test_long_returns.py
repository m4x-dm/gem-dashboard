"""Testy modulu data/long_returns.py (strona 6_stopy_zwrotu)."""

import os

import numpy as np
import pandas as pd
import pytest

from data.long_returns import (
    PERIOD_YEARS,
    PROXY_MAP,
    combine_fx,
    convert_to_pln,
    parse_fred_csv,
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


FRED_SAMPLE = (
    "observation_date,CCUSMA02PLM618N\n"
    "1996-01-01,2.4775\n"
    "1996-02-01,.\n"
    "1996-03-01,2.5310\n"
)


def test_parse_fred_csv_month_end_index_and_skips_missing():
    s = parse_fred_csv(FRED_SAMPLE)
    assert list(s.index) == [pd.Timestamp("1996-01-31"), pd.Timestamp("1996-03-31")]
    assert s.iloc[0] == pytest.approx(2.4775)


def test_combine_fx_appends_only_newer_months():
    fred = _monthly([3.0, 3.1], start="2026-08-31")
    yf_m = _monthly([9.9, 3.2, 3.3], start="2026-08-31")  # sierpien zignorowany
    out = combine_fx(fred, yf_m)
    assert list(out.values) == [3.0, 3.1, 3.3]
    assert out.index[-1] == pd.Timestamp("2026-10-31")


def test_combine_fx_without_fred():
    yf_m = _monthly([3.2, 3.3])
    pd.testing.assert_series_equal(combine_fx(None, yf_m), yf_m, check_freq=False)


def test_convert_to_pln_constant_rate_keeps_returns():
    usd = _monthly([100, 110, 121])
    fx = _monthly([4.0, 4.0, 4.0])
    pln = convert_to_pln(usd, fx)
    np.testing.assert_allclose(pln.pct_change().dropna().values, [0.10, 0.10])


def test_convert_to_pln_compounds_fx_and_drops_months_without_rate():
    usd = _monthly([100, 110, 121])
    fx = _monthly([4.0, 4.2], start="2000-02-29")  # brak kursu za styczen
    pln = convert_to_pln(usd, fx)
    assert list(pln.index) == list(fx.index)
    assert pln.pct_change().iloc[-1] == pytest.approx(1.10 * 1.05 - 1)
