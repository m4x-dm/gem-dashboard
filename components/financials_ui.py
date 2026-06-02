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


# ---------------------------------------------------------------------------
# Deep dive (per ticker) — header + 4 karty + 4 sub-taby
# ---------------------------------------------------------------------------

def _format_statement_df(df: pd.DataFrame) -> pd.DataFrame:
    """Formatuje DF statementu: kolumny = etykiety Q/Y, wartosci B/M format.

    df: surowy yfinance DF, kolumny = Timestamp lub string.
    """
    from data.financials import _quarter_label

    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    # Kolumny: Timestamp -> "QX'YY" lub "YYYY" (jesli rok-end)
    new_cols = []
    for col in out.columns:
        try:
            ts = pd.Timestamp(col)
            # Roczne (Dec 31) -> "YYYY", kwartalne -> "QX'YY"
            if ts.month == 12 and ts.day == 31:
                new_cols.append(str(ts.year))
            else:
                new_cols.append(_quarter_label(ts))
        except Exception:
            new_cols.append(str(col))
    out.columns = new_cols
    # Format wartosci B/M
    out = out.applymap(
        lambda v: format_large_number(v) if isinstance(v, (int, float)) else v
    )
    return out


def _render_beat_miss_tab(ticker: str) -> None:
    """Sub-tab 1: Wykres bar EPS estimate vs actual + forward + rewizje."""
    from data.financials import _quarter_label

    earnings_df = get_earnings_history(ticker, n_quarters=8)
    trend_df = fetch_earnings_trend(ticker)

    if earnings_df is None or earnings_df.empty:
        st.warning(f"Brak danych earnings history dla {ticker}.")
        return

    # Wykres 1: EPS est vs actual (8 Q historia) + forward 4 punkty
    fig = go.Figure()
    x_hist = [_quarter_label(d) for d in earnings_df.index]
    fig.add_bar(
        x=x_hist, y=earnings_df.get("eps_estimate"),
        name="EPS Estimate",
        marker_color="rgba(201, 168, 76, 0.45)",  # gold light
    )
    fig.add_bar(
        x=x_hist, y=earnings_df.get("eps_actual"),
        name="EPS Actual",
        marker_color=GOLD,
    )

    if trend_df is not None and not trend_df.empty and "eps_current" in trend_df.columns:
        # yfinance index: 0q, +1q, 0y, +1y — pokazujemy jako "Fwd 0q" etc.
        x_fwd = [f"Fwd {idx}" for idx in trend_df.index]
        fig.add_bar(
            x=x_fwd, y=trend_df["eps_current"],
            name="Forward consensus",
            marker_color="rgba(201, 168, 76, 0.3)",
            marker_pattern_shape="/",
        )

    fig.update_layout(
        title="EPS: Estimate vs Actual (8Q historia + forward consensus)",
        barmode="group",
        template="plotly_dark",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabela rewizji
    if trend_df is not None and "eps_current" in trend_df.columns:
        cols_to_show = [
            c for c in [
                "eps_current", "eps_7d_ago", "eps_30d_ago",
                "eps_60d_ago", "eps_90d_ago", "revision_pct",
            ] if c in trend_df.columns
        ]
        if cols_to_show:
            rev_table = trend_df[cols_to_show].copy()
            rename_map = {
                "eps_current": "EPS now",
                "eps_7d_ago": "7d ago",
                "eps_30d_ago": "30d ago",
                "eps_60d_ago": "60d ago",
                "eps_90d_ago": "90d ago",
                "revision_pct": "Rewizja (now vs 30d) %",
            }
            rev_table = rev_table.rename(columns=rename_map)
            st.markdown("#### Rewizje konsensusu analitykow")
            st.dataframe(
                rev_table,
                use_container_width=True,
                column_config={
                    "Rewizja (now vs 30d) %": st.column_config.NumberColumn(
                        format="%+.1f%%"
                    ),
                },
            )


def _render_statement_tab(
    ticker: str,
    statement_key: str,  # "income_stmt" / "balance_sheet" / "cashflow"
    statement_label: str,
    rows_priority: list[str],
    key_prefix: str,
) -> None:
    """Wspolny renderer dla IS/BS/CF (DRY)."""
    period = st.radio(
        "Okres",
        options=["Kwartalne 8Q", "Roczne 4Y"],
        horizontal=True,
        key=f"{key_prefix}_period_{ticker}",
    )
    if period == "Kwartalne 8Q":
        stmts = fetch_quarterly_statements(ticker, n_quarters=8)
    else:
        stmts = fetch_annual_statements(ticker, n_years=4)

    if stmts is None or stmts.get(statement_key) is None or stmts[statement_key].empty:
        st.warning(f"Brak danych {statement_label} dla {ticker}.")
        return

    df = stmts[statement_key]

    # Wybor wierszy: priority + reszta max 10
    available = [r for r in rows_priority if r in df.index]
    other = [r for r in df.index if r not in available]
    final_rows = available + other[:10]
    final_rows = [r for r in final_rows if r in df.index]  # safety

    if not final_rows:
        st.warning(f"Brak rozpoznawalnych wierszy w {statement_label}.")
        st.dataframe(_format_statement_df(df), use_container_width=True)
        return

    display_df = _format_statement_df(df.loc[final_rows])
    st.dataframe(display_df, use_container_width=True)


def _render_income_statement_tab(ticker: str) -> None:
    """Sub-tab 2: IS kwartalne 8Q + roczne 4Y."""
    rows_priority = [
        "Total Revenue", "Cost Of Revenue", "Gross Profit",
        "Operating Income", "Operating Expense",
        "Pretax Income", "Tax Provision", "Net Income",
        "Basic EPS", "Diluted EPS",
    ]
    _render_statement_tab(
        ticker, "income_stmt", "Income Statement",
        rows_priority, "is",
    )


def _render_balance_sheet_tab(ticker: str) -> None:
    """Sub-tab 3: BS."""
    rows_priority = [
        "Total Assets", "Current Assets", "Cash And Cash Equivalents",
        "Total Liabilities Net Minority Interest", "Current Liabilities",
        "Long Term Debt", "Common Stock Equity",
        "Total Equity Gross Minority Interest",
    ]
    _render_statement_tab(
        ticker, "balance_sheet", "Balance Sheet",
        rows_priority, "bs",
    )


def _render_cashflow_tab(ticker: str) -> None:
    """Sub-tab 4: CF. Banki GPW: ukryte FCF."""
    rows_priority = [
        "Operating Cash Flow", "Investing Cash Flow", "Financing Cash Flow",
        "Free Cash Flow", "Capital Expenditure",
        "Cash Dividends Paid", "Repurchase Of Capital Stock",
    ]
    if is_bank(ticker):
        rows_priority = [r for r in rows_priority if "Free Cash Flow" not in r]
    _render_statement_tab(
        ticker, "cashflow", "Cash Flow",
        rows_priority, "cf",
    )


def render_sprawozdania_deep_dive(ticker: str, market: str) -> None:
    """Renderuje deep dive: header + 4 karty + 4 sub-taby."""
    from data.financials import _compute_beat_streak, _quarter_label

    if not ticker:
        st.info("Wybierz ticker w screenerze i kliknij 'Pokaz szczegoly'.")
        return

    # HEADER
    ratios = get_ratios_snapshot(ticker)
    name = ratios.get("name") or ticker
    sector = ratios.get("sector") or "—"
    mcap = format_large_number(ratios.get("market_cap"))
    st.markdown(f"### 🏢 {name} ({ticker})  ·  {sector}  ·  Cap: {mcap}")

    # 4 KARTY METRYK (2 wiersze x 2 kolumny)
    earnings_df = get_earnings_history(ticker, n_quarters=8)
    trend_df = fetch_earnings_trend(ticker)

    last_q = ""
    eps_est = float("nan")
    eps_act = float("nan")
    surprise = float("nan")
    streak = 0
    if earnings_df is not None and not earnings_df.empty:
        last_row = earnings_df.iloc[-1]
        last_q = _quarter_label(earnings_df.index[-1])
        eps_est = last_row.get("eps_estimate", float("nan"))
        eps_act = last_row.get("eps_actual", float("nan"))
        surprise = last_row.get("surprise_pct", float("nan"))
        streak = _compute_beat_streak(earnings_df)

    fwd_eps = float("nan")
    fwd_growth = float("nan")
    fwd_rev = float("nan")
    if trend_df is not None and not trend_df.empty and "+1q" in trend_df.index:
        fwd_eps = trend_df.loc["+1q"].get("eps_current", float("nan"))
        fwd_growth = trend_df.loc["+1q"].get("eps_growth_yoy", float("nan"))
        fwd_rev = trend_df.loc["+1q"].get("rev_estimate", float("nan"))

    c1, c2 = st.columns(2)
    with c1:
        st.metric(
            f"{last_q or 'Last'} EPS",
            f"{eps_act:.2f}" if pd.notna(eps_act) else "—",
            f"vs est {eps_est:.2f} ({surprise:+.1f}%)" if pd.notna(surprise) else "",
        )
    with c2:
        st.metric("Beat streak", f"{streak} Q")

    c3, c4 = st.columns(2)
    with c3:
        st.metric(
            "Forward Q+1 EPS",
            f"{fwd_eps:.2f}" if pd.notna(fwd_eps) else "—",
            f"YoY {fwd_growth*100:+.1f}%" if pd.notna(fwd_growth) else "",
        )
    with c4:
        st.metric(
            "Forward Q+1 Revenue",
            format_large_number(fwd_rev) if pd.notna(fwd_rev) else "—",
        )

    st.markdown("---")

    # 4 SUB-TABY
    sub1, sub2, sub3, sub4 = st.tabs([
        "📊 Beat/Miss historia",
        "📑 Income Statement",
        "💰 Balance Sheet",
        "💵 Cash Flow",
    ])
    with sub1:
        _render_beat_miss_tab(ticker)
    with sub2:
        _render_income_statement_tab(ticker)
    with sub3:
        _render_balance_sheet_tab(ticker)
    with sub4:
        _render_cashflow_tab(ticker)
