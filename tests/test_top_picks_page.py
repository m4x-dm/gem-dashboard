"""AppTest strony Top Picks: 5 zakladek, nowe strategie renderuja sie z logu."""
import json
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")
PAGE = "views/spolki/top_picks.py"


class _FakeLocalStorage:
    def __init__(self, *a, **k):
        pass

    def getItem(self, *a, **k):
        return None

    def setItem(self, *a, **k):
        return None


def _snapshot():
    pick = {"ticker": "AAPL", "group": "Tech", "score": -1.4, "entry_price": 100.0,
            "entry_date": "2026-11-14", "weight": 0.5, "name": "Apple",
            "recommendation_mean": 1.4, "num_analysts": 40, "target_mean": 130.0,
            "upside": 0.3}
    return {"2026-11-01": {"generated_at": "x", "asof": "2026-11-14",
                           "rule_version": 1, "sp500": [pick], "gpw": []}}


def test_top_picks_ma_piec_zakladek_i_renderuje_analitykow(tmp_path, monkeypatch):
    import streamlit_local_storage
    monkeypatch.setattr(streamlit_local_storage, "LocalStorage", _FakeLocalStorage)
    import data.top_picks as tp
    import data.downloader as dl
    import data.financials as fin

    paths = dict(tp.HISTORY_PATHS)
    for name in ("analyst", "upside"):
        p = tmp_path / f"{name}.json"
        p.write_text(json.dumps(_snapshot()), encoding="utf-8")
        paths[name] = p
    monkeypatch.setattr(tp, "HISTORY_PATHS", paths)
    idx = pd.bdate_range(end="2026-11-14", periods=260)
    monkeypatch.setattr(dl, "download_prices",
                        lambda tickers, period="1y": pd.DataFrame(
                            {t: range(100, 100 + len(idx)) for t in tickers}, index=idx))
    monkeypatch.setattr(dl, "download_stooq", lambda *a, **k: None)
    monkeypatch.setattr(fin, "bulk_fetch_universe", lambda tickers: {})

    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["_auth_retries"] = 3
    at.session_state["premium"] = True
    at.switch_page(PAGE).run()

    assert not at.exception, at.exception
    labels = [t.label for t in at.tabs]
    assert any("analitykow" in l for l in labels)
    assert any("docelowej" in l for l in labels)
    html = " ".join(str(e.proto.body) for e in at.get("html"))
    assert "Strong Buy" in html
    assert "40 analitykow" in html
