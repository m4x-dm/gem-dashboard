"""Karta spolki — zakladka Finanse: wskazniki, konsensus, historia EPS, rekomendacje."""
import streamlit as st

from components.cards import (
    ratios_card, forward_consensus_card, earnings_history_card, analyst_recos_card,
)
from data.financials import (
    get_ratios_snapshot, get_forward_consensus, get_earnings_history, get_analyst_recos,
)
from data.gpw_universe import GPW_BANKS


def render(ticker, market):
    is_bank = market == "GPW" and ticker in GPW_BANKS
    st.markdown("### Wskaźniki finansowe i konsensus analityków")
    if market == "GPW":
        st.info(
            "Część wskaźników jest niedostępna dla mniejszych spółek lub sektora bankowego "
            "(EBITDA / EV-EBITDA / FCF). Konsensus analityków jest typowo dostępny dla WIG20 "
            "i większych spółek mWIG40."
        )
    if is_bank:
        st.caption("Bank — EBITDA, EV/EBITDA i FCF ukryte.")
    st.caption("Dane z yfinance, cache 24h. Brakujące wskaźniki oznaczone „—”.")

    with st.spinner(f"Pobieram dane finansowe dla {ticker}..."):
        snap = get_ratios_snapshot(ticker)
        cons = get_forward_consensus(ticker)
        hist = get_earnings_history(ticker)
        recos = get_analyst_recos(ticker)

    col1, col2 = st.columns(2)
    with col1:
        ratios_card(snap, is_bank=is_bank)
    with col2:
        forward_consensus_card(cons)

    col3, col4 = st.columns(2)
    with col3:
        earnings_history_card(hist)
    with col4:
        analyst_recos_card(recos)
