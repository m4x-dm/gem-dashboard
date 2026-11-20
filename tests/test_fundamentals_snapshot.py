"""Offline: dzienny zrzut danych fundamentalnych (zapis, odczyt, pierwszenstwo przed Yahoo)."""
import gzip
import json
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from data import fundamentals_snapshot as fs

NOW = pd.Timestamp("2026-11-20 06:00")


def _eh():
    return pd.DataFrame({"eps_estimate": [1.0, 2.0], "eps_actual": [1.1, np.nan], "surprise_pct": [10.0, np.nan]},
                        index=pd.DatetimeIndex(["2026-06-30", "2026-09-30"]))


def _ins():
    return pd.DataFrame({"Insider": ["JANE ROE"], "Position": ["CFO"], "Type": ["Sell"], "Shares": [1000],
                         "Value": [2_100_000.0]}, index=pd.DatetimeIndex(["2026-11-05"]))


def _payload(generated="2026-11-20T05:40:00Z"):
    return fs.build_payload({
        "META": {"eh": _eh(), "rd": pd.Timestamp("2026-10-21"), "nd": pd.Timestamp("2027-01-27"),
                 "ud": None, "ins": _ins()},
        "SNT.WA": {"eh": None, "rd": None, "nd": None, "ud": None, "ins": None},
    }, generated_at=pd.Timestamp(generated))


def test_roundtrip_frames_dates_and_nan():
    snap = fs.Snapshot.from_payload(json.loads(json.dumps(_payload())))
    hit, eh = snap.lookup("eh", "META")
    assert hit
    pd.testing.assert_frame_equal(eh, _eh(), check_freq=False)
    hit, ins = snap.lookup("ins", "META")
    pd.testing.assert_frame_equal(ins, _ins(), check_freq=False, check_dtype=False)
    assert snap.lookup("rd", "META") == (True, pd.Timestamp("2026-10-21"))
    assert snap.lookup("nd", "META") == (True, pd.Timestamp("2027-01-27"))


def test_covered_ticker_with_empty_field_is_a_hit_unknown_is_a_miss():
    snap = fs.Snapshot.from_payload(_payload())
    assert snap.lookup("ud", "META") == (True, None)        # w zrzucie, pole puste -> nie pytaj Yahoo
    assert snap.lookup("ins", "SNT.WA") == (True, None)
    assert snap.lookup("eh", "AAPL") == (False, None)       # spoza zrzutu -> Yahoo


def test_disabled_by_env_and_stale_snapshot_ignored(monkeypatch):
    fs.set_for_tests(_payload())
    assert fs.lookup("eh", "META") == (False, None)         # conftest: GEM_FUNDAMENTALS_SNAPSHOT=0
    monkeypatch.delenv("GEM_FUNDAMENTALS_SNAPSHOT")
    assert fs.lookup("eh", "META", now=NOW)[0] is True
    fs.set_for_tests(_payload(generated="2026-11-10T05:40:00Z"))
    assert fs.lookup("eh", "META", now=NOW) == (False, None)     # > 3 dni


def test_download_failure_is_retried_after_cooldown(monkeypatch):
    monkeypatch.delenv("GEM_FUNDAMENTALS_SNAPSHOT")
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise OSError("offline")

    monkeypatch.setattr(fs, "_download", boom)
    assert fs.snapshot(now=NOW) is None
    assert fs.snapshot(now=NOW + pd.Timedelta(minutes=1)) is None
    assert len(calls) == 1                                       # porazka pamietana 5 min
    fs.snapshot(now=NOW + pd.Timedelta(minutes=6))
    assert len(calls) == 2


def test_download_parses_gzip(monkeypatch):
    monkeypatch.delenv("GEM_FUNDAMENTALS_SNAPSHOT")
    body = gzip.compress(json.dumps(_payload()).encode())
    resp = MagicMock(status_code=200, content=body)
    resp.raise_for_status = lambda: None
    with patch("data.fundamentals_snapshot.requests.get", return_value=resp):
        snap = fs.snapshot(now=NOW)
    assert snap is not None and snap.generated_at == pd.Timestamp("2026-11-20 05:40")


def test_fetchers_prefer_snapshot_and_fall_back_to_yahoo(monkeypatch):
    from data import financials as fin
    import streamlit as st
    st.cache_data.clear()
    monkeypatch.delenv("GEM_FUNDAMENTALS_SNAPSHOT")
    fs.set_for_tests(_payload(generated=f"{pd.Timestamp.now():%Y-%m-%dT%H:%M:%SZ}"))
    with patch("data.financials.yf.Ticker", side_effect=AssertionError("Yahoo nie powinno byc pytane")):
        assert fin.fetch_insider_transactions("META")["Value"].iloc[0] == 2_100_000.0
        assert fin.fetch_upgrades_downgrades("META") is None
        assert fin.get_earnings_history("META", n_quarters=1).index[0] == pd.Timestamp("2026-09-30")
        assert fin.fetch_last_report_date("META") == pd.Timestamp("2026-10-21")
        ed = fin.fetch_earnings_dates("META")
        assert pd.Timestamp("2027-01-27") in ed.index and bool(ed.loc[pd.Timestamp("2027-01-27"), "is_future"])
    yahoo = MagicMock()
    yahoo.insider_transactions = pd.DataFrame()
    yahoo.get_insider_transactions.return_value = pd.DataFrame()
    with patch("data.financials.yf.Ticker", return_value=yahoo) as m:
        assert fin.fetch_insider_transactions("AAPL") is None   # spoza zrzutu -> Yahoo
        assert m.called
    st.cache_data.clear()
