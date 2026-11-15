"""GEM ETF Dashboard — router (gorne menu z sekcjami).

Strony definiuje components/nav.py. Router raz ustawia konfiguracje,
sidebar i Premium, a przed uruchomieniem strony sprawdza dostep.
"""
import streamlit as st

from components import nav
from components.auth import is_premium, render_lock_screen
from components.sidebar import setup_sidebar, render_footer

st.set_page_config(
    page_title="GEM ETF Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="auto",
)

setup_sidebar()

pg = st.navigation(nav.build_navigation(), position="top")

page = nav.by_title(pg.title)

if page is not None and not page.free and not is_premium():
    render_lock_screen(page.icon, page.title, page.description)
    render_footer()
else:
    pg.run()
