"""Karta spolki — zakladka Wyniki: beat/miss, rachunek zyskow i strat, bilans, przeplywy."""
import pandas as pd
import streamlit as st

from components import financials_ui as fu
from data.financials import (
    _compute_beat_streak, _quarter_label, fetch_earnings_trend, format_large_number,
    get_earnings_history,
)
from components.i18n import tr


def _summary_metrics(ticker: str) -> None:
    earnings_df = get_earnings_history(ticker, n_quarters=8)
    trend_df = fetch_earnings_trend(ticker)

    last_q = ""
    eps_est = eps_act = surprise = float("nan")
    streak = 0
    if earnings_df is not None and not earnings_df.empty:
        last_row = earnings_df.iloc[-1]
        last_q = _quarter_label(earnings_df.index[-1])
        eps_est = last_row.get("eps_estimate", float("nan"))
        eps_act = last_row.get("eps_actual", float("nan"))
        surprise = last_row.get("surprise_pct", float("nan"))
        streak = _compute_beat_streak(earnings_df)

    fwd_eps = fwd_growth = fwd_rev = float("nan")
    if trend_df is not None and not trend_df.empty and "+1q" in trend_df.index:
        fwd_eps = trend_df.loc["+1q"].get("eps_current", float("nan"))
        fwd_growth = trend_df.loc["+1q"].get("eps_growth_yoy", float("nan"))
        fwd_rev = trend_df.loc["+1q"].get("rev_estimate", float("nan"))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            f"EPS {last_q}".strip() if last_q else tr("Ostatni EPS"),
            f"{eps_act:.2f}" if pd.notna(eps_act) else "—",
            tr("vs prognoza {est} ({surprise}%)", est=f"{eps_est:.2f}", surprise=f"{surprise:+.1f}")
            if pd.notna(surprise) and pd.notna(eps_est) else "",
        )
    with c2:
        st.metric(tr("Seria wyników powyżej prognoz"), tr("{n} kw.", n=streak))
    with c3:
        st.metric(
            tr("Prognoza EPS Q+1"),
            f"{fwd_eps:.2f}" if pd.notna(fwd_eps) else "—",
            tr("r/r {pct}%", pct=f"{fwd_growth*100:+.1f}") if pd.notna(fwd_growth) else "",
        )
    with c4:
        st.metric(tr("Prognoza przychodów Q+1"),
                  format_large_number(fwd_rev) if pd.notna(fwd_rev) else "—")


def render(ticker, market):
    if market == "GPW":
        st.caption(tr("Część spółek GPW (small-cap) nie ma pełnych danych w yfinance — luki są oczekiwane."))
    try:
        _summary_metrics(ticker)
    except Exception:
        st.caption(tr("Podsumowanie wyników: dane chwilowo niedostępne"))
    t1, t2, t3, t4 = st.tabs([tr("Beat/miss"), tr("Rachunek zysków i strat"), tr("Bilans"), tr("Przepływy")])
    with t1:
        fu._render_beat_miss_tab(ticker)
    with t2:
        fu._render_income_statement_tab(ticker)
    with t3:
        fu._render_balance_sheet_tab(ticker)
    with t4:
        fu._render_cashflow_tab(ticker)
