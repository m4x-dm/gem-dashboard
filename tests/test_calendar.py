"""Testy dla pages/22_earnings_calendar.py + watchlist + earnings calendar helpers."""
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock


def test_status_badge_today():
    from data.financials import _status_badge
    today = pd.Timestamp.now().normalize()
    assert "🔥 DZIŚ" in _status_badge(today, None, None)


def test_status_badge_future_within_week():
    from data.financials import _status_badge
    today = pd.Timestamp.now().normalize()
    date = today + pd.Timedelta(days=3)
    badge = _status_badge(date, None, None)
    assert "🔜" in badge
    assert "3d" in badge


def test_status_badge_future_2weeks():
    from data.financials import _status_badge
    today = pd.Timestamp.now().normalize()
    date = today + pd.Timedelta(days=10)
    assert "⏰" in _status_badge(date, None, None)


def test_status_badge_future_far():
    from data.financials import _status_badge
    today = pd.Timestamp.now().normalize()
    date = today + pd.Timedelta(days=25)
    badge = _status_badge(date, None, None)
    assert "📅" in badge


def test_status_badge_past_beat():
    from data.financials import _status_badge
    today = pd.Timestamp.now().normalize()
    date = today - pd.Timedelta(days=5)
    badge = _status_badge(date, 1.5, 1.4)
    assert "✅ Beat" in badge
    assert "5d temu" in badge


def test_status_badge_past_miss():
    from data.financials import _status_badge
    today = pd.Timestamp.now().normalize()
    date = today - pd.Timedelta(days=5)
    badge = _status_badge(date, 1.3, 1.4)
    assert "❌ Miss" in badge


def test_status_badge_past_no_actual():
    from data.financials import _status_badge
    today = pd.Timestamp.now().normalize()
    date = today - pd.Timedelta(days=5)
    badge = _status_badge(date, None, 1.4)
    assert "⚪" in badge


def test_detect_market_sp500():
    from data.financials import _detect_market
    assert _detect_market("AAPL") == "SP500"
    assert _detect_market("MSFT") == "SP500"


def test_detect_market_gpw():
    from data.financials import _detect_market
    assert _detect_market("PKO.WA") == "GPW"
    assert _detect_market("CDR.WA") == "GPW"


def test_detect_market_etf():
    from data.financials import _detect_market
    # ETF typowo w universe (VOO/QQQ z etf_universe.py)
    assert _detect_market("VOO") == "ETF"
    assert _detect_market("QQQ") == "ETF"


def test_get_etf_set_contains_known():
    from data.financials import _get_etf_set
    etf_set = _get_etf_set()
    assert "VOO" in etf_set
    assert "QQQ" in etf_set
    # AAPL nie powinien byc w ETF set
    assert "AAPL" not in etf_set


def test_fetch_earnings_dates_normalizes_columns():
    """Mock yfinance Ticker.earnings_dates — normalize columns."""
    mock_df = pd.DataFrame({
        "EPS Estimate": [1.5, 1.6],
        "Reported EPS": [1.65, None],
        "Surprise(%)": [10.0, None],
    }, index=pd.to_datetime(["2026-05-01", "2026-07-30"]))

    mock_ticker = MagicMock()
    mock_ticker.earnings_dates = mock_df

    from data.financials import fetch_earnings_dates
    with patch("data.financials.yf.Ticker", return_value=mock_ticker), \
         patch("data.financials._cache_path_earnings_dates", return_value=None):
        result = fetch_earnings_dates("AAPL_TEST")

    assert result is not None
    assert "eps_estimate" in result.columns
    assert "eps_actual" in result.columns
    assert "eps_surprise_pct" in result.columns
    assert "is_future" in result.columns
    assert "q_label" in result.columns


def test_fetch_earnings_dates_returns_none_on_empty():
    mock_ticker = MagicMock()
    mock_ticker.earnings_dates = pd.DataFrame()

    from data.financials import fetch_earnings_dates
    with patch("data.financials.yf.Ticker", return_value=mock_ticker), \
         patch("data.financials._cache_path_earnings_dates", return_value=None):
        result = fetch_earnings_dates("EMPTY_TEST")

    assert result is None


def test_bulk_fetch_filters_etf():
    """ETF tickery nie powinny byc fetchowane (no earnings, oszczedza calls)."""
    fetch_calls = []

    def mock_fetch(ticker, **kwargs):
        fetch_calls.append(ticker)
        return pd.DataFrame({
            "eps_estimate": [1.5],
            "eps_actual": [1.6],
            "eps_surprise_pct": [6.7],
            "is_future": [False],
            "q_label": ["Q2'26"],
        }, index=pd.to_datetime(["2026-05-01"]))

    mock_progress = MagicMock()
    mock_progress.progress = MagicMock()
    mock_progress.empty = MagicMock()

    from data.financials import bulk_fetch_earnings_calendar
    with patch("data.financials.fetch_earnings_dates", side_effect=mock_fetch), \
         patch("data.financials.st.progress", return_value=mock_progress):
        result = bulk_fetch_earnings_calendar(("AAPL", "VOO", "QQQ", "MSFT"))

    # VOO, QQQ filtered out — tylko AAPL, MSFT wywołane
    assert "VOO" not in fetch_calls
    assert "QQQ" not in fetch_calls
    assert "AAPL" in fetch_calls
    assert "MSFT" in fetch_calls
    assert set(result["ticker"].unique()).issubset({"AAPL", "MSFT"})


def test_watchlist_get_empty():
    from components.watchlist import get_watchlist
    ls_mock = MagicMock()
    ls_mock.getItem.return_value = None
    result = get_watchlist(ls_mock)
    assert result == set()


def test_watchlist_get_corrupt_json():
    from components.watchlist import get_watchlist
    ls_mock = MagicMock()
    ls_mock.getItem.return_value = "!@#invalid"
    result = get_watchlist(ls_mock)
    assert result == set()


def test_watchlist_toggle_add():
    from components.watchlist import toggle_ticker, WATCHLIST_KEY
    ls_mock = MagicMock()
    ls_mock.getItem.return_value = "[]"
    result = toggle_ticker(ls_mock, "AAPL")
    assert result is True
    ls_mock.setItem.assert_called_with(WATCHLIST_KEY, '["AAPL"]')


def test_watchlist_toggle_remove():
    from components.watchlist import toggle_ticker, WATCHLIST_KEY
    ls_mock = MagicMock()
    ls_mock.getItem.return_value = '["AAPL", "MSFT"]'
    result = toggle_ticker(ls_mock, "AAPL")
    assert result is False
    ls_mock.setItem.assert_called_with(WATCHLIST_KEY, '["MSFT"]')
