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


from unittest.mock import patch, MagicMock


def test_fetch_quarterly_statements_returns_dict_with_3_keys():
    """Mock yfinance Ticker, zwracamy DataFrame dla kazdego statement."""
    mock_is = pd.DataFrame({"AAPL Q1": [100, 50]}, index=["Revenue", "Net Income"])
    mock_bs = pd.DataFrame({"AAPL Q1": [1000, 500]}, index=["Total Assets", "Total Equity"])
    mock_cf = pd.DataFrame({"AAPL Q1": [80, -10]}, index=["Operating CF", "CapEx"])

    mock_ticker = MagicMock()
    mock_ticker.quarterly_income_stmt = mock_is
    mock_ticker.quarterly_balance_sheet = mock_bs
    mock_ticker.quarterly_cashflow = mock_cf

    from data.financials import fetch_quarterly_statements
    # Cache lookup miss -> fetch from yfinance
    with patch("data.financials.yf.Ticker", return_value=mock_ticker), \
         patch("data.financials._cache_path_q", return_value=None):
        result = fetch_quarterly_statements("AAPL_TEST")

    assert isinstance(result, dict)
    assert set(result.keys()) == {"income_stmt", "balance_sheet", "cashflow"}
    assert "Revenue" in result["income_stmt"].index


def test_fetch_quarterly_statements_returns_none_on_empty():
    mock_ticker = MagicMock()
    mock_ticker.quarterly_income_stmt = pd.DataFrame()
    mock_ticker.quarterly_balance_sheet = pd.DataFrame()
    mock_ticker.quarterly_cashflow = pd.DataFrame()

    from data.financials import fetch_quarterly_statements
    with patch("data.financials.yf.Ticker", return_value=mock_ticker), \
         patch("data.financials._cache_path_q", return_value=None):
        result = fetch_quarterly_statements("EMPTY_TEST")

    assert result is None


def test_fetch_earnings_trend_returns_df_with_required_columns():
    """Mock eps_trend + earnings_estimate + revenue_estimate od yfinance."""
    mock_trend = pd.DataFrame({
        "current": [1.50, 1.65, 6.80, 7.40],
        "7daysAgo": [1.49, 1.64, 6.78, 7.38],
        "30daysAgo": [1.45, 1.60, 6.75, 7.30],
        "60daysAgo": [1.40, 1.55, 6.70, 7.20],
        "90daysAgo": [1.35, 1.50, 6.65, 7.10],
    }, index=["0q", "+1q", "0y", "+1y"])
    mock_estimate = pd.DataFrame({
        "avg": [1.50, 1.65, 6.80, 7.40],
        "growth": [0.08, 0.10, 0.12, 0.09],
    }, index=["0q", "+1q", "0y", "+1y"])
    mock_rev_est = pd.DataFrame({
        "avg": [95.4e9, 100e9, 410e9, 440e9],
    }, index=["0q", "+1q", "0y", "+1y"])

    mock_ticker = MagicMock()
    mock_ticker.eps_trend = mock_trend
    mock_ticker.earnings_estimate = mock_estimate
    mock_ticker.revenue_estimate = mock_rev_est

    from data.financials import fetch_earnings_trend
    with patch("data.financials.yf.Ticker", return_value=mock_ticker):
        result = fetch_earnings_trend("AAPL_TEST")

    assert result is not None
    assert "eps_current" in result.columns
    assert "eps_30d_ago" in result.columns
    assert "eps_growth_yoy" in result.columns
    assert "rev_estimate" in result.columns
    assert "revision_pct" in result.columns
    assert len(result) == 4  # 0q, +1q, 0y, +1y


def test_normalize_transaction_type_sale_variants():
    from data.financials import _normalize_transaction_type
    assert _normalize_transaction_type("Sale") == "Sell"
    assert _normalize_transaction_type("Sale (Non Open Market)") == "Sell"
    assert _normalize_transaction_type("Sale at Public Offering") == "Sell"
    assert _normalize_transaction_type("Sell") == "Sell"


def test_normalize_transaction_type_purchase():
    from data.financials import _normalize_transaction_type
    assert _normalize_transaction_type("Purchase") == "Buy"
    assert _normalize_transaction_type("Buy") == "Buy"
    assert _normalize_transaction_type("Purchase (Open Market)") == "Buy"


def test_normalize_transaction_type_other_kept():
    from data.financials import _normalize_transaction_type
    assert _normalize_transaction_type("Exercise of Options") == "Exercise of Options"
    assert _normalize_transaction_type("Conversion") == "Conversion"
    assert _normalize_transaction_type("Other (Acquisition)") == "Other"


def test_bulk_fetch_earnings_history_returns_dataframe_with_required_columns():
    """Mock get_earnings_history dla 3 tickerow.

    Test pokrywa:
    - kolumny output DF (ticker, last_q_label, eps_estimate/actual,
      eps_surprise_pct, beat_streak)
    - beat_streak liczone z mock data (BEAT=4, MISS=0)
    - NaN row dla tickera bez danych (EMPTY)
    """
    def mock_earnings_history(ticker, n_quarters=8):
        if ticker == "EMPTY":
            return None
        return pd.DataFrame({
            "eps_estimate": [1.0, 1.1, 1.2, 1.3],
            "eps_actual": [1.1, 1.2, 1.3, 1.4 if ticker == "BEAT" else 1.2],
            "surprise_pct": [10.0, 9.1, 8.3, 7.7 if ticker == "BEAT" else -7.7],
        }, index=pd.to_datetime(["2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30"]))

    # st.progress mock — nie chcemy bombic w testach
    mock_progress = MagicMock()
    mock_progress.progress = MagicMock()
    mock_progress.empty = MagicMock()

    from data.financials import bulk_fetch_earnings_history
    with patch("data.financials.get_earnings_history", side_effect=mock_earnings_history), \
         patch("data.financials.st.progress", return_value=mock_progress):
        result = bulk_fetch_earnings_history(("BEAT", "MISS", "EMPTY"))

    assert isinstance(result, pd.DataFrame)
    expected_cols = {
        "ticker", "last_q_label", "eps_estimate", "eps_actual",
        "eps_surprise_pct", "beat_streak",
    }
    assert expected_cols.issubset(set(result.columns))
    # BEAT i MISS w wynikach (EMPTY moze byc NaN row)
    assert "BEAT" in result["ticker"].values
    # BEAT ma streak 4 (wszystkie 4 kwartaly beat)
    beat_row = result[result["ticker"] == "BEAT"].iloc[0]
    assert beat_row["beat_streak"] == 4
    # MISS ma streak 0 (ostatni kwartal miss)
    miss_row = result[result["ticker"] == "MISS"].iloc[0]
    assert miss_row["beat_streak"] == 0
