"""Bramka Premium w routerze: strona platna bez Premium nie uruchamia tresci.

Offline: przy zablokowanej stronie router nie wola pg.run(), wiec strona
nie pobiera danych. Uzywamy strony bez sieciowego importu na starcie.
"""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def _html_text(at) -> str:
    # st.html w AppTest to UnknownElement; tresc jest w proto.body
    return " ".join(e.proto.body for e in at.get("html"))


def test_paid_page_shows_lock_screen_without_premium():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["premium"] = False
    at.session_state["_auth_retries"] = 3
    at.switch_page("pages/portfel/monte_carlo.py").run()
    assert not at.exception, at.exception
    html = _html_text(at)
    assert "Kup dostep Premium" in html
    assert "Monte Carlo" in html


def test_free_page_runs_without_premium():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["premium"] = False
    at.session_state["_auth_retries"] = 3
    at.switch_page("pages/strategia/o_strategii.py").run()
    assert not at.exception, at.exception
    assert "Kup dostep Premium" not in _html_text(at)
