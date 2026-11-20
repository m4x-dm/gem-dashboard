"""Offline: skrypt dziennego zrzutu (zbieranie, prog pokrycia, zapis)."""
import gzip
import json
import types

import pandas as pd

from data import fundamentals_snapshot as fs
from scripts import update_fundamentals as uf

TODAY = pd.Timestamp("2026-11-20")


def _fake_fin(blocked=False):
    eh = pd.DataFrame({"eps_estimate": [1.0], "eps_actual": [1.2], "surprise_pct": [20.0]},
                      index=pd.DatetimeIndex(["2026-09-30"]))
    ud = pd.DataFrame({"Firm": ["A", "B"], "ToGrade": ["Buy", "Buy"], "FromGrade": ["Hold", "Buy"],
                       "Action": ["up", "main"], "priceTargetAction": ["Raises", "Raises"],
                       "currentPriceTarget": [1.0, 2.0]},
                      index=pd.DatetimeIndex(["2026-11-10", "2026-01-10"]))
    calls = []

    def rec(name, value):
        def f(t, *a, **k):
            calls.append((name, t))
            return None if blocked else value
        return f

    fin = types.SimpleNamespace(
        get_earnings_history=rec("eh", eh),
        _fetch_info=lambda t: {} if blocked else {
            "earningsTimestamp": int(pd.Timestamp("2026-10-21").timestamp()),
            "earningsTimestampStart": int(pd.Timestamp("2027-01-27").timestamp())},
        fetch_upgrades_downgrades=rec("ud", ud),
        fetch_insider_transactions=rec("ins", None),
    )
    return fin, calls


def test_fetch_one_trims_ratings_and_skips_gpw_sources():
    fin, calls = _fake_fin()
    r = uf.fetch_one("META", fin, TODAY)
    assert r["rd"] == pd.Timestamp("2026-10-21") and r["nd"] == pd.Timestamp("2027-01-27")
    assert list(r["ud"]["Firm"]) == ["A"]                      # tylko 90 dni
    g = uf.fetch_one("SNT.WA", fin, TODAY)
    assert ("ud", "SNT.WA") not in calls and ("ins", "SNT.WA") not in calls
    assert g["ud"] is None and g["eh"] is not None


def test_future_report_timestamp_moves_to_next():
    fin, _ = _fake_fin()
    fin._fetch_info = lambda t: {"earningsTimestamp": int(pd.Timestamp("2026-11-25").timestamp())}
    r = uf.fetch_one("XTB.WA", fin, TODAY)
    assert r["rd"] is None and r["nd"] == pd.Timestamp("2026-11-25")


def test_main_rejects_low_coverage_and_writes_readable_file(tmp_path, monkeypatch):
    out = tmp_path / "f.json.gz"
    monkeypatch.setattr(uf, "get_sp500_universe", lambda: ["META", "AAPL"])
    monkeypatch.setattr(uf, "get_gpw_universe", lambda: ["SNT.WA"])
    monkeypatch.setattr(uf, "EXTRA_TICKERS", ("ASML.AS",))
    import data.financials as real_fin
    blocked, _ = _fake_fin(blocked=True)
    for k, v in vars(blocked).items():
        monkeypatch.setattr(real_fin, k, v)
    monkeypatch.setattr(uf.time, "sleep", lambda s: None)
    monkeypatch.setattr(uf, "espi_frame", lambda t: None)        # bez sieci (Bankier)
    assert uf.main(["--out", str(out)]) == 1 and not out.exists()
    ok, _ = _fake_fin()
    for k, v in vars(ok).items():
        monkeypatch.setattr(real_fin, k, v)
    assert uf.main(["--out", str(out)]) == 0
    snap = fs.Snapshot.from_payload(json.loads(gzip.decompress(out.read_bytes())))
    assert set(snap._t) == {"META", "AAPL", "SNT.WA", "ASML.AS"}
    assert snap.lookup("eh", "AAPL")[1]["surprise_pct"].iloc[0] == 20.0


def test_collect_retries_missing_fields_after_pause():
    fin, _ = _fake_fin()
    state = {"n": 0}
    real_eh = fin.get_earnings_history

    def flaky_eh(t, *a, **k):          # pierwsza proba dla TSLA: limit Yahoo
        if t == "TSLA" and state["n"] == 0:
            state["n"] += 1
            return None
        return real_eh(t, *a, **k)

    fin.get_earnings_history = flaky_eh
    sleeps = []
    per = uf.collect(["META", "TSLA"], fin, TODAY, retries=((60, 2), (120, 1)), sleep=sleeps.append)
    assert per["TSLA"]["eh"] is not None
    assert sleeps == [60, 60] or sleeps[0] == 60         # co najmniej jedna powtorka
    assert uf.missing("SNT.WA", {"eh": None, "ud": None, "ins": None}) == ["eh"]


def test_main_omits_companies_without_any_data(tmp_path, monkeypatch):
    out = tmp_path / "f.json.gz"
    monkeypatch.setattr(uf, "get_sp500_universe", lambda: ["META", "AAPL"])
    monkeypatch.setattr(uf, "get_gpw_universe", lambda: ["SNT.WA"])
    monkeypatch.setattr(uf, "EXTRA_TICKERS", ())
    monkeypatch.setattr(uf.time, "sleep", lambda s: None)
    monkeypatch.setattr(uf, "espi_frame", lambda t: None)        # bez sieci (Bankier)
    import data.financials as real_fin
    ok, _ = _fake_fin()
    for k, v in vars(ok).items():
        monkeypatch.setattr(real_fin, k, v)
    base_eh, base_info = ok.get_earnings_history, ok._fetch_info
    monkeypatch.setattr(real_fin, "get_earnings_history", lambda t, *a, **k: None if t == "SNT.WA" else base_eh(t))
    monkeypatch.setattr(real_fin, "_fetch_info", lambda t: {} if t == "SNT.WA" else base_info(t))
    assert uf.main(["--out", str(out)]) == 0
    snap = fs.Snapshot.from_payload(json.loads(gzip.decompress(out.read_bytes())))
    assert "SNT.WA" not in snap._t and {"META", "AAPL"} <= set(snap._t)



def test_fetch_one_collects_espi_only_for_gpw():
    fin, _ = _fake_fin()
    frame = pd.DataFrame({"title": ["Raport"], "link": ["l"]}, index=pd.DatetimeIndex(["2026-11-18"]))
    asked = []

    def espi(t):
        asked.append(t)
        return frame

    assert uf.fetch_one("SNT.WA", fin, TODAY, espi)["espi"] is frame
    assert uf.fetch_one("META", fin, TODAY, espi)["espi"] is None
    assert asked == ["SNT.WA"]
