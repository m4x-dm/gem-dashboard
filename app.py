"""GEM ETF Dashboard — router (gorne menu z sekcjami).

Strony definiuje components/nav.py. Router raz ustawia konfiguracje,
sidebar i Premium, a przed uruchomieniem strony sprawdza dostep.
"""
import streamlit as st

from components import nav
from components.i18n import init_lang, install_table_translation
from components.auth import is_premium, render_lock_screen
from components.sidebar import setup_sidebar, render_footer

st.set_page_config(
    page_title="GEM ETF Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="auto",
)

# st.navigation MUSI byc przed setup_sidebar(): komponent localStorage w init_auth()
# wywoluje rerun, ktory przed zbudowaniem nawigacji gubi strone z adresu URL
# (bezposredni link, np. /ranking, otwieral Pulpit). Zweryfikowane 2026-11-15.
# Jezyk przed nawigacja: tytuly stron w menu sa tlumaczone (?lang=en).
init_lang()
install_table_translation()

pg = st.navigation(nav.build_navigation(), position="top")

setup_sidebar()

free, icon, title, description = nav.access_info(pg.title)

if not free and not is_premium():
    render_lock_screen(icon, title, description)
    render_footer()
else:
    pg.run()
