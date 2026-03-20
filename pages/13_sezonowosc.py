"""Strona 13: Sezonowosc — heatmapa miesięcznych zwrotow, wzorce sezonowe, Sell in May."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from components.sidebar import setup_sidebar, render_footer
from data.downloader import download_prices
from data.etf_universe import ALL_TICKERS, ETF_NAMES
from data.momentum import monthly_returns_matrix
from components.charts import seasonality_heatmap, _base_layout, COLORS, BG2, GOLD
from components.constants import PERIOD_MAP_FULL

st.set_page_config(page_title="Sezonowosc", page_icon="📅", layout="wide")
setup_sidebar()

st.markdown("# 📅 Sezonowosc")
st.caption("Heatmapa miesięcznych zwrotow, wzorce sezonowe, analiza Sell in May")

# --- Ticker select ---
MONTH_NAMES_PL = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
                  "Lip", "Sie", "Wrz", "Paz", "Lis", "Gru"]

default_tickers = ["QQQ", "SPY", "VEA", "AGG", "GLD"]
custom = st.session_state.get("custom_tickers", [])
all_available = ALL_TICKERS + custom

ticker = st.selectbox(
    "Wybierz ticker",
    options=all_available,
    index=all_available.index("QQQ") if "QQQ" in all_available else 0,
    format_func=lambda t: f"{t} — {ETF_NAMES.get(t, t)}",
)

period = st.selectbox("Okres danych", list(PERIOD_MAP_FULL.keys())[3:],
                       index=4, key="sez_period")
yf_period = PERIOD_MAP_FULL.get(period, "10y")

# --- Download ---
with st.spinner("Pobieram dane..."):
    prices = download_prices([ticker], period=yf_period)

if prices.empty or ticker not in prices.columns:
    st.error(f"Brak danych dla {ticker}")
    render_footer()
    st.stop()

series = prices[ticker].dropna()
matrix = monthly_returns_matrix(series)

if matrix.empty:
    st.warning("Za malo danych do analizy sezonowosci.")
    render_footer()
    st.stop()

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📊 Heatmapa", "📈 Sredni miesiac", "🏖️ Sell in May"])

with tab1:
    st.plotly_chart(seasonality_heatmap(matrix, title=f"Sezonowosc {ticker} — miesięczne zwroty (%)"),
                    use_container_width=True)

with tab2:
    avg = matrix.mean() * 100
    median = matrix.median() * 100
    colors = ["#22C55E" if v > 0 else "#EF4444" for v in avg.values]
    x_labels = [MONTH_NAMES_PL[m - 1] for m in avg.index]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x_labels, y=avg.values, name="Srednia",
        marker_color=colors,
        text=[f"{v:.2f}%" for v in avg.values],
        textposition="outside", textfont=dict(size=11),
    ))
    fig.add_trace(go.Scatter(
        x=x_labels, y=median.values, name="Mediana",
        mode="lines+markers",
        line=dict(color=GOLD, width=2),
        marker=dict(size=6),
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)", line_width=1)
    fig.update_layout(**_base_layout(f"{ticker} — sredni zwrot miesięczny (%)", height=450))
    fig.update_yaxes(title_text="%")
    st.plotly_chart(fig, use_container_width=True)

    # Stats table
    stats_df = pd.DataFrame({
        "Miesiac": MONTH_NAMES_PL[:len(avg)],
        "Srednia (%)": [f"{v:.2f}" for v in avg.values],
        "Mediana (%)": [f"{v:.2f}" for v in median.values],
        "% dodatnich": [f"{(matrix[m] > 0).sum() / matrix[m].notna().sum() * 100:.0f}%"
                        for m in avg.index],
        "Liczba lat": [int(matrix[m].notna().sum()) for m in avg.index],
    })
    st.dataframe(stats_df, use_container_width=True, hide_index=True)

with tab3:
    st.markdown("### Sell in May and Go Away")
    st.caption("Porownanie zwrotow Maj-Pazdziernik vs Listopad-Kwiecien")

    # Calculate Sell in May periods
    may_oct_months = [5, 6, 7, 8, 9, 10]
    nov_apr_months = [11, 12, 1, 2, 3, 4]

    years = sorted(matrix.index.tolist())
    sell_may_data = []

    for year in years:
        # May-Oct of this year
        mo_rets = []
        for m in may_oct_months:
            if m in matrix.columns:
                val = matrix.loc[year, m] if year in matrix.index else np.nan
                if pd.notna(val):
                    mo_rets.append(val)
        may_oct_ret = (np.prod([1 + r for r in mo_rets]) - 1) if mo_rets else np.nan

        # Nov of previous year through Apr of this year
        na_rets = []
        for m in nov_apr_months:
            yr = year - 1 if m >= 11 else year
            if yr in matrix.index and m in matrix.columns:
                val = matrix.loc[yr, m]
                if pd.notna(val):
                    na_rets.append(val)
        nov_apr_ret = (np.prod([1 + r for r in na_rets]) - 1) if na_rets else np.nan

        sell_may_data.append({
            "Rok": year,
            "Maj-Paz (%)": may_oct_ret * 100 if pd.notna(may_oct_ret) else np.nan,
            "Lis-Kwi (%)": nov_apr_ret * 100 if pd.notna(nov_apr_ret) else np.nan,
        })

    sm_df = pd.DataFrame(sell_may_data).dropna(subset=["Maj-Paz (%)", "Lis-Kwi (%)"])

    if not sm_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[str(y) for y in sm_df["Rok"]],
            y=sm_df["Maj-Paz (%)"],
            name="Maj-Paz",
            marker_color="#EF4444",
        ))
        fig.add_trace(go.Bar(
            x=[str(y) for y in sm_df["Rok"]],
            y=sm_df["Lis-Kwi (%)"],
            name="Lis-Kwi",
            marker_color="#22C55E",
        ))
        fig.update_layout(**_base_layout(f"{ticker} — Sell in May vs Winter", height=450))
        fig.update_layout(barmode="group")
        fig.update_yaxes(title_text="%")
        fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)", line_width=1)
        st.plotly_chart(fig, use_container_width=True)

        # Summary stats
        avg_mo = sm_df["Maj-Paz (%)"].mean()
        avg_na = sm_df["Lis-Kwi (%)"].mean()
        win_na = (sm_df["Lis-Kwi (%)"] > sm_df["Maj-Paz (%)"]).sum()
        total = len(sm_df)

        cols = st.columns(3)
        cols[0].metric("Sredni zwrot Maj-Paz", f"{avg_mo:.2f}%")
        cols[1].metric("Sredni zwrot Lis-Kwi", f"{avg_na:.2f}%")
        cols[2].metric("Lis-Kwi wygrywa", f"{win_na}/{total} ({win_na/total*100:.0f}%)")
    else:
        st.warning("Za malo danych do analizy Sell in May.")

render_footer()
