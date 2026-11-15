"""Smoke test: kazda strona z rejestru renderuje sie przez router z Premium.

Sieciowy (yfinance/stooq) — uruchamiaj: RUN_NETWORK=1 pytest tests/test_pages_smoke.py
"""
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from components import nav

APP = str(Path(__file__).resolve().parents[1] / "app.py")

pytestmark = pytest.mark.skipif(os.environ.get("RUN_NETWORK") != "1",
                                reason="smoke test sieciowy: RUN_NETWORK=1")


class _FakeLocalStorage:
    """LocalStorage blokuje sie w AppTest (brak przegladarki) — stub."""

    def __init__(self, *a, **k):
        pass

    def getItem(self, *a, **k):
        return None

    def setItem(self, *a, **k):
        return None


@pytest.fixture(autouse=True)
def _stub_local_storage(monkeypatch):
    import streamlit_local_storage
    monkeypatch.setattr(streamlit_local_storage, "LocalStorage", _FakeLocalStorage)
    import components.financials_ui as fui
    if hasattr(fui, "LocalStorage"):
        monkeypatch.setattr(fui, "LocalStorage", _FakeLocalStorage)


@pytest.mark.parametrize("page", nav.PAGES, ids=lambda p: p.key)
def test_page_renders_with_premium(page):
    at = AppTest.from_file(APP, default_timeout=900)
    at.session_state["premium"] = True
    at.session_state["_auth_retries"] = 3
    at.switch_page(page.path).run()
    assert not at.exception, f"{page.key}: {at.exception}"
