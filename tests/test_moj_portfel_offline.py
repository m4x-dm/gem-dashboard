"""Offline: strona Moj portfel (Free / Premium, pusta / z portfelem) — zero sieci."""
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from components import portfolio_storage as ps
from data.portfolio.xtb_parser import parse_xtb_xlsx
from tests.xtb_fixtures import make_ike_xlsx, make_zwykle_xlsx

APP = str(Path(__file__).resolve().parents[1] / "app.py")
PAGE = "views/portfel/moj_portfel.py"
STORED: dict[str, str] = {}


class _FakeLocalStorage:
    def __init__(self, *a, **k):
        pass

    def getItem(self, itemKey, *a, **k):
        return STORED.get(itemKey)

    def setItem(self, itemKey=None, itemValue=None, key=None):
        STORED[itemKey] = itemValue


def _fake_quotes(tickers):
    base = {"SNT.WA": (335.0, 330.0), "META": (610.0, 600.0), "IS3N.DE": (47.0, 46.0),
            "USDPLN=X": (4.0, 4.0), "EURPLN=X": (4.3, 4.3)}
    rows = {t: base[t] for t in tickers if t in base}
    return pd.DataFrame.from_dict(rows, orient="index", columns=["last", "prev"])


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    STORED.clear()
    import streamlit_local_storage
    monkeypatch.setattr(streamlit_local_storage, "LocalStorage", _FakeLocalStorage)
    import components.financials_ui as fui
    if hasattr(fui, "LocalStorage"):
        monkeypatch.setattr(fui, "LocalStorage", _FakeLocalStorage)
    from data.portfolio import valuation
    monkeypatch.setattr(valuation, "fetch_live_prices", _fake_quotes)
    import data.financials as fin
    monkeypatch.setattr(fin, "fetch_earnings_dates", lambda t: None)


def _seed():
    ike, zw = parse_xtb_xlsx(make_ike_xlsx()), parse_xtb_xlsx(make_zwykle_xlsx())
    ps.save_portfolio(_FakeLocalStorage(), {ike.account_id: ike, zw.account_id: zw})


def _run(premium: bool):
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["_auth_retries"] = 3
    if premium:
        at.session_state["premium"] = True
    at.switch_page(PAGE).run()
    return at


def _text(at) -> str:
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption]
    parts += [str(e.proto.body) for e in at.get("html")]
    return " ".join(parts)


def test_empty_state_free():
    at = _run(False)
    assert not at.exception, at.exception
    t = _text(at)
    assert "Mój portfel" in t
    assert "Jak pobrać eksport z XTB" in t
