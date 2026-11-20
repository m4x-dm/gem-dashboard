"""Offline: wykres analizy technicznej spolki (swiece, SMA, poziomy, zdarzenia, RSI)."""
import numpy as np
import pandas as pd

from components.charts import technical_chart
from data.portfolio import technicals as ta


def _ohlc(n=300):
    idx = pd.bdate_range(end="2026-11-20", periods=n)
    t = np.arange(n)
    close = 100 + 10 * np.sin(2 * np.pi * t / 30)
    return pd.DataFrame({"Open": close - 0.5, "High": close + 1, "Low": close - 1, "Close": close}, index=idx)


def test_chart_frame_has_indicators_from_full_history():
    f = ta.chart_frame(_ohlc(400), sessions=126)   # 400 >= 200 + 126
    assert len(f) == 126
    assert {"Open", "High", "Low", "Close", "SMA50", "SMA200", "RSI"} <= set(f.columns)
    assert f["SMA200"].notna().all()          # liczone z pelnych 2 lat, nie z okna


def test_technical_chart_traces_levels_and_rsi():
    df = _ohlc()
    f = ta.chart_frame(df, sessions=126)
    lv = ta.levels(df["High"], df["Low"])
    events = [(f.index[-3], float(f["Close"].iloc[-3]), "neg", "przebite wsparcie 90,00 USD (-2,0%)")]
    fig = technical_chart(f, lv, events, ccy="USD")
    names = [t.name for t in fig.data]
    assert fig.data[0].type == "candlestick"
    assert "SMA50" in names and "SMA200" in names and "RSI" in names
    marks = [t for t in fig.data if t.type == "scatter" and t.mode == "markers"]
    assert len(marks) == 1 and "przebite wsparcie" in marks[0].hovertext[0]
    shapes = fig.layout.shapes
    assert len(shapes) >= len(lv) + 2        # poziomy + linie RSI 70/30
    texts = [a.text for a in fig.layout.annotations]
    assert any("(" in s and "×)" in s for s in texts)


def test_technical_chart_without_open_falls_back_to_line():
    df = _ohlc().drop(columns="Open")
    fig = technical_chart(ta.chart_frame(df, sessions=60), [], [], ccy="PLN")
    assert fig.data[0].type == "scatter"
