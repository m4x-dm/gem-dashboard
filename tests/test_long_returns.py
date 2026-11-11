"""Testy modulu data/long_returns.py (strona 6_stopy_zwrotu)."""

import os

import numpy as np
import pandas as pd
import pytest

import data.long_returns as lr
from data.long_returns import (
    PERIOD_YEARS,
    PROXY_MAP,
    align_end,
    annual_volatility,
    calendar_year_returns,
    combine_fx,
    common_window,
    correlation_with_proxy,
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


def test_annual_volatility_ignores_gap():
    # 100,110,121 (+10%,+10%), brak miesiaca, potem 133.1 po dwoch miesiacach -> pomijamy
    s = _monthly([100, 110, 121, 999, 133.1, 146.41]).drop(_monthly([0] * 4).index[3])
    # stopy z kolejnych miesiecy: +10%, +10%, +10% (146.41/133.1) -> std 0
    assert annual_volatility(s) == pytest.approx(0.0, abs=1e-12)
    s2 = _monthly([100, 120, 108, 999, 110]).drop(_monthly([0] * 4).index[3])
    # kolejne stopy: +20%, -10% (110/999 pominiete) -> std = 0.15 -> x sqrt(12)
    assert annual_volatility(s2) == pytest.approx(0.15 * np.sqrt(12))


def test_annual_volatility_empty_is_nan():
    assert np.isnan(annual_volatility(pd.Series(dtype=float)))


def test_correlation_with_proxy_gap_in_one_series():
    a = _monthly([100, 110, 99, 120, 118, 130, 125, 140]).drop(_monthly([0] * 8).index[3])
    b = _monthly([50, 55, 49.5, 60, 59, 65, 62.5, 70])
    c = correlation_with_proxy(a, b, min_months=3)
    assert 0.9 < c <= 1.0


def _clear_caches():
    for f in (lr._load_monthly_cached, lr._fetch_usdpln_cached, lr._fetch_usdpln_yf_cached):
        f.clear()


def test_load_monthly_proxy_failure_returns_unspliced(monkeypatch):
    _clear_caches()
    days_etf = pd.bdate_range("1995-01-02", "2000-12-29")
    fake = {"SPY": pd.Series(np.linspace(100, 300, len(days_etf)), index=days_etf)}
    monkeypatch.setattr(lr, "_fetch_daily", lambda t, period: fake.get(t))
    s, proxy_t, end = lr.load_monthly("SPY", True)
    assert proxy_t is None and end is None
    assert s is not None and s.index[0] == pd.Timestamp("1995-01-31")
    _clear_caches()


def test_load_monthly_missing_etf_returns_none_triple(monkeypatch):
    _clear_caches()
    monkeypatch.setattr(lr, "_fetch_daily", lambda t, period: None)
    assert lr.load_monthly("SPY", True) == (None, None, None)
    assert lr.load_monthly("SPY", False) == (None, None, None)
    _clear_caches()


def test_load_monthly_impl_splices_when_proxy_enabled(monkeypatch):
    days_proxy = pd.bdate_range("1990-01-01", "2000-12-29")
    days_etf = pd.bdate_range("1995-01-02", "2000-12-29")
    fake = {
        "VFINX": pd.Series(np.linspace(10, 50, len(days_proxy)), index=days_proxy),
        "SPY": pd.Series(np.linspace(100, 300, len(days_etf)), index=days_etf),
    }
    monkeypatch.setattr(lr, "_fetch_daily", lambda t, period: fake.get(t))
    s, proxy_t, end = lr._load_monthly_impl("SPY", True)
    assert proxy_t == "VFINX" and end == pd.Timestamp("1995-01-31")
    assert s.index[0] == pd.Timestamp("1990-01-31")
    s2, proxy_t2, end2 = lr._load_monthly_impl("SPY", False)
    assert proxy_t2 is None and end2 is None and s2.index[0] == pd.Timestamp("1995-01-31")


def test_load_monthly_impl_missing_ticker(monkeypatch):
    monkeypatch.setattr(lr, "_fetch_daily", lambda t, period: None)
    assert lr._load_monthly_impl("SPY", True) == (None, None, None)


def test_correlation_with_proxy_identical_returns():
    a = _monthly([100, 110, 99, 120, 118])
    assert correlation_with_proxy(a, a * 3, min_months=3) == pytest.approx(1.0)


def test_correlation_with_proxy_too_short_overlap_is_nan():
    a = _monthly([1, 2], start="2000-01-31")
    b = _monthly([1, 2], start="2010-01-31")
    assert np.isnan(correlation_with_proxy(a, b))


@pytest.mark.skipif(os.environ.get("RUN_NETWORK") != "1", reason="test sieciowy: RUN_NETWORK=1")
@pytest.mark.parametrize("etf,proxy", sorted(PROXY_MAP.items()))
def test_proxy_quality_network(etf, proxy):
    e_d, p_d = lr._yf_max(etf), lr._yf_max(proxy)
    if e_d is None or p_d is None:
        pytest.skip(f"brak danych yfinance dla {etf} lub {proxy} (rate limit / siec)")
    e = lr.to_monthly(e_d)
    p = lr.to_monthly(p_d)
    corr = correlation_with_proxy(e, p)
    print(f"CORR {etf} vs {proxy}: {corr:.4f}")
    assert corr > 0.95, f"{etf} vs {proxy}: korelacja {corr:.3f}"


def test_fred_request_uses_honest_user_agent(monkeypatch):
    """FRED zrywa polaczenie dla podrobionego UA przegladarki — nie wysylamy 'Mozilla'."""
    sent = {}

    def fake_get(url, *args, **kwargs):
        sent["url"] = url
        sent["headers"] = kwargs.get("headers") or {}
        raise ConnectionError("stop")

    monkeypatch.setattr(lr.requests, "get", fake_get)
    monkeypatch.setattr(lr, "_fetch_daily", lambda t, period: None)
    lr._fetch_fred_usdpln.clear()
    lr._fetch_usdpln_cached.clear()
    lr._fetch_usdpln_yf_cached.clear()
    assert lr.fetch_usdpln_monthly() == (None, "none")
    lr._fetch_fred_usdpln.clear()  # nie zostawiaj negatywnego wyniku w cache dla innych testow
    assert sent["url"] == lr.FRED_USDPLN_URL
    ua = sent["headers"].get("User-Agent", "")
    assert "Mozilla" not in ua


def test_convert_to_pln_drops_months_before_dec_1995():
    usd = _growth(10, start="1990-01-31")  # 1990-01 .. 2000-01
    fx = pd.Series(2.0, index=usd.index)
    pln = convert_to_pln(usd, fx)
    assert pln.index[0] == pd.Timestamp("1995-12-31")
    assert (pln.index >= lr.PLN_START).all()
    assert pln.index[-1] == usd.index[-1]


def test_convert_to_pln_start_none_keeps_full_history():
    usd = _growth(10, start="1990-01-31")
    fx = pd.Series(2.0, index=usd.index)
    assert convert_to_pln(usd, fx, start=None).index[0] == pd.Timestamp("1990-01-31")
