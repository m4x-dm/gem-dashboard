"""Strona 15: Analiza Drawdownow — top N spadkow, czas trwania, odbudowa."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from components.sidebar import setup_sidebar, render_footer
from data.downloader import download_prices
from data.etf_universe import ALL_TICKERS, ETF_NAMES
from data.momentum import top_drawdowns, drawdown_series
from components.charts import drawdown_chart, _base_layout, COLORS, GOLD, BG2
from components.formatting import fmt_pct, MUTED, BG_CARD, BORDER
from components.constants import PERIOD_MAP_FULL, RED, GREEN

st.set_page_config(page_title="Analiza Drawdownow", page_icon="📉", layout="wide")
setup_sidebar()

st.markdown("# 📉 Analiza Drawdownow")
st.caption("Top spadki od szczytu, czas trwania, czas odbudowy")

# --- Config ---
custom = st.session_state.get("custom_tickers", [])
all_available = ALL_TICKERS + custom

col1, col2 = st.columns([2, 1])
with col1:
    ticker = st.selectbox("Ticker", all_available,
                           index=all_available.index("QQQ") if "QQQ" in all_available else 0,
                           format_func=lambda t: f"{t} — {ETF_NAMES.get(t, t)}",
                           key="dd_ticker")
with col2:
    period = st.selectbox("Okres", list(PERIOD_MAP_FULL.keys())[3:], index=4, key="dd_period")

yf_period = PERIOD_MAP_FULL[period]

with st.spinner("Pobieram dane..."):
    prices = download_prices([ticker], period=yf_period)

if prices.empty or ticker not in prices.columns:
    st.error(f"Brak danych dla {ticker}")
    render_footer()
    st.stop()

series = prices[ticker].dropna()
dd = drawdown_series(series)
top_dd = top_drawdowns(series, n=10)

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["📉 Underwater", "📋 Tabela", "⚖️ Porownanie", "📊 Histogram"])

with tab1:
    st.subheader(f"Drawdown — {ticker}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dd.index, y=dd.values * 100, mode="lines",
        fill="tozeroy", line=dict(color=RED, width=1),
        fillcolor="rgba(239,68,68,0.2)", name="Drawdown",
        hovertemplate="%{x|%Y-%m-%d}<br>Drawdown: %{y:.1f}%<extra></extra>",
    ))

    # Mark top 5 troughs
    if not top_dd.empty:
        for i, row in top_dd.head(5).iterrows():
            trough = row["trough_date"]
            depth = row["depth_pct"] * 100
            fig.add_annotation(
                x=trough, y=depth,
                text=f"#{i} ({depth:.1f}%)",
                showarrow=True, arrowhead=2,
                font=dict(size=10, color=GOLD),
                arrowcolor=GOLD,
            )

    fig.update_layout(**_base_layout(f"{ticker} — spadki od szczytu", height=450))
    fig.update_yaxes(title_text="%")
    st.plotly_chart(fig, use_container_width=True)

    # Current drawdown
    current_dd = dd.iloc[-1]
    if current_dd < 0:
        st.warning(f"Aktualny drawdown: **{current_dd*100:.1f}%**")
    else:
        st.success("Aktualnie na szczycie (brak drawdownu)")

with tab2:
    st.subheader(f"Top 10 drawdownow — {ticker}")
    if top_dd.empty:
        st.info("Brak drawdownow w wybranym okresie.")
    else:
        # Format table
        display_df = top_dd.copy()
        display_df["depth_pct"] = display_df["depth_pct"].apply(lambda v: f"{v*100:.1f}%")
        display_df["peak_date"] = display_df["peak_date"].apply(lambda d: d.strftime("%Y-%m-%d") if pd.notna(d) else "—")
        display_df["trough_date"] = display_df["trough_date"].apply(lambda d: d.strftime("%Y-%m-%d") if pd.notna(d) else "—")
        display_df["recovery_date"] = display_df["recovery_date"].apply(lambda d: d.strftime("%Y-%m-%d") if pd.notna(d) else "trwa...")
        display_df["days_down"] = display_df["days_down"].apply(lambda d: f"{d} dni" if pd.notna(d) else "—")
        display_df["days_recovery"] = display_df["days_recovery"].apply(lambda d: f"{d} dni" if pd.notna(d) else "trwa...")
        display_df.columns = ["Szczyt", "Dolina", "Odbudowa", "Glebia", "Spadek (dni)", "Odbudowa (dni)"]
        st.dataframe(display_df, use_container_width=True)

with tab3:
    st.subheader("Porownanie drawdownow")
    compare_tickers = st.multiselect("Wybierz 2-4 tickery", all_available,
                                      default=["QQQ", "VEA", "AGG"],
                                      max_selections=4, key="dd_compare")
    if len(compare_tickers) >= 2:
        with st.spinner("Pobieram dane..."):
            compare_prices = download_prices(compare_tickers, period=yf_period)

        if not compare_prices.empty:
            st.plotly_chart(
                drawdown_chart(compare_prices, title="Porownanie drawdownow"),
                use_container_width=True,
            )

            # Summary: max DD per ticker
            cols = st.columns(len(compare_tickers))
            for i, t in enumerate(compare_tickers):
                if t in compare_prices.columns:
                    s = compare_prices[t].dropna()
                    dd_s = drawdown_series(s)
                    max_dd = dd_s.min()
                    cols[i].metric(f"Max DD {t}", f"{max_dd*100:.1f}%")
        else:
            st.warning("Brak danych dla wybranych tickerow.")
    else:
        st.info("Wybierz co najmniej 2 tickery.")

with tab4:
    st.subheader(f"Rozklad drawdownow — {ticker}")
    if not top_dd.empty and len(top_dd) >= 3:
        col1, col2 = st.columns(2)

        with col1:
            depths = top_dd["depth_pct"].values * 100
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=depths, nbinsx=15,
                marker_color=RED, opacity=0.75,
                name="Glebia drawdownu",
            ))
            fig.update_layout(**_base_layout("Rozklad glebokosci drawdownow (%)", height=350))
            fig.update_xaxes(title_text="Glebia (%)")
            fig.update_yaxes(title_text="Liczba")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            durations = top_dd["days_down"].dropna().values
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=durations, nbinsx=15,
                marker_color="#F59E0B", opacity=0.75,
                name="Czas trwania",
            ))
            fig.update_layout(**_base_layout("Rozklad dlugosci spadkow (dni)", height=350))
            fig.update_xaxes(title_text="Dni")
            fig.update_yaxes(title_text="Liczba")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Za malo drawdownow do wyswietlenia histogramu.")

render_footer()
