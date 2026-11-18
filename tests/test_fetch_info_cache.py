"""_fetch_info: cache 24h tylko dla udanych odpowiedzi (2026-11-18).

Wczesniej porazka Yahoo (np. 429) zapisywala {} na 24h i psula wskazniki,
rekomendacje i profil spolki na cala dobe.
"""
from data import financials as fin


class _FakeTicker:
    calls = 0
    fail = True

    def __init__(self, *a, **k):
        pass

    @property
    def info(self):
        _FakeTicker.calls += 1
        if _FakeTicker.fail:
            raise RuntimeError("429 Too Many Requests")
        return {"currentPrice": 100.0, "numberOfAnalystOpinions": 12, "targetMeanPrice": 120.0}


def _setup(monkeypatch):
    fin._fetch_info_cached.clear()
    _FakeTicker.calls = 0
    _FakeTicker.fail = True
    monkeypatch.setattr(fin.yf, "Ticker", _FakeTicker)
    monkeypatch.setattr(fin, "_get_yf_session", lambda: None)
    monkeypatch.setattr(fin.time, "sleep", lambda s: None)


def test_failure_is_not_cached(monkeypatch):
    _setup(monkeypatch)
    assert fin._fetch_info("ZZZ_TEST") == {}
    assert _FakeTicker.calls == 3  # trzy proby

    _FakeTicker.fail = False  # Yahoo znow odpowiada
    info = fin._fetch_info("ZZZ_TEST")
    assert info.get("currentPrice") == 100.0
    # Dane pochodne tez od razu poprawne, bez czekania 24h
    assert fin.get_analyst_recos("ZZZ_TEST")["num_analysts"] == 12
    fin._fetch_info_cached.clear()


def test_success_is_cached(monkeypatch):
    _setup(monkeypatch)
    _FakeTicker.fail = False
    fin._fetch_info("ZZZ_TEST2")
    fin._fetch_info("ZZZ_TEST2")
    assert _FakeTicker.calls == 1
    fin._fetch_info_cached.clear()
