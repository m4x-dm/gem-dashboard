"""Strona 24: Bulk Insider Screener.

Bulk insider activity dla SP500 (456 spolek). Window: 6 mc.
ETF wykluczone (no insider data). GPW pominiete (yfinance brak SEC Form 4).

Spec: docs/superpowers/specs/2026-06-05-bulk-insider-screener-design.md
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_local_storage import LocalStorage

from components.formatting import GREEN, RED
from components import nav
from components.sidebar import render_footer
from components.watchlist import get_watchlist, toggle_ticker
from data.financials import (
    bulk_fetch_insider_screener,
    format_large_number,
)
from data.sp500_universe import ALL_SP500_TICKERS
from components.i18n import tr



st.markdown(tr("# Bulk Insider Screener"))
st.caption(
    tr("Bulk insider activity dla SP500 (456 spolek). "
    "Window: ostatnie 6 mc. ETF wykluczone (no insider data). "
    "GPW pominiete (yfinance nie ma SEC Form 4 dla PL).")
)

# ---------------------------------------------------------------------------
# BULK FETCH (cache 24h, cold cache ~5-7 min)
# ---------------------------------------------------------------------------

universe = tuple(ALL_SP500_TICKERS)
df = bulk_fetch_insider_screener(universe)

if df.empty:
    st.warning(
        tr("Brak danych insider — yfinance moze byc globalnie blocked dla "
        "insider endpointow. Sprobuj ponownie za kilka minut (cache 24h).")
    )
    render_footer()
    st.stop()

# Watchlist (F17)
ls = LocalStorage()
watchlist = get_watchlist(ls)

# ---------------------------------------------------------------------------
# FILTRY (expander)
# ---------------------------------------------------------------------------

with st.expander(tr("Filtry"), expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        sector_options = sorted(set(df["sector"].dropna()))
        sector_filter = st.multiselect(
            tr("Sektor"),
            options=sector_options,
            default=[],
            key="insider_screener_sector",
        )
        status_filter = st.radio(
            tr("Status"),
            ["Wszystkie", "Net Buyers 🟢", "Net Sellers 🔴", "Mixed 🟡"],
            horizontal=True, key="insider_screener_status", format_func=tr,
        )
    with c2:
        min_net_value = st.number_input(
            tr("Min |Net Value| ($)"),
            min_value=0, value=0, step=100_000,
            help=tr("Filter abs(net_value_6m). 0 = bez filtra."),
            key="insider_screener_min_net",
        )
        min_streak = st.slider(
            tr("Min beat streak (mc 0-6)"), 0, 6, 0,
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
            tr("Min Market Cap"),
            options=cap_options,
            format_func=lambda x: tr(x[0]),
            key="insider_screener_min_cap",
        )
        sort_by = st.selectbox(
            tr("Sort by"),
            options=[
                "net_value_6m DESC", "net_value_6m ASC",
                "n_buys DESC", "n_sells DESC",
                "beat_streak_buys DESC", "market_cap DESC",
                "top_inst_pct DESC", "avg_buy_size DESC", "ticker A-Z",
            ],
            key="insider_screener_sort",
        )
        top_n = st.selectbox(
            tr("Top N"), [10, 25, 50, 100, 250], index=2,
            key="insider_screener_top_n",
        )
        # F17 watchlist filter
        only_watchlist = st.checkbox(
            tr("⭐ Tylko watchlist"),
            value=False,
            disabled=len(watchlist) == 0,
            help="Watchlist pusty — kliknij ⭐ w tabeli aby dodac." if not watchlist else None,
            key="insider_screener_only_watchlist",
        )
        if st.button(tr("🔄 Refresh cache"), key="insider_screener_refresh"):
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
if only_watchlist:
    filtered = filtered[filtered["ticker"].isin(watchlist)]

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
c1.metric(tr("Spolek z danymi"), f"{total_with_data}/456")
c2.metric(
    tr("Net Buyers 🟢"), f"{n_net_buyers}",
    f"{n_net_buyers / total_with_data * 100:.0f}%" if total_with_data else "",
)
c3.metric(tr("Net Sellers 🔴"), f"{n_net_sellers}")
c4.metric(tr("Avg Net 6mc"), format_large_number(avg_net) if pd.notna(avg_net) else "—")

st.markdown("---")

# ---------------------------------------------------------------------------
# SEKCJA 1: Top Buyers + Top Sellers (2 bar charts side-by-side)
# ---------------------------------------------------------------------------

st.markdown(tr("### 📈 Top movers"))
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
            title=tr("Top 10 Net Buyers (6 mc)"),
            template="plotly_dark",
            height=380,
            yaxis=dict(autorange="reversed"),
            xaxis_title=tr("Net Value USD"),
            margin=dict(l=40, r=80, t=60, b=40),
            showlegend=False,
        )
        st.plotly_chart(fig_b, width="stretch")
    else:
        st.caption(tr("Brak net buyers po filtrach."))

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
            title=tr("Top 10 Net Sellers (6 mc)"),
            template="plotly_dark",
            height=380,
            yaxis=dict(autorange="reversed"),
            xaxis_title=tr("Net Value USD"),
            margin=dict(l=40, r=80, t=60, b=40),
            showlegend=False,
        )
        st.plotly_chart(fig_s, width="stretch")
    else:
        st.caption(tr("Brak net sellers po filtrach."))

st.markdown("---")

# ---------------------------------------------------------------------------
# SEKCJA 2: Tabela screener (st.dataframe)
# ---------------------------------------------------------------------------

st.markdown(tr('### 📋 Tabela screener ({v0} spolek)', v0=len(filtered)))

display = filtered.head(top_n).copy()
display = display.rename(columns={
    "sentiment": "🎯",
    "ticker": "Ticker",
    "name": tr("Nazwa"),
    "sector": tr("Sektor"),
    "market_cap": "Cap",
    "net_value_6m": tr("Net 6mc"),
    "n_buys": "#Buys",
    "n_sells": "#Sells",
    "top_buyer": "Top Buyer",
    "top_institutional": "Top Fund",
    "beat_streak_buys": "Streak",
})
display_cols = [
    "🎯", "Ticker", tr("Nazwa"), tr("Sektor"), "Cap", tr("Net 6mc"),
    "#Buys", "#Sells", "Top Buyer", "Top Fund", "Streak",
]

# Dodaj ⭐ kolumna jako pierwsza (F17)
display.insert(0, "⭐", display["Ticker"].isin(watchlist))
display_cols_with_star = ["⭐"] + display_cols

edited = st.data_editor(
    display[display_cols_with_star],
    width="stretch",
    hide_index=True,
    column_config={
        "⭐": st.column_config.CheckboxColumn("⭐", width="small"),
        "Cap": st.column_config.NumberColumn("Cap", format="$%.0f"),
        tr("Net 6mc"): st.column_config.NumberColumn(tr("Net 6mc"), format="$%+.0f"),
        "Streak": st.column_config.ProgressColumn(
            "Streak", min_value=0, max_value=6, format=tr("%d mc"),
        ),
    },
    disabled=[c for c in display_cols_with_star if c != "⭐"],
    key="insider_screener_table_v2",
)
# Diff detection -> toggle watchlist (F17)
diff_mask = edited["⭐"] != display[display_cols_with_star]["⭐"]
if diff_mask.any():
    for _, row in edited[diff_mask].iterrows():
        toggle_ticker(ls, row["Ticker"])
    st.rerun()

st.markdown("---")

# ---------------------------------------------------------------------------
# SEKCJA 3: Sektorowa heatmapa (Plotly horizontal bar)
# ---------------------------------------------------------------------------

st.markdown(tr("### 🏭 Net insider activity per sektor"))

sector_agg = filtered.groupby("sector")["net_value_6m"].sum().sort_values()
if not sector_agg.empty:
    colors_sec = [GREEN if v > 0 else RED for v in sector_agg.values]
    fig_sec = go.Figure(go.Bar(
        x=sector_agg.values,
        y=sector_agg.index,
        orientation="h",
        marker_color=colors_sec,
        text=[format_large_number(v) for v in sector_agg.values],
        textposition="outside",
    ))
    fig_sec.update_layout(
        title=tr("Sum net insider value 6 mc per sektor"),
        template="plotly_dark",
        height=400,
        xaxis_title=tr("Sum Net Value USD"),
        margin=dict(l=40, r=80, t=60, b=40),
        showlegend=False,
    )
    st.plotly_chart(fig_sec, width="stretch")
else:
    st.caption(tr("Brak danych sektorowych po filtrach."))

st.markdown("---")

# ---------------------------------------------------------------------------
# CROSS-LINK do Karty spolki (zakladka Akcjonariat = insiderzy)
# ---------------------------------------------------------------------------

st.markdown(tr("### 🏢 Karta spółki"))
col_sel, col_btn = st.columns([3, 1])
with col_sel:
    selected_ticker = st.selectbox(
        tr("Wybierz spółkę:"),
        options=[""] + filtered["ticker"].tolist(),
        key="insider_screener_card_select",
    )
with col_btn:
    st.write("")  # spacer
    go_btn = st.button(
        tr("Otwórz kartę spółki"),
        key="insider_screener_card_btn",
        disabled=not selected_ticker,
    )

if go_btn and selected_ticker:
    nav.go_company(selected_ticker)

st.markdown("---")

# ---------------------------------------------------------------------------
# CSV EXPORT
# ---------------------------------------------------------------------------

csv = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    tr("📥 Eksport CSV (screener)"),
    data=csv,
    file_name=f"insider_screener_sp500_{pd.Timestamp.now():%Y%m%d}.csv",
    mime="text/csv",
    key="insider_screener_csv",
)

render_footer()
