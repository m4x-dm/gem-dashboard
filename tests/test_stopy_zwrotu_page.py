"""Strona 6_stopy_zwrotu: kolejnosc w menu i smoke test renderowania."""

import os
from pathlib import Path

import pytest
from streamlit.source_util import page_sort_key

PAGES = Path(__file__).resolve().parents[1] / "pages"


def test_menu_order_between_info_and_sp500():
    order = [p.name for p in sorted(PAGES.glob("*.py"), key=page_sort_key)]
    i = order.index("6_stopy_zwrotu.py")
    assert order[i - 1] == "6_info.py"
    assert order[i + 1] == "7_sp500.py"


def test_sidebar_separators_shifted():
    css = (PAGES.parent / "components" / "sidebar.py").read_text(encoding="utf-8")
    for n in (9, 13, 16):
        assert f'a[data-testid="stSidebarNavLink"]:nth-child({n})' in css
    for n in (8, 12, 15):
        assert f'a[data-testid="stSidebarNavLink"]:nth-child({n})' not in css


def test_home_card_before_sp500():
    app = (PAGES.parent / "app.py").read_text(encoding="utf-8")
    assert app.index("pages/6_stopy_zwrotu.py") < app.index("pages/7_sp500.py")


@pytest.mark.skipif(os.environ.get("RUN_NETWORK") != "1", reason="smoke test sieciowy: RUN_NETWORK=1")
@pytest.mark.parametrize("proxy,ccy", [(False, "USD"), (True, "USD"), (True, "PLN")])
def test_page_renders(proxy, ccy):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(PAGES / "6_stopy_zwrotu.py"), default_timeout=300)
    at.session_state["premium"] = True
    at.run()
    assert not at.exception
    at.toggle(key="lr_proxy").set_value(proxy)
    at.radio(key="lr_ccy").set_value(ccy)
    at.run()
    assert not at.exception, at.exception
    assert len(at.tabs) == 4
    assert len(at.dataframe) >= 4
