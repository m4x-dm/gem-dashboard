"""Offline: strony Premium po angielsku — bez wyjatkow i bez polskich napisow.

Karta spolki: kazda z 6 sekcji dla spolki z S&P 500 i z GPW (dane podstawione z
test_karta_offline — przewaznie puste stany, wiec sprawdzamy tez komunikaty o braku danych).
"""
import pytest
from streamlit.testing.v1 import AppTest

from tests.test_i18n_pages import _polish_leftovers
from tests.test_karta_offline import APP, PAGE as KARTA, SECTIONS, _offline  # noqa: F401  (autouse fixture)


def _run_karta(ticker: str, tab: str | None, premium: bool = True):
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["premium"] = premium
    at.session_state["_auth_retries"] = 3
    at.session_state["lang"] = "en"
    at.query_params["t"] = ticker
    if tab:
        at.query_params["tab"] = tab
    at.switch_page(KARTA).run()
    return at


@pytest.mark.parametrize("tab", list(SECTIONS.values()))
@pytest.mark.parametrize("ticker", ["AAPL", "CDR.WA"])
def test_karta_sections_in_english(ticker, tab):
    at = _run_karta(ticker, tab)
    assert not at.exception, at.exception
    leftovers = _polish_leftovers(at)
    assert not leftovers, "Polskie teksty w wersji EN:\n" + "\n".join(sorted(set(leftovers)))


@pytest.mark.parametrize("tab", ["finanse", "dywidendy"])
def test_karta_teasers_in_english_for_free_user(tab):
    at = _run_karta("AAPL", tab, premium=False)
    assert not at.exception, at.exception
    assert not _polish_leftovers(at)
    assert "Unlock Premium" in [b.proto.label for b in at.get("link_button")]


# --- Wszystkie strony Premium (dane syntetyczne z test_pulpit_offline + puste dane fundamentalne) ---

import pandas as pd  # noqa: E402

from components import nav  # noqa: E402
from tests import test_pulpit_offline as _pulpit  # noqa: E402

PREMIUM_PAGES = [p.path for p in nav.PAGES if not p.free and p.key != "karta"]


@pytest.fixture
def _offline_prices(monkeypatch):
    import streamlit_local_storage
    import data.downloader as dl
    import data.financials as fin
    monkeypatch.setattr(streamlit_local_storage, "LocalStorage", _pulpit._FakeLocalStorage)
    monkeypatch.setattr(dl, "download_single", _pulpit._fake_series)
    monkeypatch.setattr(dl, "download_stooq", _pulpit._fake_series)
    monkeypatch.setattr(dl, "download_prices",
                        lambda tickers, period="15y": pd.DataFrame({t: _pulpit._fake_series(t) for t in tickers}))
    monkeypatch.setattr(fin, "bulk_fetch_earnings_calendar", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(fin, "bulk_fetch_universe", lambda *a, **k: {})
    for name in ("bulk_fetch_earnings_history", "bulk_fetch_insiders"):
        if hasattr(fin, name):
            monkeypatch.setattr(fin, name, lambda *a, **k: pd.DataFrame())


@pytest.mark.parametrize("path", PREMIUM_PAGES)
def test_premium_pages_in_english(path, _offline_prices):
    at = AppTest.from_file(APP, default_timeout=240)
    at.session_state["premium"] = True
    at.session_state["_auth_retries"] = 3
    at.session_state["lang"] = "en"
    at.switch_page(path).run()
    assert not at.exception, at.exception
    leftovers = _polish_leftovers(at)
    assert not leftovers, "Polskie teksty w wersji EN:\n" + "\n".join(sorted(set(leftovers)))
