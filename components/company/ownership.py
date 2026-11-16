"""Karta spolki — zakladka Akcjonariat: akcjonariusze, fundusze, transakcje insiderow."""
import streamlit as st

from components import financials_ui as fu


def render(ticker, market):
    st.markdown("### Akcjonariat i transakcje insiderów")
    if market == "GPW":
        st.caption("Dla spółek GPW dane yfinance bywają niepełne; raporty bieżące: gpw.pl/komunikaty-spolek.")
    fu._render_insiders_tab(ticker)
