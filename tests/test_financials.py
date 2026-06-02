"""Testy modulu data/financials.py."""
import pandas as pd
import pytest
from data.financials import _quarter_label, _compute_beat_streak


def test_quarter_label_format():
    # Pierwszy kwartal 2026
    assert _quarter_label(pd.Timestamp("2026-03-31")) == "Q1'26"
    # Q2'26
    assert _quarter_label(pd.Timestamp("2026-06-30")) == "Q2'26"
    # Q3'26
    assert _quarter_label(pd.Timestamp("2026-09-30")) == "Q3'26"
    # Q4'26
    assert _quarter_label(pd.Timestamp("2026-12-31")) == "Q4'26"
    # Edge: datetime nie Timestamp
    from datetime import datetime
    assert _quarter_label(datetime(2025, 6, 30)) == "Q2'25"


def test_quarter_label_handles_nat():
    # NaT input zwraca pusty string
    assert _quarter_label(pd.NaT) == ""
    assert _quarter_label(None) == ""


def test_compute_beat_streak_simple():
    # Wszystkie kwartaly beat
    df = pd.DataFrame({
        "eps_estimate": [1.0, 1.1, 1.2, 1.3],
        "eps_actual": [1.1, 1.2, 1.3, 1.4],
    })
    assert _compute_beat_streak(df) == 4


def test_compute_beat_streak_zero():
    # Ostatni kwartal miss = streak 0
    df = pd.DataFrame({
        "eps_estimate": [1.0, 1.1, 1.2, 1.3],
        "eps_actual": [1.1, 1.2, 1.3, 1.2],  # ostatni miss
    })
    assert _compute_beat_streak(df) == 0


def test_compute_beat_streak_partial():
    # Ostatnie 2 beat, wczesniej miss
    df = pd.DataFrame({
        "eps_estimate": [1.0, 1.1, 1.2, 1.3],
        "eps_actual": [0.9, 1.0, 1.3, 1.4],  # miss, miss, beat, beat
    })
    assert _compute_beat_streak(df) == 2


def test_compute_beat_streak_empty_or_nan():
    assert _compute_beat_streak(pd.DataFrame()) == 0
    df = pd.DataFrame({"eps_estimate": [float("nan")], "eps_actual": [1.0]})
    assert _compute_beat_streak(df) == 0
