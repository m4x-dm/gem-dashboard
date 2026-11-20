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
    monkeypatch.setattr(fin, "fetch_upgrades_downgrades", lambda t: None)
    monkeypatch.setattr(fin, "fetch_insider_transactions", lambda t: None)
    monkeypatch.setattr(fin, "fetch_last_report_date", lambda t: None)
    from data.portfolio import technicals
    monkeypatch.setattr(technicals, "fetch_ohlc", lambda tickers, period="2y": {})
    from data.portfolio import news as _news_mod
    monkeypatch.setattr(_news_mod, "collect", lambda rows, today, **k: ([], {}))
    import streamlit as st
    st.cache_data.clear()                   # _alerts / _history_prices z poprzednich testow
    from data.portfolio import history
    monkeypatch.setattr(history, "fetch_history", _fake_history)


def _fake_history(tickers, start):
    idx = pd.bdate_range(start, pd.Timestamp.now().normalize())
    level = {"SNT.WA": 330.0, "META": 600.0, "IS3N.DE": 46.0, "USDPLN=X": 4.0, "EURPLN=X": 4.3,
             "ETFBW20TR.WA": 80.0, "ETFBM40TR.WA": 120.0, "SPY": 500.0, "QQQ": 450.0}
    import numpy as np
    ramp = np.linspace(0.9, 1.0, len(idx))
    return pd.DataFrame({t: level[t] * ramp for t in tickers if t in level}, index=idx)


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
    # wykres wartosc vs wplaty darmowy, porownanie z indeksami jako zajawka
    assert "Wartość i wpłaty" in t
    keys = [c.proto.id for c in at.get("plotly_chart")]
    assert len(keys) == 2                   # wartosc vs wplaty + donut struktury
    assert "Twój portfel vs WIG20" in t


def test_premium_benchmark_comparison():
    _seed()
    at = _run(True)
    assert not at.exception, at.exception
    t = _text(at)
    assert "Porównanie z indeksami" in t
    assert len(at.get("plotly_chart")) == 3
    for name in ("WIG20", "mWIG40", "S&amp;P 500", "Nasdaq 100"):
        assert name in t or name.replace("&amp;", "&") in t, name


def test_history_download_failure_degrades():
    from data.portfolio import history
    import pytest as _pt
    mp = _pt.MonkeyPatch()
    mp.setattr(history, "fetch_history", lambda tickers, start: pd.DataFrame())
    import streamlit as st
    st.cache_data.clear()                   # _history_prices z poprzednich testow
    try:
        _seed()
        at = _run(False)
        assert not at.exception, at.exception
        assert any("Nie udało się pobrać historii" in i.value for i in at.info)
    finally:
        mp.undo()
        st.cache_data.clear()


def test_portfolio_premium_panel_and_account_filter():
    _seed()
    at = _run(True)
    assert not at.exception, at.exception
    t = _text(at)
    assert "🔒" not in t
    assert "Yahoo nie zwrócił danych: META" in t    # USA bez danych = porazka pobrania
    assert "brak danych Yahoo: SNT.WA" in t           # GPW
    assert "Źródła danych" in [e.label for e in at.expander]
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


def _fake_alert_sources(monkeypatch):
    import data.financials as fin
    today = pd.Timestamp.now().normalize()
    earn = pd.DataFrame({"eps_estimate": [1.0, 1.1], "eps_actual": [1.12, float("nan")],
                         "eps_surprise_pct": [12.0, float("nan")], "is_future": [False, True],
                         "q_label": ["Q3 2026", "Q4 2026"]},
                        index=[today - pd.Timedelta(days=5), today + pd.Timedelta(days=3)])
    ud = pd.DataFrame({"Firm": ["Barclays", "JPM"], "ToGrade": ["Buy", "Buy"], "FromGrade": ["Hold", "Buy"],
                       "Action": ["up", "main"], "priceTargetAction": ["Raises", "Raises"],
                       "currentPriceTarget": [800.0, 820.0]},
                      index=[today - pd.Timedelta(days=2), today - pd.Timedelta(days=4)])
    ins = pd.DataFrame({"Insider": ["JANE ROE"], "Position": ["Chief Financial Officer"], "Type": ["Sell"],
                        "Shares": [1000], "Value": [2_100_000.0]}, index=[today - pd.Timedelta(days=1)])
    monkeypatch.setattr(fin, "fetch_earnings_dates", lambda t: earn if t == "META" else None)
    monkeypatch.setattr(fin, "fetch_upgrades_downgrades", lambda t: ud if t == "META" else None)
    monkeypatch.setattr(fin, "fetch_insider_transactions", lambda t: ins if t == "META" else None)


def test_premium_alerts_panel(monkeypatch):
    _fake_alert_sources(monkeypatch)
    _seed()
    at = _run(True)
    assert not at.exception, at.exception
    t = _text(at)
    for s in ("wynik Q3 2026: EPS +12,0% vs konsensus", "Barclays: Hold → Buy", "ceny docelowe: 2↑ 0↓",
              "sprzedaż akcji przez insidera: CFO · 2,1 mln USD", "raport kwartalny", "za 3 dni",
              "brak danych Yahoo: SNT.WA"):
        assert s in t, s
    assert t.index("CFO") < t.index("Barclays") < t.index("wynik Q3")   # najnowsze pierwsze


def test_premium_alerts_and_charts_in_english(monkeypatch):
    from tests.test_i18n_pages import _polish_leftovers
    _fake_alert_sources(monkeypatch)
    _seed()
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["_auth_retries"] = 3
    at.session_state["lang"] = "en"
    at.session_state["premium"] = True
    at.switch_page(PAGE).run()
    assert not at.exception, at.exception
    leftovers = _polish_leftovers(at)
    assert not leftovers, "Polskie teksty w wersji EN: " + " | ".join(sorted(set(leftovers)))
    t = _text(at)
    assert "Comparison with indices" in t
    assert "Barclays: Hold → Buy" in t


def test_alerts_panel_uses_daily_snapshot(monkeypatch):
    """Na Streamlit Cloud Yahoo blokuje quoteSummary — panel bierze dane z dziennego zrzutu."""
    from data import fundamentals_snapshot as fs
    import data.financials as fin
    import importlib
    importlib.reload(fin)          # prawdziwe fetchery (fixture podmienia je na None)
    monkeypatch.delenv("GEM_FUNDAMENTALS_SNAPSHOT")
    today = pd.Timestamp.now().normalize()
    ins = pd.DataFrame({"Insider": ["JANE ROE"], "Position": ["Chief Financial Officer"], "Type": ["Sell"],
                        "Shares": [1000], "Value": [2_100_000.0]}, index=[today - pd.Timedelta(days=1)])
    fs.set_for_tests(fs.build_payload({"META": {"ins": ins}, "SNT.WA": {}},
                                      generated_at=pd.Timestamp.now(tz="UTC")))
    _seed()
    at = _run(True)
    assert not at.exception, at.exception
    t = _text(at)
    assert "sprzedaż akcji przez insidera: CFO · 2,1 mln USD" in t
    assert "Dane fundamentalne z dziennego zrzutu" in t
    importlib.reload(fin)



def _fake_ohlc(tickers, period="2y"):
    """META: oscylacja 590-650, potem spadek pod wsparcie ~590 w ostatnich sesjach."""
    import numpy as np
    n = 300
    idx = pd.bdate_range(end=pd.Timestamp.now().normalize(), periods=n)
    t_ = np.arange(n)
    close = 620 + 30 * np.sin(2 * np.pi * t_ / 30)
    close[-10:-3] = 600.0
    close[-3:] = [575.0, 572.0, 570.0]
    df = pd.DataFrame({"High": close, "Low": close, "Close": close}, index=idx)
    return {t: df for t in tickers if t == "META"}


def test_premium_technika_table_and_alerts(monkeypatch):
    from data.portfolio import technicals
    monkeypatch.setattr(technicals, "fetch_ohlc", _fake_ohlc)
    _seed()
    at = _run(True)
    assert not at.exception, at.exception
    t = _text(at)
    for s in ("Analiza techniczna", "Opór", "Wsparcie", "SMA200", "Od 52-tyg. max", "przebite wsparcie"):
        assert s in t, s
    assert at.button_group(key="pf_ta_ticker").options == ["META.US"]   # etykiety jak w pozycjach
    at.button_group(key="pf_ta_period").set_value("1R").run()
    assert not at.exception, at.exception


def test_free_technika_teaser():
    _seed()
    at = _run(False)
    assert not at.exception, at.exception
    assert "Poziomy techniczne Twoich spółek" in _text(at)


def test_technika_in_english(monkeypatch):
    from tests.test_i18n_pages import _polish_leftovers
    from data.portfolio import technicals
    monkeypatch.setattr(technicals, "fetch_ohlc", _fake_ohlc)
    _seed()
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["_auth_retries"] = 3
    at.session_state["lang"] = "en"
    at.session_state["premium"] = True
    at.switch_page(PAGE).run()
    assert not at.exception, at.exception
    leftovers = _polish_leftovers(at)
    assert not leftovers, "Polskie teksty w wersji EN: " + " | ".join(sorted(set(leftovers)))
    t = _text(at)
    assert "Technical analysis" in t and "support" in t


def test_long_alert_list_is_collapsed(monkeypatch):
    from data.portfolio import alerts as al
    import importlib, sys
    page = sys.modules.get("views.portfel.moj_portfel")
    many = [al.Alert(pd.Timestamp.now().normalize() - pd.Timedelta(days=i % 20), "META", "rating", "pos",
                     "{firm}: {frm} → {to}", {"firm": f"F{i}", "frm": "Hold", "to": "Buy"}) for i in range(20)]
    import data.portfolio.alerts as mod
    monkeypatch.setattr(mod, "collect", lambda *a, **k: list(many))
    _seed()
    at = _run(True)
    assert not at.exception, at.exception
    assert any(e.label == "Pokaż wszystkie (20)" for e in at.expander)



def _fake_news(rows, today, **k):
    from data.portfolio import news as n
    now = pd.Timestamp.now().normalize()
    items = [n.NewsItem(now - pd.Timedelta(days=1), "SNT.WA", "Synektik z rekordowymi wynikami", "https://a/1",
                        "Bankier.pl"),
             n.NewsItem(now - pd.Timedelta(days=2), "SNT.WA", "Wyniki finansowe QSr 4/2025", "https://a/2", "ESPI",
                        "espi"),
             n.NewsItem(now - pd.Timedelta(days=1), "META", "Meta rallies", "https://a/3", "Barrons.com")]
    return items, {"SNT.WA": {"google": "ok", "espi": "ok"}, "META": {"yahoo": "error"}}


def test_premium_news_section_and_filter(monkeypatch):
    from data.portfolio import news as n
    monkeypatch.setattr(n, "collect", _fake_news)
    _seed()
    at = _run(True)
    assert not at.exception, at.exception
    t = _text(at)
    for s in ("Newsy", "Synektik z rekordowymi wynikami", "ESPI", "Meta rallies", 'target="_blank"'):
        assert s in t, s
    assert "Źródła newsów" in [e.label for e in at.expander]
    at.button_group(key="pf_news_ticker").set_value("META").run()
    t = _text(at)
    assert "Meta rallies" in t and "Synektik z rekordowymi wynikami" not in t


def test_free_news_teaser():
    _seed()
    at = _run(False)
    assert not at.exception, at.exception
    assert "Newsy o Twoich spółkach" in _text(at)


def test_news_in_english(monkeypatch):
    from tests.test_i18n_pages import _polish_leftovers
    from data.portfolio import news as n
    monkeypatch.setattr(n, "collect", _fake_news)
    _seed()
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["_auth_retries"] = 3
    at.session_state["lang"] = "en"
    at.session_state["premium"] = True
    at.switch_page(PAGE).run()
    assert not at.exception, at.exception
    leftovers = [s for s in _polish_leftovers(at) if "Synektik" not in s and "Wyniki finansowe" not in s]
    assert not leftovers, "Polskie teksty w wersji EN: " + " | ".join(sorted(set(leftovers)))
    assert "#### News" in " ".join(m.value for m in at.markdown) or "News" in _text(at)
