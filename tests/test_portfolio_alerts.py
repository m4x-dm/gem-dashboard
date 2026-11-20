"""Offline: alerty fundamentalne Mojego portfela (wyniki, analitycy, insiderzy)."""
import pandas as pd
import pytest

from data.portfolio import alerts as al

TODAY = pd.Timestamp("2026-11-20")


def _earn(rows):
    df = pd.DataFrame([{"eps_estimate": 1.0, "eps_actual": 1.0, "eps_surprise_pct": s, "is_future": f,
                        "q_label": "Q3 2026"} for _, s, f in rows],
                      index=pd.DatetimeIndex([pd.Timestamp(d) for d, _, _ in rows]))
    return df


def _ud(rows):
    return pd.DataFrame([{"Firm": f, "ToGrade": to, "FromGrade": fr, "Action": a, "priceTargetAction": pt,
                          "currentPriceTarget": 100.0} for _, f, fr, to, a, pt in rows],
                        index=pd.DatetimeIndex([pd.Timestamp(d) for d, *_ in rows]))


def _ins(rows):
    return pd.DataFrame([{"Insider": n, "Position": p, "Type": t, "Shares": 10, "Value": v}
                         for _, n, p, t, v in rows],
                        index=pd.DatetimeIndex([pd.Timestamp(d) for d, *_ in rows]))


@pytest.mark.parametrize("surprise,tone", [(12.0, "pos"), (-5.0, "neg"), (1.0, "neutral")])
def test_earnings_beat_miss_inline(surprise, tone):
    out = al.earnings_alerts("META", _earn([("2026-10-28", surprise, False)]), TODAY)
    assert len(out) == 1
    a = out[0]
    assert (a.kind, a.tone, a.ticker, a.date) == ("earnings", tone, "META", pd.Timestamp("2026-10-28"))
    assert a.params["q"] == "Q3 2026"


def test_earnings_old_and_unknown_skipped_upcoming_kept():
    df = _earn([("2026-09-01", 5.0, False), ("2026-11-10", float("nan"), False),
                ("2026-11-25", float("nan"), True), ("2027-01-30", float("nan"), True)])
    out = al.earnings_alerts("NOW", df, TODAY)
    assert [a.kind for a in out] == ["upcoming"]
    assert out[0].params["days"] == 5


def test_earnings_quarter_end_index_dated_by_report_date():
    # Yahoo: indeks = koniec kwartalu (30.09), raport wyszedl 21.10 -> alert z data 21.10
    df = _earn([("2026-06-30", 3.0, False), ("2026-09-30", 8.0, False)])
    assert al.earnings_alerts("META", df, TODAY) == []           # bez daty raportu: 30.09 poza oknem
    out = al.earnings_alerts("META", df, TODAY, pd.Timestamp("2026-10-21"))
    assert [(a.date, a.params["s"]) for a in out] == [(pd.Timestamp("2026-10-21"), 8.0)]
    # data raportu wczesniejsza niz koniec kwartalu (stara) albo w przyszlosci -> ignorowana
    assert al.earnings_alerts("META", df, TODAY, pd.Timestamp("2027-01-27")) == []


def test_earnings_none():
    assert al.earnings_alerts("X", None, TODAY) == []


def test_analyst_rating_changes_and_targets_summary():
    df = _ud([
        ("2026-11-14", "Barclays", "Hold", "Buy", "up", "Raises"),
        ("2026-11-12", "UBS", "Buy", "Neutral", "down", "Lowers"),
        ("2026-11-10", "Mizuho", "", "Outperform", "init", "Announces"),
        ("2026-11-09", "JPM", "Buy", "Buy", "main", "Raises"),
        ("2026-11-08", "GS", "Buy", "Buy", "main", "Raises"),
        ("2026-09-01", "MS", "Hold", "Buy", "up", "Raises"),         # > 30 dni
    ])
    out = al.analyst_alerts("TSLA", df, TODAY)
    kinds = [(a.kind, a.tone) for a in out]
    assert kinds == [("rating", "pos"), ("rating", "neg"), ("rating", "neutral"), ("targets", "pos")]
    assert out[0].params == {"firm": "Barclays", "frm": "Hold", "to": "Buy"}
    assert out[-1].params == {"up": 3, "down": 1}
    assert out[-1].date is None


def test_analyst_no_target_changes_no_summary():
    df = _ud([("2026-11-14", "Barclays", "Buy", "Buy", "reit", "Maintains")])
    assert al.analyst_alerts("TSLA", df, TODAY) == []


def test_insider_buy_big_sell_small_sells_and_awards():
    df = _ins([
        ("2026-11-09", "JOHN DOE", "Chief Executive Officer", "Buy", 500_000.0),
        ("2026-11-05", "JANE ROE", "Chief Financial Officer", "Sell", 2_100_000.0),
        ("2026-11-04", "A B", "Director", "Sell", 300_000.0),
        ("2026-11-03", "C D", "Director", "Sell", 200_000.0),
        ("2026-11-02", "E F", "Officer", "Stock Award", 0.0),
        ("2026-08-01", "G H", "Director", "Buy", 1_000.0),          # > 30 dni
    ])
    out = al.insider_alerts("META", df, TODAY)
    assert [(a.kind, a.tone) for a in out] == [("insider_buy", "pos"), ("insider_sell", "neg"),
                                              ("insider_sells", "neg")]
    assert out[0].params["who"] == "CEO"            # skrot stanowiska
    assert out[0].params["usd"] == 500_000.0
    assert out[2].params == {"n": 2, "usd": 500_000.0}


def test_insider_missing_value_and_position():
    df = _ins([("2026-11-09", "JOHN DOE", None, "Buy", float("nan"))])
    out = al.insider_alerts("META", df, TODAY)
    assert out[0].params["who"] == "JOHN DOE"
    assert out[0].params["usd"] != out[0].params["usd"]  # NaN


def test_sort_alerts_order():
    d = pd.Timestamp
    items = [
        al.Alert(None, "X", "no_data", "neutral", "", {}),
        al.Alert(d("2026-11-25"), "A", "upcoming", "neutral", "", {"days": 5}),
        al.Alert(None, "B", "targets", "pos", "", {}),
        al.Alert(d("2026-11-01"), "C", "earnings", "pos", "", {}),
        al.Alert(d("2026-11-22"), "A2", "upcoming", "neutral", "", {"days": 2}),
        al.Alert(d("2026-11-14"), "D", "rating", "pos", "", {}),
    ]
    assert [a.ticker for a in al.sort_alerts(items)] == ["D", "C", "B", "A2", "A", "X"]


def test_collect_gpw_skips_analysts_and_handles_errors():
    calls = []

    def earn(t):
        calls.append(("e", t))
        if t == "BAD":
            raise RuntimeError("boom")
        return _earn([("2026-10-28", 10.0, False)]) if t == "META" else None

    def ud(t):
        calls.append(("u", t))
        return None

    def ins(t):
        calls.append(("i", t))
        return None

    out = al.collect(("META", "SNT.WA", "BAD"), TODAY, earn, ud, ins, lambda t: 1 / 0)
    assert ("u", "SNT.WA") not in calls and ("i", "SNT.WA") not in calls
    assert ("u", "META") in calls
    assert [a.kind for a in out] == ["earnings", "fetch_failed", "no_data"]
    assert out[1].params["tickers"] == "BAD"         # blad Yahoo (nie GPW) -> "sprobuj ponownie"
    assert out[2].params["tickers"] == "SNT.WA"


def test_collect_reports_source_status_and_fetch_failures():
    status = {}
    earn = lambda t: _earn([("2026-10-28", 10.0, False)]) if t == "META" else None
    ud = lambda t: (_ for _ in ()).throw(RuntimeError("429")) if t == "META" else None
    ins = lambda t: None
    out = al.collect(("META", "NOW", "SNT.WA"), TODAY, earn, ud, ins, status=status)
    assert status["META"] == {"earnings": "ok", "ratings": "error", "insiders": "empty"}
    assert status["SNT.WA"] == {"earnings": "empty", "ratings": "skip", "insiders": "skip"}
    kinds = {a.kind: a for a in out}
    assert kinds["fetch_failed"].params["tickers"] == "NOW"          # USA bez zadnych danych
    assert kinds["no_data"].params["tickers"] == "SNT.WA"            # GPW
    assert [a.kind for a in out][-2:] == ["fetch_failed", "no_data"]
