"""Karta spolki przez router — offline (dane podstawione)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")
PAGE = "views/spolki/karta.py"


class _FakeLS:
    def __init__(self, *a, **k): pass
    def getItem(self, *a, **k): return None
    def setItem(self, *a, **k): return None


def _series(n=400, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2025-01-01", periods=n)
    return pd.Series(100 * np.cumprod(1 + rng.normal(0.0005, 0.01, n)), index=idx)


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    import streamlit_local_storage
    import data.downloader as dl
    import data.financials as fin
    import data.company as co
    monkeypatch.setattr(streamlit_local_storage, "LocalStorage", _FakeLS)
    monkeypatch.setattr(dl, "download_single", lambda t, period="15y": _series())
    monkeypatch.setattr(dl, "download_prices",
                        lambda ts, period="15y": pd.DataFrame({t: _series(seed=i) for i, t in enumerate(ts[:30])}))
    monkeypatch.setattr(co, "universe_prices",
                        lambda u, period="2y": pd.DataFrame({t: _series(seed=i) for i, t in enumerate(("AAPL", "CDR.WA", *u[:30]))}))
    monkeypatch.setattr(fin, "get_ratios_snapshot", lambda t: {"pe": 20.0, "fwd_pe": 18.0, "market_cap": 1e12,
                                                               "dividend_yield": 0.5, "name": "Apple Inc.",
                                                               "current_price": 100.0, "currency": "USD"})
    monkeypatch.setattr(fin, "get_analyst_recos", lambda t: {})
    import components.financials_ui as fu
    import components.company.finance as cfin
    import components.company.results as cres
    for mod in (fin, fu, cfin, cres):
        for name, val in (("get_forward_consensus", None), ("get_earnings_history", None),
                          ("fetch_earnings_trend", None), ("fetch_major_holders", None),
                          ("fetch_insider_purchases", None), ("fetch_insider_transactions", None),
                          ("fetch_insider_roster_holders", None), ("fetch_institutional_holders", None),
                          ("fetch_mutualfund_holders", None), ("fetch_quarterly_statements", None),
                          ("fetch_annual_statements", None)):
            if hasattr(mod, name):
                monkeypatch.setattr(mod, name, lambda *a, _v=val, **k: _v)
    for mod in (fu, cfin):
        if hasattr(mod, "get_ratios_snapshot"):
            monkeypatch.setattr(mod, "get_ratios_snapshot", lambda t: {"pe": 20.0, "name": "Apple Inc."})
    monkeypatch.setattr(fin, "fetch_earnings_dates", lambda t: None)
    monkeypatch.setattr(fin, "_fetch_info", lambda t: {"dividendYield": 0.02, "payoutRatio": 0.3})
    monkeypatch.setattr(co, "company_profile", lambda t: {"summary": "Opis.", "beta": 1.1, "low52": 80.0,
                                                          "high52": 120.0, "exchange": "NMS", "currency": "USD"})
    monkeypatch.setattr(co, "dividend_history", lambda t: pd.Series(dtype=float))
    monkeypatch.setattr(co, "sector_caps", lambda m, s: pd.Series({"AAPL": 1e12, "MSFT": 9e11}))


def _run(premium: bool, t: str | None):
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["premium"] = premium
    at.session_state["_auth_retries"] = 3
    if t is not None:
        at.query_params["t"] = t
    at.switch_page(PAGE).run()
    return at


def _html(at):
    return " ".join(e.proto.body for e in at.get("html"))


def test_free_shows_overview_and_five_teasers():
    at = _run(False, "AAPL")
    assert not at.exception, at.exception
    assert len(at.tabs) >= 6
    assert _html(at).count("🔒") == 5


def test_premium_renders_all_tabs():
    at = _run(True, "AAPL")
    assert not at.exception, at.exception
    assert _html(at).count("🔒") == 0
    assert not any("dane chwilowo niedostępne" in str(c.value) for c in at.caption)


def test_unknown_ticker_message():
    at = _run(False, "XXX")
    assert not at.exception
    assert any("Nie znaleziono spółki" in str(m.value) for m in [*at.markdown, *at.warning, *at.info])


def test_no_ticker_shows_search():
    at = _run(False, None)
    assert not at.exception
    assert at.selectbox(key="karta_search") is not None


def test_search_follows_ticker_change():
    at = _run(False, "AAPL")
    assert at.selectbox(key="karta_search").value == "AAPL"
    at.query_params["t"] = "MSFT"
    at.run()
    assert not at.exception
    assert at.selectbox(key="karta_search").value == "MSFT"


def test_premium_gpw_bank_renders():
    at = _run(True, "PKO.WA")
    assert not at.exception, at.exception
    assert not any("dane chwilowo niedostępne" in str(c.value) for c in at.caption)


def test_premium_beat_miss_chart_path(monkeypatch):
    import components.financials_ui as fu
    import components.company.results as cres
    baseline = len(_run(True, "AAPL").get("plotly_chart"))
    df = pd.DataFrame({"eps_estimate": [1.0, 1.1, 1.2, 1.3],
                       "eps_actual": [1.1, 1.1, 1.3, 1.4],
                       "surprise_pct": [10.0, 0.0, 8.3, 7.7]},
                      index=pd.to_datetime(["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"]))
    for mod in (fu, cres):
        monkeypatch.setattr(mod, "get_earnings_history", lambda *a, **k: df)
    at = _run(True, "AAPL")
    assert not at.exception, at.exception
    assert not any("dane chwilowo niedostępne" in str(c.value) for c in at.caption)
    assert len(at.get("plotly_chart")) > baseline


def test_premium_no_dividends_info():
    at = _run(True, "AAPL")
    assert not at.exception, at.exception
    assert any("Spółka nie wypłaca dywidendy." in str(i.value) for i in at.info)


def test_premium_dividends_tab_renders(monkeypatch):
    import data.company as co
    now = pd.Timestamp.now().normalize()
    dates = [now - pd.DateOffset(months=2) - pd.DateOffset(months=6 * k) for k in range(12)]
    monkeypatch.setattr(co, "dividend_history", lambda t: pd.Series(0.5, index=pd.DatetimeIndex(sorted(dates))))
    at = _run(True, "AAPL")
    assert not at.exception, at.exception
    assert not any("dane chwilowo niedostępne" in str(c.value) for c in at.caption)
    assert not any("Spółka nie wypłaca dywidendy." in str(i.value) for i in at.info)
    assert not any("Brak aktualnej stopy dywidendy" in str(c.value) for c in at.caption)
    assert at.number_input(key="kdv_amount").value == 10000.0
    html = _html(at)
    assert "1,00%" in html and "30,00%" in html     # yield z TTM/cena 100, payout z info
    net = co.dividend_after_tax(10000.0, 0.01, "SP500", "zwykle")["net"]
    expected = f"{net:,.2f} USD".replace(",", " ").replace(".", ",")
    assert any(m.value == expected for m in at.metric), [m.value for m in at.metric]
    assert any("USA" in str(c.value) for c in at.caption)


def test_premium_gpw_dividends_pln_belka(monkeypatch):
    import data.company as co
    now = pd.Timestamp.now().normalize()
    dates = [now - pd.DateOffset(months=2) - pd.DateOffset(months=12 * k) for k in range(6)]
    monkeypatch.setattr(co, "dividend_history", lambda t: pd.Series(2.0, index=pd.DatetimeIndex(sorted(dates))))
    monkeypatch.setattr(co, "company_profile", lambda t: {"summary": "Opis.", "beta": 1.0, "low52": 80.0,
                                                          "high52": 120.0, "exchange": "WSE", "currency": "PLN"})
    at = _run(True, "PKO.WA")
    assert not at.exception, at.exception
    assert not any("dane chwilowo niedostępne" in str(c.value) for c in at.caption)
    y = 2.0 / 100.0
    net = co.dividend_after_tax(10000.0, y, "GPW", "zwykle")
    assert net["tax"] == pytest.approx(10000.0 * y * 0.19)
    assert co.dividend_after_tax(10000.0, y, "GPW", "ike")["tax"] == 0
    fmt = lambda x: f"{x:,.2f} PLN".replace(",", " ").replace(".", ",")
    vals = [m.value for m in at.metric]
    assert fmt(net["net"]) in vals, vals
    assert any("Belki" in str(c.value) for c in at.caption)
