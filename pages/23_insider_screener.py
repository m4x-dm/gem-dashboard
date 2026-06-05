"""Strona 23: Bulk Insider Screener.

Bulk insider activity dla SP500 (456 spolek). Window: 6 mc.
ETF wykluczone (no insider data). GPW pominiete (yfinance brak SEC Form 4).

Spec: docs/superpowers/specs/2026-06-05-bulk-insider-screener-design.md
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.auth import require_premium
from components.formatting import GOLD, GREEN, RED
from components.sidebar import setup_sidebar, render_footer
from data.financials import (
    bulk_fetch_insider_screener,
    format_large_number,
)
from data.sp500_universe import ALL_SP500_TICKERS


# ---------------------------------------------------------------------------
# Page config + auth + sidebar
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Insider Screener",
    page_icon="👥",
    layout="wide",
)
setup_sidebar()
if not require_premium(23):
    st.stop()

st.markdown("# 👥 Bulk Insider Screener")
st.caption(
    "Bulk insider activity dla SP500 (456 spolek). "
    "Window: ostatnie 6 mc. ETF wykluczone (no insider data). "
    "GPW pominiete (yfinance nie ma SEC Form 4 dla PL)."
)

# ---------------------------------------------------------------------------
# BULK FETCH (cache 24h, cold cache ~5-7 min)
# ---------------------------------------------------------------------------

universe = tuple(ALL_SP500_TICKERS)
df = bulk_fetch_insider_screener(universe)

if df.empty:
    st.warning(
        "Brak danych insider — yfinance moze byc globalnie blocked dla "
        "insider endpointow. Sprobuj ponownie za kilka minut (cache 24h)."
    )
    render_footer()
    st.stop()

# ---------------------------------------------------------------------------
# FILTRY (expander)
# ---------------------------------------------------------------------------

with st.expander("Filtry", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        sector_options = sorted(set(df["sector"].dropna()))
        sector_filter = st.multiselect(
            "Sektor",
            options=sector_options,
            default=[],
            key="insider_screener_sector",
        )
        status_filter = st.radio(
            "Status",
            ["Wszystkie", "Net Buyers 🟢", "Net Sellers 🔴", "Mixed 🟡"],
            horizontal=True, key="insider_screener_status",
        )
    with c2:
        min_net_value = st.number_input(
            "Min |Net Value| ($)",
            min_value=0, value=0, step=100_000,
            help="Filter abs(net_value_6m). 0 = bez filtra.",
            key="insider_screener_min_net",
        )
        min_streak = st.slider(
            "Min beat streak (mc 0-6)", 0, 6, 0,
            key="insider_screener_min_streak",
        )
    with c3:
        cap_options = [
            ("Brak", 0),
            ("$1B+", 1e9),
            ("$10B+", 10e9),
            ("$100B+", 100e9),
            ("$1T+", 1e12),
        ]
        min_cap_choice = st.selectbox(
            "Min Market Cap",
            options=cap_options,
            format_func=lambda x: x[0],
            key="insider_screener_min_cap",
        )
        sort_by = st.selectbox(
            "Sort by",
            options=[
                "net_value_6m DESC", "net_value_6m ASC",
                "n_buys DESC", "n_sells DESC",
                "beat_streak_buys DESC", "market_cap DESC",
                "top_inst_pct DESC", "avg_buy_size DESC", "ticker A-Z",
            ],
            key="insider_screener_sort",
        )
        top_n = st.selectbox(
            "Top N", [10, 25, 50, 100, 250], index=2,
            key="insider_screener_top_n",
        )
        if st.button("🔄 Refresh cache", key="insider_screener_refresh"):
            st.cache_data.clear()
            st.rerun()

# ---------------------------------------------------------------------------
# APPLY FILTRY
# ---------------------------------------------------------------------------

filtered = df.copy()
if sector_filter:
    filtered = filtered[filtered["sector"].isin(sector_filter)]
if status_filter == "Net Buyers 🟢":
    filtered = filtered[filtered["sentiment"] == "🟢"]
elif status_filter == "Net Sellers 🔴":
    filtered = filtered[filtered["sentiment"] == "🔴"]
elif status_filter == "Mixed 🟡":
    filtered = filtered[filtered["sentiment"] == "🟡"]
if min_net_value > 0:
    filtered = filtered[filtered["net_value_6m"].abs() >= min_net_value]
if min_streak > 0:
    filtered = filtered[filtered["beat_streak_buys"] >= min_streak]
if min_cap_choice[1] > 0:
    filtered = filtered[filtered["market_cap"].fillna(0) >= min_cap_choice[1]]

# Sort
if sort_by.endswith("DESC"):
    col = sort_by.replace(" DESC", "")
    filtered = filtered.sort_values(by=col, ascending=False, na_position="last")
elif sort_by.endswith("ASC"):
    col = sort_by.replace(" ASC", "")
    filtered = filtered.sort_values(by=col, ascending=True, na_position="last")
elif sort_by == "ticker A-Z":
    filtered = filtered.sort_values(by="ticker")

# ---------------------------------------------------------------------------
# SUMMARY (4 metric cards)
# ---------------------------------------------------------------------------

total_with_data = len(df)
n_net_buyers = int((df["sentiment"] == "🟢").sum())
n_net_sellers = int((df["sentiment"] == "🔴").sum())
avg_net = df["net_value_6m"].mean()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Spolek z danymi", f"{total_with_data}/456")
c2.metric(
    "Net Buyers 🟢", f"{n_net_buyers}",
    f"{n_net_buyers / total_with_data * 100:.0f}%" if total_with_data else "",
)
c3.metric("Net Sellers 🔴", f"{n_net_sellers}")
c4.metric("Avg Net 6mc", format_large_number(avg_net) if pd.notna(avg_net) else "—")

st.markdown("---")

# ---------------------------------------------------------------------------
# SEKCJA 1: Top Buyers + Top Sellers (2 bar charts side-by-side)
# ---------------------------------------------------------------------------

st.markdown("### 📈 Top movers")
col_b, col_s = st.columns(2)

with col_b:
    top_buyers = filtered.nlargest(10, "net_value_6m")
    if not top_buyers.empty and top_buyers["net_value_6m"].max() > 0:
        labels_b = [
            f"{t} — {n[:25]}"
            for t, n in zip(top_buyers["ticker"], top_buyers["name"])
        ]
        fig_b = go.Figure(go.Bar(
            x=top_buyers["net_value_6m"],
            y=labels_b,
            orientation="h",
            marker_color=GREEN,
            text=[format_large_number(v) for v in top_buyers["net_value_6m"]],
            textposition="outside",
        ))
        fig_b.update_layout(
            title="Top 10 Net Buyers (6 mc)",
            template="plotly_dark",
            height=380,
            yaxis=dict(autorange="reversed"),
            xaxis_title="Net Value USD",
            margin=dict(l=40, r=80, t=60, b=40),
            showlegend=False,
        )
        st.plotly_chart(fig_b, use_container_width=True)
    else:
        st.caption("Brak net buyers po filtrach.")

with col_s:
    top_sellers = filtered.nsmallest(10, "net_value_6m")
    if not top_sellers.empty and top_sellers["net_value_6m"].min() < 0:
        labels_s = [
            f"{t} — {n[:25]}"
            for t, n in zip(top_sellers["ticker"], top_sellers["name"])
        ]
        fig_s = go.Figure(go.Bar(
            x=top_sellers["net_value_6m"],
            y=labels_s,
            orientation="h",
            marker_color=RED,
            text=[format_large_number(v) for v in top_sellers["net_value_6m"]],
            textposition="outside",
        ))
        fig_s.update_layout(
            title="Top 10 Net Sellers (6 mc)",
            template="plotly_dark",
            height=380,
            yaxis=dict(autorange="reversed"),
            xaxis_title="Net Value USD",
            margin=dict(l=40, r=80, t=60, b=40),
            showlegend=False,
        )
        st.plotly_chart(fig_s, use_container_width=True)
    else:
        st.caption("Brak net sellers po filtrach.")

st.markdown("---")

# ---------------------------------------------------------------------------
# SEKCJA 2: Tabela screener (st.dataframe)
# ---------------------------------------------------------------------------

st.markdown(f"### 📋 Tabela screener ({len(filtered)} spolek)")

display = filtered.head(top_n).copy()
display = display.rename(columns={
    "sentiment": "🎯",
    "ticker": "Ticker",
    "name": "Nazwa",
    "sector": "Sektor",
    "market_cap": "Cap",
    "net_value_6m": "Net 6mc",
    "n_buys": "#Buys",
    "n_sells": "#Sells",
    "top_buyer": "Top Buyer",
    "top_institutional": "Top Fund",
    "beat_streak_buys": "Streak",
})
display_cols = [
    "🎯", "Ticker", "Nazwa", "Sektor", "Cap", "Net 6mc",
    "#Buys", "#Sells", "Top Buyer", "Top Fund", "Streak",
]

st.dataframe(
    display[display_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Cap": st.column_config.NumberColumn("Cap", format="$%.0f"),
        "Net 6mc": st.column_config.NumberColumn("Net 6mc", format="$%+.0f"),
        "Streak": st.column_config.ProgressColumn(
            "Streak", min_value=0, max_value=6, format="%d mc",
        ),
    },
)

st.markdown("---")

# Placeholder dla Task 7-8
st.info("🚧 Heatmapa, cross-link i CSV dodane w kolejnych taskach.")

render_footer()
