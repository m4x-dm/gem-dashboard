"""Offline: Pulpit dla uzytkownika Free i Premium (dane syntetyczne, zero sieci)."""
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")
PULPIT = "views/start/pulpit.py"


class _FakeLocalStorage:
    def __init__(self, *a, **k):
        pass

    def getItem(self, *a, **k):
        return None

    def setItem(self, *a, **k):
        return None


def _fake_series(ticker, period="15y"):
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=1800)
    rng = np.random.default_rng(zlib.crc32(str(ticker).encode()))
    vals = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(idx))))
    return pd.Series(vals, index=idx, name=ticker)


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    import streamlit_local_storage
    monkeypatch.setattr(streamlit_local_storage, "LocalStorage", _FakeLocalStorage)
    import components.financials_ui as fui
    if hasattr(fui, "LocalStorage"):
        monkeypatch.setattr(fui, "LocalStorage", _FakeLocalStorage)

    import data.downloader as dl
    monkeypatch.setattr(dl, "download_single", _fake_series)
    monkeypatch.setattr(dl, "download_stooq", _fake_series)
    monkeypatch.setattr(
        dl, "download_prices",
        lambda tickers, period="15y": pd.DataFrame({t: _fake_series(t) for t in tickers}))
    import data.financials as fin
    monkeypatch.setattr(fin, "bulk_fetch_earnings_calendar",
                        lambda *a, **k: pd.DataFrame())


def _run(premium: bool, favorites=()):
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["_auth_retries"] = 3
    if premium:
        at.session_state["premium"] = True
    if favorites:
        at.session_state["favorites"] = set(favorites)
    at.switch_page(PULPIT).run()
    return at


def _html(at) -> str:
    return " ".join(str(e.proto.body) for e in at.get("html"))


def _md(at) -> str:
    return " ".join(m.value for m in at.markdown)


def test_free_pulpit_two_teasers_and_free_blocks():
    at = _run(False, favorites={"SPY"})
    assert not at.exception, at.exception
    assert _html(at).count("🔒") == 2
    assert "Wyniki strategii" in _md(at)
    assert "Ulubione" in _md(at)
    assert any("są w Premium" in c.value for c in at.caption)


def test_premium_pulpit_no_teasers():
    at = _run(True)
    assert not at.exception, at.exception
    assert _html(at).count("🔒") == 0
    assert "Wyniki strategii" in _md(at)
    assert "Moja watchlista" in _md(at)
