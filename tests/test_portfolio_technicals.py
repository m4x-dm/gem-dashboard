"""Offline: analiza techniczna pozycji (poziomy, zdarzenia z ostatnich 10 sesji, tabela)."""
import numpy as np
import pandas as pd
import pytest

from data.portfolio import technicals as ta


def _ohlc(close, spread=0.005, end="2026-11-20"):
    close = np.asarray(close, dtype=float)
    idx = pd.bdate_range(end=end, periods=len(close))
    return pd.DataFrame({"High": close * (1 + spread), "Low": close * (1 - spread), "Close": close}, index=idx)


def _wave(n, lo=90.0, hi=110.0, period=30):
    """Kurs oscylujacy miedzy lo a hi (wyrazne szczyty i dolki co `period` sesji)."""
    t = np.arange(n)
    return (lo + hi) / 2 + (hi - lo) / 2 * np.sin(2 * np.pi * t / period)


def test_levels_cluster_repeated_pivots_and_drop_single_touch():
    close = _wave(126)
    close[60] = 130.0                                   # jednorazowy szczyt -> nie jest poziomem
    df = _ohlc(close, spread=0.0)
    lv = ta.levels(df["High"], df["Low"])
    prices = [p for p, n in lv]
    assert any(abs(p - 110) < 1.5 for p in prices)
    assert any(abs(p - 90) < 1.5 for p in prices)
    assert all(abs(p - 130) > 5 for p in prices)
    assert all(n >= 2 for _, n in lv)


def test_snapshot_row_nearest_levels_and_indicators():
    close = np.concatenate([_wave(300), [100.0]])
    row = ta.snapshot_row(_ohlc(close, spread=0.0))
    assert row["price"] == pytest.approx(100.0)
    assert row["res"] == pytest.approx(110, abs=1.5)
    assert row["sup"] == pytest.approx(90, abs=1.5)
    assert row["sma200"] == pytest.approx(100, abs=1.0)
    assert 0 <= row["rsi"] <= 100
    assert row["from_high52"] == pytest.approx(100 / 110 - 1, abs=0.02)


def test_short_history_degrades_gracefully():
    row = ta.snapshot_row(_ohlc(np.linspace(100, 110, 60)))
    assert np.isnan(row["sma200"]) and np.isnan(row["from_high52"])
    assert ta.events("X", _ohlc(np.linspace(100, 110, 60))) is not None


def test_level_break_up_detected_without_lookahead():
    close = np.concatenate([_wave(290), np.full(7, 104.0), [116.0, 117.0, 117.5]])
    ev = [a for a in ta.events("SNT.WA", _ohlc(close, spread=0.0)) if a.kind == "tech_level"]
    assert len(ev) == 1
    a = ev[0]
    assert a.tone == "pos" and a.params["level"] == pytest.approx(110, abs=1.5)
    assert a.date == _ohlc(close).index[-3]


def test_level_created_inside_window_is_not_a_break():
    # Szczyty 120 tylko w ostatnich 10 sesjach -> poziom z danych sprzed okna go nie zna.
    close = np.concatenate([np.full(290, 100.0), [120, 105, 120, 105, 121, 106, 100, 100, 100, 100]])
    ev = [a for a in ta.events("X", _ohlc(close, spread=0.0)) if a.kind == "tech_level"]
    assert ev == []


def test_last_cross_helper():
    idx = pd.bdate_range(end="2026-11-20", periods=20)
    a = pd.Series(np.r_[np.full(15, 1.0), np.full(5, 3.0)], index=idx)
    b = pd.Series(2.0, index=idx)
    assert ta.last_cross(a, b, 10) == (idx[15], "up")
    assert ta.last_cross(b, a, 10) == (idx[15], "down")
    assert ta.last_cross(a, b, 3) is None


def test_new_52w_high_and_rsi_overbought():
    rng = np.random.default_rng(0)
    close = np.concatenate([100 + rng.normal(0, 0.5, 290), np.linspace(101, 125, 10)])
    ev = {a.kind: a for a in ta.events("META", _ohlc(close))}
    assert ev["tech_52w"].tone == "pos" and ev["tech_52w"].date == _ohlc(close).index[-1]
    assert ev["tech_rsi"].params["zone"] == "hi"
    assert "tech_sma200" not in ev or ev["tech_sma200"].tone == "pos"


def test_events_are_dated_alerts_sorted_with_fundamentals():
    from data.portfolio import alerts
    assert {"tech_level", "tech_cross", "tech_sma200", "tech_52w", "tech_rsi"} <= set(alerts.DATED_KINDS)
