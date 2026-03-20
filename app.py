"""GEM ETF Dashboard — entrypoint."""

import streamlit as st
from components.sidebar import setup_sidebar, render_footer
from components.auth import is_premium, FREE_PAGES

st.set_page_config(
    page_title="GEM ETF Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

setup_sidebar()

# Strona glowna
st.markdown("# 📈 GEM ETF Dashboard")
st.markdown("Kliknij kafelek, aby przejsc do wybranej zakladki.")

# Definicje kart: (indeks strony, ikona, tytul, opis, plik strony)
cards = [
    (0, "🏠", "Podsumowanie", "Centrum dowodzenia — sygnal GEM, regime, top ETF-y, sparklines", "pages/0_podsumowanie.py"),
    (1, "🎯", "Sygnal GEM", "Aktualny sygnal klasycznego GEM + top 5 ETF-ow wg momentum", "pages/1_sygnal_gem.py"),
    (2, "📊", "Ranking", "Tabela rankingowa 30+ ETF-ow z wynikiem momentum", "pages/2_ranking.py"),
    (3, "📈", "Wykresy", "Cena, momentum i drawdown dla wybranych ETF-ow", "pages/3_wykresy.py"),
    (4, "⚖️", "Porownanie", "Head-to-head 2-4 ETF-ow + macierz korelacji", "pages/4_porownanie.py"),
    (5, "🔬", "Backtest", "GEM vs Buy&Hold — krzywa kapitalu i statystyki", "pages/5_backtest.py"),
    (6, "📖", "O strategii", "Opis strategii GEM Gary'ego Antonacciego", "pages/6_info.py"),
    (7, "🇺🇸", "S&P 500", "Ranking, wykresy i backtest ~500 spolek z indeksu S&P 500", "pages/7_sp500.py"),
    (8, "🇵🇱", "Polskie Akcje GPW", "140 spolek z WIG20, mWIG40 i sWIG80", "pages/8_gpw.py"),
    (9, "🪙", "Kryptowaluty", "Top 200 kryptowalut — ranking, alt/BTC ratio, backtest", "pages/9_kryptowaluty.py"),
    (10, "🏗️", "Portfolio Builder", "Zbuduj portfel, ustaw wagi, backtest i analiza korelacji", "pages/10_portfolio.py"),
    (11, "🔎", "Screener", "Cross-asset ranking momentum ze wszystkich klas aktywow", "pages/11_screener.py"),
    (12, "🌍", "Makro Dashboard", "VIX, yield curve, DXY, S&P+200MA, zloto, ropa", "pages/12_makro.py"),
    (13, "📅", "Sezonowosc", "Heatmapa miesięcznych zwrotow, wzorce sezonowe, Sell in May", "pages/13_sezonowosc.py"),
    (14, "💱", "Waluta PLN/USD", "Wplyw kursu USD/PLN na zwroty ETF-ow", "pages/14_waluta.py"),
    (15, "📉", "Drawdowny", "Analiza spadkow od szczytu, czas trwania i odbudowy", "pages/15_drawdown.py"),
    (16, "🚦", "Historia Sygnalow", "Pelna historia zmian sygnalu GEM w czasie", "pages/16_sygnaly.py"),
    (17, "🎲", "Monte Carlo", "Symulacja przyszlych zwrotow — ile mozesz miec za N lat?", "pages/17_monte_carlo.py"),
    (18, "🔄", "Rotacja Sektorowa", "Ktory sektor GICS prowadzi? Heatmapa momentum sektorow", "pages/18_sektory.py"),
    (19, "🔗", "Intermarket", "Relacje miedzy klasami aktywow: akcje, obligacje, zloto, dolar", "pages/19_intermarket.py"),
]

premium = is_premium()

# Grid 3 kolumny — karty z page_link wewnatrz
for row_start in range(0, len(cards), 3):
    row = cards[row_start:row_start + 3]
    cols = st.columns(3)
    for col, (idx, icon, title, desc, page) in zip(cols, row):
        is_free = idx in FREE_PAGES
        locked = not is_free and not premium
        with col:
            ct = st.container(border=True)
            with ct:
                if locked:
                    st.markdown(
                        f'<div style="font-size:28px;margin-bottom:4px;">{icon} '
                        f'<span style="font-size:14px;color:#C9A84C;vertical-align:middle;">🔒 PREMIUM</span></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(f'<div style="font-size:28px;margin-bottom:4px;">{icon}</div>', unsafe_allow_html=True)
                st.page_link(page, label=f"**{title}**", use_container_width=True)
                st.caption(desc)

# CSS — stylowanie kart
st.markdown("""
<style>
    /* Kontenery kart na homepage */
    div[data-testid="stExpander"],
    div.stContainer > div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #141929 !important;
        border: 1px solid rgba(201,168,76,0.25) !important;
        border-radius: 12px !important;
        transition: border-color 0.2s, transform 0.2s;
    }
    div.stContainer > div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #C9A84C !important;
        transform: translateY(-3px);
    }
    /* Page link w kartach — gold color */
    div[data-testid="stVerticalBlockBorderWrapper"] a[data-testid="stPageLink-NavLink"] {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] a[data-testid="stPageLink-NavLink"] span {
        color: #C9A84C !important;
        font-size: 15px !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] a[data-testid="stPageLink-NavLink"]:hover span {
        color: #E5C66E !important;
    }
</style>
""", unsafe_allow_html=True)

render_footer()
