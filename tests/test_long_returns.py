"""Testy modulu data/long_returns.py (strona 6_stopy_zwrotu)."""

import os

import numpy as np
import pandas as pd
import pytest

from data.long_returns import (
    PERIOD_YEARS,
    PROXY_MAP,
    align_end,
    annual_volatility,
    calendar_year_returns,
    combine_fx,
    common_window,
    convert_to_pln,
    data_since_label,
    parse_fred_csv,
    period_label,
    period_returns,
    rolling_cagr,
    rolling_summary,
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
    (2, "2 lata"), (12, "12 lat"), (14, "14 lat"), (21, "21 lat"), (24, "24 lata"),
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


def test_calendar_year_returns_skips_partial_first_year_and_flags_ytd():
    # start w marcu 2000: rok 2000 niepelny -> pominiety; 2001 pelny; 2002 do marca -> YTD
    idx = pd.date_range("2000-03-31", "2002-03-31", freq="ME")
    s = pd.Series(np.linspace(100, 200, len(idx)), index=idx)
    yearly, ytd_year = calendar_year_returns(s)
    assert list(yearly.index) == [2001, 2002]
    assert yearly.loc[2001] == pytest.approx(s.loc["2001-12-31"] / s.loc["2000-12-31"] - 1)
    assert ytd_year == 2002


def test_calendar_year_returns_full_last_year_has_no_ytd():
    idx = pd.date_range("1999-12-31", "2001-12-31", freq="ME")
    s = pd.Series(np.linspace(100, 150, len(idx)), index=idx)
    yearly, ytd_year = calendar_year_returns(s)
    assert list(yearly.index) == [2000, 2001]
    assert ytd_year is None


def test_rolling_cagr_window_count_and_value():
    s = _growth(6)  # 73 punkty
    r = rolling_cagr(s, 5)
    assert len(r) == 73 - 60
    np.testing.assert_allclose(r.values, 0.10)


def test_rolling_summary():
    r = pd.Series([-0.02, 0.01, 0.03, 0.05, 0.10])
    out = rolling_summary(r)
    assert out["min"] == -0.02 and out["max"] == 0.10
    assert out["median"] == pytest.approx(0.03)
    assert out["pct_negative"] == pytest.approx(0.2)
    assert out["count"] == 5


def test_rolling_summary_empty():
    out = rolling_summary(pd.Series(dtype=float))
    assert out["count"] == 0 and np.isnan(out["median"])


def test_align_end_cuts_to_earliest_last_month():
    a = _monthly([1, 2, 3, 4], start="2026-07-31")
    b = _monthly([1, 2, 3], start="2026-07-31")
    out = align_end({"A": a, "B": b})
    assert out["A"].index[-1] == out["B"].index[-1] == pd.Timestamp("2026-09-30")


def test_common_window_cuts_to_latest_start():
    a = _monthly(range(1, 11), start="2000-01-31")
    b = _monthly(range(1, 6), start="2000-06-30")
    out = common_window({"A": a, "B": b})
    assert out["A"].index[0] == out["B"].index[0] == pd.Timestamp("2000-06-30")
    assert len(out["A"]) == len(out["B"])


def test_annual_volatility():
    s = _monthly([100, 110, 99, 108.9])  # stopy +10%, -10%, +10%
    r = s.pct_change().dropna()
    assert annual_volatility(s) == pytest.approx(r.std(ddof=0) * np.sqrt(12))


def test_data_since_label():
    s = _monthly([1, 2], start="1980-01-31")
    assert data_since_label(s, None, None) == "1980"
    assert data_since_label(s, "VFINX", pd.Timestamp("1993-01-31")) == "1980 (proxy VFINX do 01.1993)"


def test_period_returns_missing_month_is_date_based():
    s = _growth(6)
    s = s.drop(s.index[30])
    df = period_returns(s)
    assert df.loc["1 rok", "cagr"] == pytest.approx(0.10, abs=1e-9)
    assert df.loc["3 lata", "cagr"] == pytest.approx(0.10, abs=1e-9)


def test_period_returns_nan_when_start_month_missing():
    s = _growth(6)
    s = s.drop(s.index[-13])  # brak miesiaca bazowego dla "1 rok"
    df = period_returns(s)
    assert np.isnan(df.loc["1 rok", "cagr"])
    assert df.loc["3 lata", "cagr"] == pytest.approx(0.10, abs=1e-9)


def test_rolling_cagr_missing_month_not_distorted():
    s = _growth(6)
    missing = s.index[30]
    s = s.drop(missing)
    r = rolling_cagr(s, 1)
    assert missing not in r.index
    assert (missing + pd.offsets.MonthEnd(12)) not in r.index
    assert len(r) == 59
    np.testing.assert_allclose(r.values, 0.10)


def test_common_window_no_overlap_returns_empty():
    a = _monthly([1, 2, 3], start="2005-01-31")
    b = _monthly([1, 2, 3], start="2010-01-31")
    assert common_window({"A": a, "B": b}) == {}


def test_to_monthly_tz_aware():
    idx = pd.bdate_range("2026-08-01", "2026-10-15", tz="America/New_York")
    daily = pd.Series(np.arange(len(idx), dtype=float), index=idx)
    m = to_monthly(daily, today=pd.Timestamp("2026-11-11"))
    assert m.index.tz is None
    assert m.index[-1] == pd.Timestamp("2026-10-31")


def test_convert_to_pln_drops_zero_rate():
    usd = _monthly([100, 110, 121])
    fx = _monthly([4.0, 0.0, 4.0])
    pln = convert_to_pln(usd, fx)
    assert len(pln) == 2 and np.isfinite(pln.values).all()


def test_parse_fred_csv_drops_zero():
    s = parse_fred_csv("observation_date,X" + chr(10) + "2000-01-01,0" + chr(10) + "2000-02-01,2.0" + chr(10))
    assert list(s.values) == [2.0]


def test_period_returns_unsorted_input_same_as_sorted():
    s = _growth(6)
    pd.testing.assert_frame_equal(period_returns(s.iloc[::-1]), period_returns(s))


def test_rolling_summary_drops_inf():
    out = rolling_summary(pd.Series([0.1, np.inf, 0.2]))
    assert out["count"] == 2 and out["max"] == 0.2


def test_combine_fx_without_yfinance():
    fred = _monthly([3.0, 3.1])
    pd.testing.assert_series_equal(combine_fx(fred, None), fred, check_freq=False)
