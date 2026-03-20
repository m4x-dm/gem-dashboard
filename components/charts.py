"""Wykresy Plotly z dark theme i gold accent."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from components.constants import GOLD, BG, BG2, GRID, CHART_COLORS as COLORS  # noqa: F401


def _base_layout(title: str = "", height: int = 450) -> dict:
    """Bazowy layout dla wykresow."""
    return dict(
        template="plotly_dark",
        paper_bgcolor=BG2,
        plot_bgcolor=BG2,
        title=dict(text=title, font=dict(size=16, color="#E5E7EB")),
        font=dict(color="#9CA3AF", size=12),
        xaxis=dict(gridcolor=GRID, showgrid=True),
        yaxis=dict(gridcolor=GRID, showgrid=True),
        height=height,
        margin=dict(l=40, r=20, t=40, b=30),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
    )


def price_chart(prices: pd.DataFrame, title: str = "Cena (baza = 100)",
                normalize: bool = True) -> go.Figure:
    """Wykres cenowy (znormalizowany lub absolutny)."""
    fig = go.Figure()
    data = prices.dropna(how="all")
    if normalize and len(data) > 0:
        first_valid = data.apply(lambda s: s.dropna().iloc[0] if len(s.dropna()) > 0 else np.nan)
        first_valid = first_valid.replace(0, np.nan)
        data = data / first_valid * 100

    for i, col in enumerate(data.columns):
        series = data[col].dropna()
        fig.add_trace(go.Scatter(
            x=series.index, y=series.values,
            name=col, mode="lines",
            line=dict(color=COLORS[i % len(COLORS)], width=2),
        ))

    fig.update_layout(**_base_layout(title))
    return fig


def momentum_chart(prices: pd.DataFrame, window: int = 252,
                    title: str = "Momentum 12M (rolling)") -> go.Figure:
    """Rolling momentum chart."""
    fig = go.Figure()
    skip = 21  # 1-month skip for skip-month momentum
    for i, col in enumerate(prices.columns):
        series = prices[col].dropna()
        if len(series) > window:
            if window >= 252:
                # Skip-month momentum (12-1): od 13M wstecz do 1M wstecz
                mom = (series.shift(skip) / series.shift(window + skip) - 1).dropna() * 100
            else:
                mom = series.pct_change(periods=window).dropna() * 100
            fig.add_trace(go.Scatter(
                x=mom.index, y=mom.values,
                name=col, mode="lines",
                line=dict(color=COLORS[i % len(COLORS)], width=2),
            ))

    # Linia zerowa
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)", line_width=1)
    fig.update_layout(**_base_layout(title))
    fig.update_yaxes(title_text="%")
    return fig


def drawdown_chart(prices: pd.DataFrame, title: str = "Drawdown (spadek od szczytu)") -> go.Figure:
    """Wykres drawdown."""
    fig = go.Figure()
    for i, col in enumerate(prices.columns):
        series = prices[col].dropna()
        running_max = series.cummax()
        dd = ((series - running_max) / running_max) * 100
        fig.add_trace(go.Scatter(
            x=dd.index, y=dd.values,
            name=col, mode="lines",
            fill="tozeroy",
            line=dict(color=COLORS[i % len(COLORS)], width=1),
            fillcolor=f"rgba({_hex_to_rgb(COLORS[i % len(COLORS)])},0.15)",
        ))

    fig.update_layout(**_base_layout(title))
    fig.update_yaxes(title_text="%")
    return fig


def ranking_bar_chart(ranking_df: pd.DataFrame, top_n: int = 10,
                      title: str = "Top 10 — wynik momentum") -> go.Figure:
    """Wykres slupkowy rankingu."""
    df = ranking_df.head(top_n).copy()
    df = df.sort_values("Wynik", ascending=True)  # odwroc dla poziomego wykresu

    colors = [("#22C55E" if v > 0 else "#EF4444") for v in df["Wynik"]]

    fig = go.Figure(go.Bar(
        x=df["Wynik"] * 100,
        y=df.index,
        orientation="h",
        marker_color=colors,
        text=[f"{v*100:.1f}%" for v in df["Wynik"]],
        textposition="outside",
        textfont=dict(size=11),
    ))
    fig.update_layout(**_base_layout(title, height=max(300, top_n * 35)))
    fig.update_xaxes(title_text="Wynik kompozytowy (%)")
    return fig


def equity_chart(equity_curves: dict[str, pd.Series],
                 title: str = "Krzywa kapitalu") -> go.Figure:
    """Wykres equity curve dla backtestu."""
    fig = go.Figure()
    for i, (name, eq) in enumerate(equity_curves.items()):
        fig.add_trace(go.Scatter(
            x=eq.index, y=eq.values,
            name=name, mode="lines",
            line=dict(color=COLORS[i % len(COLORS)], width=2),
        ))

    fig.update_layout(**_base_layout(title))
    fig.update_yaxes(title_text="Wartosc portfela (USD)")
    return fig


def correlation_heatmap(corr_matrix: pd.DataFrame,
                        title: str = "Macierz korelacji") -> go.Figure:
    """Heatmapa korelacji."""
    fig = go.Figure(go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.index,
        colorscale=[[0, "#EF4444"], [0.5, BG2], [1, "#22C55E"]],
        zmid=0,
        text=np.round(corr_matrix.values, 2),
        texttemplate="%{text}",
        textfont=dict(size=11),
    ))
    fig.update_layout(**_base_layout(title, height=max(400, len(corr_matrix) * 45)))
    return fig


def category_pie(category_counts: dict, title: str = "Rozklad kategorii") -> go.Figure:
    """Pie chart kategorii ETF."""
    fig = go.Figure(go.Pie(
        labels=list(category_counts.keys()),
        values=list(category_counts.values()),
        marker=dict(colors=COLORS[:len(category_counts)]),
        textfont=dict(size=12),
        hole=0.4,
    ))
    fig.update_layout(**_base_layout(title, height=350))
    return fig


def sparkline_chart(series: pd.Series, title: str = "", height: int = 120,
                     color: str = GOLD, fill: bool = True) -> go.Figure:
    """Minimalny wykres liniowy (sparkline) do kart makro."""
    fig = go.Figure()
    s = series.dropna()
    if len(s) == 0:
        return fig

    fill_mode = "tozeroy" if fill else "none"
    r, g, b = _hex_to_rgb(color).split(",")
    fill_color = f"rgba({r},{g},{b},0.12)" if fill else None

    fig.add_trace(go.Scatter(
        x=s.index, y=s.values, mode="lines",
        line=dict(color=color, width=1.5),
        fill=fill_mode, fillcolor=fill_color,
        hovertemplate="%{x|%Y-%m-%d}<br>%{y:.2f}<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig


def seasonality_heatmap(matrix: pd.DataFrame,
                        title: str = "Sezonowosc — miesięczne zwroty (%)") -> go.Figure:
    """Heatmapa rok × miesiac. Kolory: czerwony (ujemny) → bg → zielony (dodatni)."""
    MONTH_NAMES_PL = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
                      "Lip", "Sie", "Wrz", "Paz", "Lis", "Gru"]
    vals = matrix.values * 100  # do procentow
    labels = np.where(np.isnan(vals), "", np.vectorize(lambda v: f"{v:.1f}%")(vals))

    cols_present = matrix.columns.tolist()
    x_labels = [MONTH_NAMES_PL[m - 1] if m <= 12 else str(m) for m in cols_present]

    fig = go.Figure(go.Heatmap(
        z=vals,
        x=x_labels,
        y=[str(y) for y in matrix.index],
        colorscale=[[0, "#EF4444"], [0.5, BG2], [1, "#22C55E"]],
        zmid=0,
        text=labels,
        texttemplate="%{text}",
        textfont=dict(size=10),
        hovertemplate="Rok: %{y}<br>Miesiąc: %{x}<br>Zwrot: %{text}<extra></extra>",
    ))
    h = max(400, len(matrix) * 28)
    fig.update_layout(**_base_layout(title, height=h))
    fig.update_xaxes(side="top")
    return fig


def fan_chart(simulations: pd.DataFrame,
              percentiles: list[int] | None = None,
              title: str = "Monte Carlo — wachlarz przyszlych sciezek",
              trading_days: int = 252) -> go.Figure:
    """Wachlarz percentylowy symulacji Monte Carlo."""
    if percentiles is None:
        percentiles = [5, 25, 50, 75, 95]

    x_years = np.arange(len(simulations)) / trading_days
    pcts = {}
    for p in percentiles:
        pcts[p] = np.percentile(simulations.values, p, axis=1)

    fig = go.Figure()

    # Fill bands (outer to inner)
    band_pairs = [(5, 95, "rgba(201,168,76,0.08)"), (25, 75, "rgba(201,168,76,0.18)")]
    for lo, hi, fill_color in band_pairs:
        if lo in pcts and hi in pcts:
            fig.add_trace(go.Scatter(
                x=x_years, y=pcts[hi], mode="lines",
                line=dict(width=0), showlegend=False, hoverinfo="skip",
            ))
            fig.add_trace(go.Scatter(
                x=x_years, y=pcts[lo], mode="lines",
                line=dict(width=0), fill="tonexty", fillcolor=fill_color,
                showlegend=False, hoverinfo="skip",
            ))

    # Median line
    if 50 in pcts:
        fig.add_trace(go.Scatter(
            x=x_years, y=pcts[50], mode="lines",
            line=dict(color=GOLD, width=2.5), name="Mediana (P50)",
            hovertemplate="Rok %{x:.1f}<br>Wartosc: %{y:,.0f}<extra></extra>",
        ))

    # Percentile labels
    for p in [5, 25, 75, 95]:
        if p in pcts:
            fig.add_trace(go.Scatter(
                x=x_years, y=pcts[p], mode="lines",
                line=dict(color=GOLD, width=1, dash="dot"),
                name=f"P{p}",
                hovertemplate=f"P{p}<br>Rok %{{x:.1f}}<br>Wartosc: %{{y:,.0f}}<extra></extra>",
            ))

    fig.update_layout(**_base_layout(title, height=500))
    fig.update_xaxes(title_text="Lata")
    fig.update_yaxes(title_text="Wartosc portfela")
    return fig


def ta_overview_chart(prices: pd.Series, ema_df: pd.DataFrame,
                      bb_df: pd.DataFrame, signals_df: pd.DataFrame | None = None,
                      title: str = "Analiza techniczna") -> go.Figure:
    """Wykres cenowy + EMA + Bollinger Bands + markery BUY/SELL."""
    fig = go.Figure()

    # Bollinger fill
    bb_clean = bb_df.dropna()
    if not bb_clean.empty:
        fig.add_trace(go.Scatter(
            x=bb_clean.index, y=bb_clean["Upper"], mode="lines",
            line=dict(width=0), showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=bb_clean.index, y=bb_clean["Lower"], mode="lines",
            line=dict(width=0), fill="tonexty",
            fillcolor="rgba(201,168,76,0.08)", showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=bb_clean.index, y=bb_clean["Upper"], mode="lines",
            line=dict(color="rgba(201,168,76,0.3)", width=1, dash="dot"), name="BB Upper",
        ))
        fig.add_trace(go.Scatter(
            x=bb_clean.index, y=bb_clean["Lower"], mode="lines",
            line=dict(color="rgba(201,168,76,0.3)", width=1, dash="dot"), name="BB Lower",
        ))

    # Cena
    p = prices.dropna()
    fig.add_trace(go.Scatter(
        x=p.index, y=p.values, name="Cena", mode="lines",
        line=dict(color="#E5E7EB", width=2),
    ))

    # EMA lines
    ema_colors = {"EMA_20": GOLD, "EMA_50": "#3B82F6", "EMA_200": "#A855F7"}
    for col in ema_df.columns:
        s = ema_df[col].dropna()
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=col, mode="lines",
            line=dict(color=ema_colors.get(col, GOLD), width=1.5),
        ))

    # BUY/SELL markers
    if signals_df is not None and not signals_df.empty:
        buys = signals_df[signals_df["type"] == "BUY"]
        sells = signals_df[signals_df["type"] == "SELL"]
        if not buys.empty:
            fig.add_trace(go.Scatter(
                x=buys["date"], y=buys["price"], mode="markers",
                marker=dict(symbol="triangle-up", size=12, color="#22C55E", line=dict(width=1, color="#fff")),
                name="KUP",
            ))
        if not sells.empty:
            fig.add_trace(go.Scatter(
                x=sells["date"], y=sells["price"], mode="markers",
                marker=dict(symbol="triangle-down", size=12, color="#EF4444", line=dict(width=1, color="#fff")),
                name="SPRZEDAJ",
            ))

    fig.update_layout(**_base_layout(title, height=500))
    return fig


def macd_chart(macd_df: pd.DataFrame, title: str = "MACD") -> go.Figure:
    """Wykres MACD: linia MACD, Signal, Histogram (bar green/red)."""
    fig = go.Figure()
    df = macd_df.dropna()
    if df.empty:
        fig.update_layout(**_base_layout(title, height=250))
        return fig

    # Histogram bars
    colors = ["#22C55E" if v >= 0 else "#EF4444" for v in df["Histogram"]]
    fig.add_trace(go.Bar(
        x=df.index, y=df["Histogram"], name="Histogram",
        marker_color=colors, opacity=0.6,
    ))

    # MACD & Signal lines
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MACD"], name="MACD", mode="lines",
        line=dict(color=GOLD, width=2),
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Signal"], name="Signal", mode="lines",
        line=dict(color="#3B82F6", width=1.5),
    ))

    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.2)", line_width=1)
    fig.update_layout(**_base_layout(title, height=250))
    return fig


def rsi_chart(rsi_series: pd.Series, title: str = "RSI") -> go.Figure:
    """Wykres RSI z strefami overbought/oversold."""
    fig = go.Figure()
    s = rsi_series.dropna()
    if s.empty:
        fig.update_layout(**_base_layout(title, height=250))
        return fig

    # Overbought zone (70-100)
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(239,68,68,0.08)", line_width=0)
    # Oversold zone (0-30)
    fig.add_hrect(y0=0, y1=30, fillcolor="rgba(34,197,94,0.08)", line_width=0)

    # RSI line
    fig.add_trace(go.Scatter(
        x=s.index, y=s.values, name="RSI", mode="lines",
        line=dict(color=GOLD, width=2),
    ))

    # Reference lines
    for level, dash in [(30, "dash"), (50, "dot"), (70, "dash")]:
        fig.add_hline(y=level, line_dash=dash, line_color="rgba(255,255,255,0.2)", line_width=1)

    fig.update_layout(**_base_layout(title, height=250))
    fig.update_yaxes(range=[0, 100])
    return fig


def _hex_to_rgb(hex_color: str) -> str:
    """Konwertuje #RRGGBB na R,G,B."""
    h = hex_color.lstrip("#")
    return f"{int(h[:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"
