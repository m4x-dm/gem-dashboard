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
    monkeypatch.setattr(fin, "fetch_earnings_dates", lambda t: None)
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
