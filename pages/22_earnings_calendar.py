"""Strona 22: Earnings Calendar — nadchodzace + niedawne raporty.

Window: data.today() ± 28 dni.
Universe: SP500 (456) + GPW (121) = 577. ETF wykluczone (no earnings).

Spec: docs/superpowers/specs/2026-06-04-earnings-calendar-design.md
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_local_storage import LocalStorage

from components.auth import require_premium
from components.sidebar import setup_sidebar, render_footer
from components.watchlist import get_watchlist, toggle_ticker
from data.financials import (
    _detect_market,
    _status_badge,
    bulk_fetch_earnings_calendar,
)
from data.gpw_universe import ALL_GPW_TICKERS
from data.sp500_universe import ALL_SP500_TICKERS


# ---------------------------------------------------------------------------
# Module-level helpers (regula @st.fragment: PRZED `with tab:` blokiem)
# ---------------------------------------------------------------------------

def _navigate_to_deep_dive(ticker: str) -> None:
    """Przeskakuje do F13 deep dive dla wybranego tickera.

    Pattern session_state zgodny z F13 hotfix (commit b1f8502):
    osobna 'pending' flaga (nie widget key) + `st.switch_page`.
    """
    market = _detect_market(ticker)
    if market == "SP500":
        st.session_state["sp500_deep_dive_ticker"] = ticker
        st.session_state["sp500_pending_view"] = "deep_dive"
        st.switch_page("pages/7_sp500.py")
    elif market == "GPW":
        st.session_state["gpw_deep_dive_ticker"] = ticker
        st.session_state["gpw_pending_view"] = "deep_dive"
        st.switch_page("pages/8_gpw.py")
    else:
        st.warning(f"Deep dive niedostepny dla ETF/UNKNOWN ({ticker}).")


def _render_heatmap(df: pd.DataFrame, weeks_back: int = 3, weeks_fwd: int = 4) -> None:
    """Renderuje Plotly calendar heatmap 8 tygodni.

    Komorka = jeden dzien (Pon-Pt, weekendy ukryte).
    Kolor = ilosc raportow tego dnia (gold scale).
    Dzis = czerwona ramka.
    """
    today_norm = pd.Timestamp.now().normalize()
    start = today_norm - pd.Timedelta(weeks=weeks_back)
    end = today_norm + pd.Timedelta(weeks=weeks_fwd)

    # Aggregate: data -> lista tickerow
    by_day = df.groupby(df["date"].dt.normalize())["ticker"].apply(list).to_dict()

    # Build matrix: rows = tygodnie, cols = dni (Pon-Pt)
    matrix = []
    week_labels = []
    cell_data = []
    current_week_start = start - pd.Timedelta(days=start.weekday())  # poniedzialek

    while current_week_start <= end:
        row = []
        row_data = []
        for dow in range(5):  # Pon-Pt
            day = current_week_start + pd.Timedelta(days=dow)
            if day < start or day > end:
                row.append(None)
                row_data.append(None)
                continue
            tickers_for_day = by_day.get(day, [])
            row.append(len(tickers_for_day))
            row_data.append(tickers_for_day)

        # Label tygodnia: numer relatywny do dziś
        week_diff = (current_week_start - today_norm).days // 7
        week_labels.append(f"T{week_diff:+d}")
        matrix.append(row)
        cell_data.append(row_data)
        current_week_start += pd.Timedelta(weeks=1)

    # Hover text builder
    hover_text = []
    for week_row in cell_data:
        hover_row = []
        for cell_tickers in week_row:
            if cell_tickers is None or len(cell_tickers) == 0:
                hover_row.append("")
            else:
                preview = cell_tickers[:5]
                more = len(cell_tickers) - 5
                hover = f"{len(cell_tickers)} raporty:<br>" + "<br>".join(f"• {t}" for t in preview)
                if more > 0:
                    hover += f"<br>+ {more} wiecej"
                hover_row.append(hover)
        hover_text.append(hover_row)

    fig = go.Figure(go.Heatmap(
        z=matrix,
        x=["Pon", "Wt", "Sr", "Cz", "Pt"],
        y=week_labels,
        colorscale=[[0, "#1F2937"], [0.5, "#C9A84C"], [1, "#FFD700"]],
        showscale=True,
        colorbar=dict(title="Raporty"),
        hovertext=hover_text,
        hovertemplate="%{hovertext}<extra></extra>",
        zmin=0,
    ))

    # Dzis = ramka (annotacja)
    today_dow = today_norm.weekday()
    if today_dow < 5:  # tylko Pon-Pt
        try:
            t0_idx = week_labels.index("T+0")
            fig.add_shape(
                type="rect",
                x0=today_dow - 0.5, x1=today_dow + 0.5,
                y0=t0_idx - 0.5, y1=t0_idx + 0.5,
                line=dict(color="#EF4444", width=2),
                fillcolor="rgba(0,0,0,0)",
            )
        except ValueError:
            pass

    fig.update_layout(
        title="Kalendarz miesiecy — 8 tygodni (T-3 do T+4)",
        template="plotly_dark",
        height=400,
        yaxis=dict(autorange="reversed"),  # T-3 na gorze
        margin=dict(l=40, r=40, t=60, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def _apply_sort(df: pd.DataFrame, sort_by: str) -> pd.DataFrame:
    """Sortowanie tabeli wedlug wybranej opcji."""
    today_norm = pd.Timestamp.now().normalize()
    if sort_by == "Data (najblizej dzis)":
        df = df.copy()
        df["_abs_days"] = (df["date"] - today_norm).abs()
        return df.sort_values("_abs_days").drop(columns=["_abs_days"])
    if sort_by == "Data (chronologicznie)":
        return df.sort_values("date")
    if sort_by == "EPS surprise % (past)":
        return df.sort_values("eps_surprise_pct", ascending=False, na_position="last")
    if sort_by == "Ticker A-Z":
        return df.sort_values("ticker")
    return df


def _render_calendar_table(df: pd.DataFrame, watchlist_set: set[str], ls_obj) -> None:
    """Renderuje tabele st.data_editor z checkbox watchlist + CSV export.

    Po edycji checkboxa: diff vs current watchlist, toggle w localStorage,
    st.rerun() dla refresh state.
    """
    if df.empty:
        st.info("Brak wynikow po filtrach.")
        return

    df = df.copy()
    df["status"] = df.apply(
        lambda r: _status_badge(r["date"], r.get("eps_actual"), r.get("eps_estimate")),
        axis=1,
    )
    df["in_watchlist"] = df["ticker"].isin(watchlist_set)

    display_cols = [
        "in_watchlist", "ticker", "name", "market", "sector",
        "date", "q_label", "eps_estimate", "eps_actual",
        "eps_surprise_pct", "status",
    ]
    display = df[display_cols].copy()
    display = display.rename(columns={
        "in_watchlist": "⭐",
        "ticker": "Ticker",
        "name": "Nazwa",
        "market": "Market",
        "sector": "Sektor",
        "date": "Data",
        "q_label": "Q",
        "eps_estimate": "EPS est",
        "eps_actual": "EPS act",
        "eps_surprise_pct": "Δ%",
        "status": "Status",
    })

    # Edytowalny tylko ⭐
    disabled_cols = [c for c in display.columns if c != "⭐"]

    edited = st.data_editor(
        display,
        column_config={
            "⭐": st.column_config.CheckboxColumn("⭐", width="small"),
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Market": st.column_config.TextColumn("Market", width="small"),
            "Q": st.column_config.TextColumn("Q", width="small"),
            "EPS est": st.column_config.NumberColumn("EPS est", format="%.2f", width="small"),
            "EPS act": st.column_config.NumberColumn("EPS act", format="%.2f", width="small"),
            "Δ%": st.column_config.NumberColumn("Δ%", format="%+.1f%%", width="small"),
            "Data": st.column_config.DateColumn("Data", format="YYYY-MM-DD", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="medium"),
        },
        disabled=disabled_cols,
        hide_index=True,
        use_container_width=True,
        key="calendar_table",
    )

    # Diff toggles -> save do localStorage
    diff_mask = edited["⭐"] != display["⭐"]
    if diff_mask.any():
        for _, row in edited[diff_mask].iterrows():
            toggle_ticker(ls_obj, row["Ticker"])
        st.rerun()

    # CSV export
    csv = display.drop(columns=["⭐"]).to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Eksport CSV",
        data=csv,
        file_name="earnings_calendar.csv",
        mime="text/csv",
        key="calendar_csv",
    )


# ---------------------------------------------------------------------------
# Page config + auth + sidebar
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Earnings Calendar",
    page_icon="📅",
    layout="wide",
)
setup_sidebar()
if not require_premium(22):
    st.stop()

# Header
st.markdown("# 📅 Earnings Calendar")
st.caption(
    "Nadchodzace i niedawne raporty (±28 dni) dla SP500 + GPW. "
    "Kliknij ⭐ aby dodac spolke do watchlistu. "
    "ETF wykluczone — nie maja earnings."
)

# Universe
universe = tuple(ALL_SP500_TICKERS + ALL_GPW_TICKERS)

# Watchlist (localStorage)
ls = LocalStorage()
watchlist = get_watchlist(ls)

# ---------------------------------------------------------------------------
# FILTRY (expander)
# ---------------------------------------------------------------------------

with st.expander("Filtry", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        market_filter = st.radio(
            "Market",
            options=["Wszystkie", "SP500", "GPW"],
            horizontal=True,
            key="calendar_market",
        )
        status_filter = st.radio(
            "Status",
            options=["Wszystkie", "Future", "Past"],
            horizontal=True,
            key="calendar_status",
        )
    with col2:
        sector_filter = st.multiselect(
            "Sektor (multiselect)",
            options=[],  # populated po fetch
            default=[],
            key="calendar_sector",
        )
        only_watchlist = st.checkbox(
            "⭐ Tylko watchlist",
            value=False,
            disabled=len(watchlist) == 0,
            help="Watchlist pusty — kliknij ⭐ w tabeli aby dodac." if not watchlist else None,
            key="calendar_only_watchlist",
        )
    with col3:
        sort_by = st.selectbox(
            "Sort",
            options=[
                "Data (najblizej dzis)",
                "Data (chronologicznie)",
                "EPS surprise % (past)",
                "Ticker A-Z",
            ],
            index=0,
            key="calendar_sort",
        )
        refresh = st.button("🔄 Refresh cache", key="calendar_refresh")
        if refresh:
            st.cache_data.clear()
            st.rerun()

# ---------------------------------------------------------------------------
# BULK FETCH (cache 24h)
# ---------------------------------------------------------------------------

df = bulk_fetch_earnings_calendar(universe)

if df.empty:
    st.warning("Brak danych earnings w wybranym oknie ±28 dni.")
    render_footer()
    st.stop()

# ---------------------------------------------------------------------------
# APPLY FILTRY
# ---------------------------------------------------------------------------

filtered = df.copy()
if market_filter != "Wszystkie":
    filtered = filtered[filtered["market"] == market_filter]
if status_filter == "Future":
    filtered = filtered[filtered["is_future"]]
elif status_filter == "Past":
    filtered = filtered[~filtered["is_future"]]
if sector_filter:
    filtered = filtered[filtered["sector"].isin(sector_filter)]
if only_watchlist:
    filtered = filtered[filtered["ticker"].isin(watchlist)]

# ---------------------------------------------------------------------------
# SUMMARY CARDS (4 metryki)
# ---------------------------------------------------------------------------

total = len(df)
n_future = int(df["is_future"].sum())
today = pd.Timestamp.now().normalize()
n_this_week = int(((df["date"] >= today) & (df["date"] <= today + pd.Timedelta(days=7))).sum())
past_df = df[~df["is_future"]]
n_beat = int((past_df["eps_actual"] > past_df["eps_estimate"]).sum())
n_miss = int((past_df["eps_actual"] < past_df["eps_estimate"]).sum())
avg_surprise = past_df["eps_surprise_pct"].mean()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total ±28d", f"{total}")
c2.metric("Future (nadchodzace)", f"{n_future}", f"{n_this_week} w tym tyg.")
c3.metric(
    "Past Beat / Miss",
    f"{n_beat} / {n_miss}",
    f"{n_beat / (n_beat + n_miss) * 100:.0f}% beat" if (n_beat + n_miss) > 0 else "",
)
c4.metric("Avg surprise %", f"{avg_surprise:+.1f}%" if pd.notna(avg_surprise) else "—")

st.markdown("---")

# ---------------------------------------------------------------------------
# HEATMAPA (8 tygodni)
# ---------------------------------------------------------------------------

_render_heatmap(filtered)

st.markdown("---")

# ---------------------------------------------------------------------------
# TABELA (data_editor z checkbox watchlist)
# ---------------------------------------------------------------------------

st.markdown("### 📋 Tabela raportow")
sorted_df = _apply_sort(filtered, sort_by)
_render_calendar_table(sorted_df, watchlist, ls)

st.markdown("---")

# Placeholder dla Task 7 (cross-link)
st.info("🚧 Cross-link dodany w kolejnym tasku.")

render_footer()
