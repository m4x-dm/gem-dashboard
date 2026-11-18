"""Karta spolki — zakladka Akcjonariat: akcjonariusze, fundusze, transakcje insiderow."""
import streamlit as st

from components import financials_ui as fu
from components.i18n import tr


def render(ticker, market):
    st.markdown(tr("### Akcjonariat i transakcje insiderów"))
    if market == "GPW":
        st.caption(tr("Dla spółek GPW dane yfinance bywają niepełne; raporty bieżące: gpw.pl/komunikaty-spolek."))
    fu._render_insiders_tab(ticker)
