"""Offline regresja: strona Porownaj nie moze sypac sie na StreamlitDuplicateElementId.

Head-to-head i Side-by-side (te same tickery i okres) renderuja identyczne
wykresy w dwoch zakladkach — bez jawnych key= dostaja to samo auto-ID.
Dane sa syntetyczne (zero sieci).
"""
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from components import nav

APP = str(Path(__file__).resolve().parents[1] / "app.py")
PAGE = next(p for p in nav.PAGES if p.path.endswith("porownaj.py"))


class _FakeLocalStorage:
    def __init__(self, *a, **k):
        pass

    def getItem(self, *a, **k):
        return None

    def setItem(self, *a, **k):
        return None


def _fake_series(ticker, period="15y"):
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=600)
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
    monkeypatch.setattr(dl, "benchmark_status", lambda s, *a, **k: {"state": "ok"})


def test_h2h_and_sbs_identical_selection_no_duplicate_id():
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["premium"] = True
    at.session_state["_auth_retries"] = 3
    at.switch_page(PAGE.path).run()
    assert not at.exception, at.exception

    at.session_state["h2h_sel"] = ["SPY", "QQQ"]
    at.session_state["h2h_period"] = "2 lata"
    at.run()
    assert not at.exception, at.exception
