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


def test_portfolio_free_shows_positions_and_teaser():
    _seed()
    at = _run(False)
    assert not at.exception, at.exception
    t = _text(at)
    for s in ("SNT.PL", "META.US", "IS3N.DE", "ABC.XX", "Wartość", "Zysk / strata", "Wpłaty netto",
              "Dywidendy", "Co się dzieje"):
        assert s in t, s
    assert "🔒" in t                       # panel Premium jako zajawka
    assert "OIL.WTI" not in t              # CFD pominiete
    assert "4 346" in t                    # wartosc: 1005 + 1220 + 2021 + 100
    assert "Jak pobrać eksport z XTB" not in t


def test_portfolio_premium_panel_and_account_filter():
    _seed()
    at = _run(True)
    assert not at.exception, at.exception
    t = _text(at)
    assert "🔒" not in t
    assert "Brak raportów" in t            # fetch_earnings_dates -> None dla wszystkich
    seg = at.button_group(key="pf_account")
    assert seg.options == ["Wszystkie", "IKE", "Zwykłe"]
    seg.set_value("ZWYKLE").run()
    assert not at.exception, at.exception
    t = _text(at)
    assert "SNT.PL" not in t
    assert any("Brak otwartych pozycji" in i.value for i in at.info)


def test_position_row_opens_company_card():
    _seed()
    at = _run(False)
    btns = [b for b in at.button if str(b.key or "").startswith("pfbtn_")]
    # Karta spolki tylko dla S&P 500 / GPW: ETF (IS3N.DE) i nieznany ABC.XX bez przycisku
    assert sorted(b.key.rsplit("_", 1)[-1] for b in btns) == ["META", "SNT.WA"]
    meta = next(b for b in btns if b.key.endswith("_META"))
    meta.click().run()
    assert at.query_params.get("t") in ("META", ["META"])


def test_delete_portfolio():
    _seed()
    at = _run(False)
    at.button(key="pf_delete_confirm").click().run()
    assert not at.exception, at.exception
    assert "Jak pobrać eksport z XTB" in _text(at)
    # portfel usuniety w sesji i w localStorage (kolejny odczyt go nie wskrzesi)
    assert at.session_state["portfolio_accounts"] == {}
    assert ps.load_portfolio(_FakeLocalStorage()) == ({}, False)


def test_portfolio_renders_in_english():
    from tests.test_i18n_pages import _polish_leftovers
    _seed()
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["_auth_retries"] = 3
    at.session_state["lang"] = "en"
    at.switch_page(PAGE).run()
    assert not at.exception, at.exception
    leftovers = _polish_leftovers(at)
    assert not leftovers, "Polskie teksty w wersji EN:\n" + "\n".join(sorted(set(leftovers)))
