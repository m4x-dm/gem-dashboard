"""Testy struktury wykresow strony 6_stopy_zwrotu."""

import numpy as np
import pandas as pd

from components.charts import growth_chart, rolling_returns_chart, yearly_returns_heatmap


def _m(values, start="2000-01-31"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="ME"), dtype=float)


def test_growth_chart_log_axis_and_dashed_proxy_segment():
    series = {"SPY": _m([100, 110, 121, 133]), "GLD": _m([10, 11, 12, 13])}
    proxy_end = {"SPY": pd.Timestamp("2000-02-29"), "GLD": None}
    fig = growth_chart(series, proxy_end, start_value=10_000, currency="USD")
    assert fig.layout.yaxis.type == "log"
    names = [t.name for t in fig.data]
    assert names.count("SPY") == 2 and names.count("GLD") == 1
    dashes = {(t.name, t.line.dash) for t in fig.data}
    assert ("SPY", "dash") in dashes and ("SPY", "solid") in dashes
    gld = [t for t in fig.data if t.name == "GLD"][0]
    assert gld.y[0] == 10_000


def test_yearly_returns_heatmap_marks_ytd():
    df = pd.DataFrame({"SPY": [0.1, -0.05, 0.02], "AGG": [0.03, 0.01, np.nan]},
                      index=[2024, 2025, 2026])
    fig = yearly_returns_heatmap(df, ytd_year=2026)
    assert list(fig.data[0].y) == ["2024", "2025", "2026 YTD"]
    assert list(fig.data[0].x) == ["SPY", "AGG"]


def test_rolling_returns_chart_one_trace_per_series_plus_zero_line():
    fig = rolling_returns_chart({"SPY": _m([0.1, 0.12]), "AGG": _m([0.03, 0.02])}, years=10)
    assert len(fig.data) == 2
    assert any(s.y0 == 0 for s in fig.layout.shapes)


def test_growth_chart_polish_separators_and_axis_title():
    fig = growth_chart({"SPY": _m([100, 110])}, {"SPY": None}, currency="PLN")
    assert fig.layout.separators == ", "
    assert fig.layout.yaxis.title.text == "Wartosc (PLN)"


def test_growth_chart_proxy_end_after_series_end_keeps_only_dashed_in_legend():
    fig = growth_chart({"SPY": _m([100, 110])}, {"SPY": pd.Timestamp("2005-01-31")})
    assert len(fig.data) == 1
    assert fig.data[0].showlegend is True and fig.data[0].line.dash == "dash"


def test_yearly_returns_heatmap_empty_df_no_crash():
    fig = yearly_returns_heatmap(pd.DataFrame())
    assert len(fig.data) == 0


def test_yearly_returns_heatmap_layout_and_clipping():
    df = pd.DataFrame({"SPY": [0.1, 5.0, 0.02]}, index=[2024, 2025, 2026])
    fig = yearly_returns_heatmap(df)
    assert fig.layout.margin.t == 90 and fig.layout.separators == ", "
    assert fig.data[0].zmax == 100 and fig.data[0].zmin == -100
    assert fig.data[0].text[0][0] == "10,0%"
