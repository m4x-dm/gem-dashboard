"""Render helpery dla tab 'Sprawozdania Q' w pages/7_sp500.py + 8_gpw.py.

Modul jest importowany przez pages — helpery musza byc na poziomie modulu
przed `with tab:` blokiem (regula z F12 screener, commit d7c3407).
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.constants import GOLD, GREEN, RED
from data.financials import (
    bulk_fetch_earnings_history,
    fetch_annual_statements,
    fetch_earnings_trend,
    fetch_quarterly_statements,
    format_currency,
    format_large_number,
    get_earnings_history,
    get_forward_consensus,
    get_ratios_snapshot,
    is_bank,
)


# ---------------------------------------------------------------------------
# Screener (bulk view, ~570-620 spolek)
# ---------------------------------------------------------------------------

def render_sprawozdania_screener(
    universe: list[str],
    market: str,  # "SP500" lub "GPW"
) -> str | None:
    """Renderuje screener bulk earnings (filtry + tabela + summary cards).

    Returns: ticker wybrany do deep dive, lub None gdy user nie wybral.
    """
    st.markdown("### 🔍 Screener — beat/miss ostatniego kwartalu")

    # FILTRY (expander)
    with st.expander("Filtry", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            beat_status = st.radio(
                "Beat status",
                options=["Wszystkie", "Beat EPS", "Miss EPS"],
                index=0,
                horizontal=True,
                key=f"{market}_beat_status",
            )
            min_surprise = st.slider(
                "Min EPS surprise %",
                min_value=-50.0, max_value=50.0, value=-50.0, step=5.0,
                key=f"{market}_min_surprise",
            )
        with col2:
            min_streak = st.slider(
                "Min beat streak (Q)",
                min_value=0, max_value=8, value=0,
                key=f"{market}_min_streak",
            )
            top_n = st.selectbox(
                "Top N",
                options=[10, 25, 50, 100, 250],
                index=2,
                key=f"{market}_top_n",
            )
        with col3:
            sort_by = st.selectbox(
                "Sort by",
                options=[
                    "eps_surprise_pct",
                    "beat_streak",
                    "eps_actual",
                    "ticker",
                ],
                index=0,
                key=f"{market}_sort_by",
            )
            sort_desc = st.checkbox(
                "Malejaco", value=True, key=f"{market}_sort_desc"
            )
            refresh = st.button("🔄 Odswiez cache", key=f"{market}_refresh")
            if refresh:
                st.cache_data.clear()
                st.rerun()

    # BULK FETCH
    df = bulk_fetch_earnings_history(tuple(universe))

    if df.empty:
        st.warning("Brak danych dla universe.")
        return None

    # FILTRY apply
    filtered = df.copy()
    if beat_status == "Beat EPS":
        filtered = filtered[filtered["eps_surprise_pct"] > 0]
    elif beat_status == "Miss EPS":
        filtered = filtered[filtered["eps_surprise_pct"] < 0]
    filtered = filtered[filtered["eps_surprise_pct"].fillna(-999) >= min_surprise]
    filtered = filtered[filtered["beat_streak"] >= min_streak]
    filtered = filtered.sort_values(by=sort_by, ascending=not sort_desc).head(top_n)

    # SUMMARY CARDS (4 metryki)
    total = len(df)
    beat_eps = int((df["eps_surprise_pct"] > 0).sum())
    miss_eps = int((df["eps_surprise_pct"] < 0).sum())
    avg_surprise = df["eps_surprise_pct"].mean()
    avg_streak = df["beat_streak"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Beat EPS", f"{beat_eps}/{total}", f"{beat_eps/total*100:.0f}%" if total else "")
    c2.metric("Miss EPS", f"{miss_eps}/{total}", f"{miss_eps/total*100:.0f}%" if total else "")
    c3.metric(
        "Avg surprise %",
        f"{avg_surprise:+.1f}%" if pd.notna(avg_surprise) else "—",
    )
    c4.metric(
        "Avg streak (Q)",
        f"{avg_streak:.1f}" if pd.notna(avg_streak) else "—",
    )

    # TABELA
    st.markdown(f"#### Wyniki ({len(filtered)} spolek)")

    display = filtered.rename(columns={
        "ticker": "Ticker",
        "last_q_label": "Q",
        "eps_estimate": "EPS est",
        "eps_actual": "EPS act",
        "eps_surprise_pct": "EPS Δ%",
        "beat_streak": "Streak",
    })

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "EPS est": st.column_config.NumberColumn(format="%.2f"),
            "EPS act": st.column_config.NumberColumn(format="%.2f"),
            "EPS Δ%": st.column_config.NumberColumn(format="%+.1f%%"),
            "Streak": st.column_config.ProgressColumn(
                min_value=0, max_value=8, format="%d Q",
            ),
        },
    )

    # DEEP DIVE SELECT + AKCJE
    st.markdown("---")
    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        selected = st.selectbox(
            "Wybierz ticker do deep dive",
            options=[""] + filtered["ticker"].tolist(),
            key=f"{market}_deep_dive_select",
        )
    with col_btn:
        st.write("")  # spacer
        go_btn = st.button(
            "📈 Pokaz szczegoly",
            key=f"{market}_deep_dive_btn",
            disabled=not selected,
        )

    # CSV EXPORT
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Eksport CSV (screener)",
        data=csv,
        file_name=f"sprawozdania_screener_{market}.csv",
        mime="text/csv",
        key=f"{market}_csv_screener",
    )

    if go_btn and selected:
        return selected
    return None
