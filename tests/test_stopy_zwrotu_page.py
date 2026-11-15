"""Strona Stopy zwrotu (pages/etf/stopy_zwrotu.py): smoke test renderowania."""

import os
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.mark.skipif(os.environ.get("RUN_NETWORK") != "1", reason="smoke test sieciowy: RUN_NETWORK=1")
@pytest.mark.parametrize("proxy,ccy", [(False, "USD"), (True, "USD"), (True, "PLN")])
def test_page_renders(proxy, ccy):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP), default_timeout=300)
    at.session_state["premium"] = True
    at.session_state["_auth_retries"] = 3
    at.switch_page("pages/etf/stopy_zwrotu.py").run()
    assert not at.exception
    at.toggle(key="lr_proxy").set_value(proxy)
    at.radio(key="lr_ccy").set_value(ccy)
    at.run()
    assert not at.exception, at.exception
    assert len(at.tabs) == 4
    assert len(at.dataframe) >= 5  # CAGR + skumulowana + roczne + kroczace + ryzyko
    headers = [m.value for m in at.markdown]
    assert any("CAGR" in h for h in headers) and any("Skumulowana" in h for h in headers)
    assert at.selectbox(key="lr_bar_period").value is not None
