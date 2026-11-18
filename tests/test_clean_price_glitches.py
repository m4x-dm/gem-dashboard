"""clean_price_glitches: bledne punkty cenowe Yahoo dla krypto (2026-11-18)."""
import numpy as np
import pandas as pd

from data.downloader import clean_price_glitches


def _df(vals):
    idx = pd.date_range("2026-01-01", periods=len(vals), freq="D")
    return pd.DataFrame({"X": vals}, index=idx, dtype=float)


def test_single_day_spike_removed():
    out = clean_price_glitches(_df([1, 1.02, 1.01, 6000, 1.03, 1.02, 1.04]))
    assert out["X"].max() < 2
    assert np.isfinite(out["X"].pct_change().dropna()).all()


def test_zero_price_removed():
    out = clean_price_glitches(_df([1, 1.1, 0, 1.2, 1.15]))
    assert (out["X"] > 0).all()
    assert np.isfinite(out["X"].pct_change().dropna()).all()


def test_sustained_jump_kept():
    vals = [1, 1, 1, 1, 8, 8.2, 8.1, 8.3, 8.4]
    out = clean_price_glitches(_df(vals))
    assert out["X"].iloc[-1] == 8.4
    assert out["X"].iloc[5] == 8.2


def test_leading_nan_kept_before_listing():
    out = clean_price_glitches(_df([np.nan, np.nan, 2.0, 2.1, 2.05]))
    assert out["X"].iloc[:2].isna().all()
    assert out["X"].iloc[2] == 2.0
