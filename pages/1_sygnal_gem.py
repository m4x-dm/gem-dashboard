"""Strona 1: Sygnal GEM — aktualny sygnal + top 5."""

import streamlit as st
from components.sidebar import setup_sidebar, get_risk_free, render_footer
from data.etf_universe import ALL_TICKERS, ETF_NAMES, ETF_CATEGORY_MAP
from data.downloader import download_prices
from data.momentum import gem_classic_signal, build_ranking
from components.cards import signal_card, metric_row, top_etf_cards
from components.charts import ranking_bar_chart

st.set_page_config(page_title="Sygnal GEM", page_icon="🎯", layout="wide")
setup_sidebar()

st.markdown("# 🎯 Sygnal GEM")

# Pobierz dane
tickers = list(set(ALL_TICKERS + st.session_state.get("custom_tickers", [])))
prices = download_prices(tickers)

rf = get_risk_free()

# Klasyczny GEM
gem_data = gem_classic_signal(prices, rf)

st.markdown("### Klasyczny GEM (QQQ / VEA / EEM / ACWI / AGG)")
signal_card(gem_data)
metric_row(gem_data["qqq_12m"], gem_data["vea_12m"], gem_data["eem_12m"], gem_data["acwi_12m"], gem_data["agg_12m"], rf)

st.divider()

# Rozszerzony ranking
st.markdown("### Top 5 ETF-ow — rozszerzony ranking momentum")
ranking = build_ranking(prices, rf)

# Nazwy dla custom tickerow
custom = st.session_state.get("custom_tickers", [])
names = dict(ETF_NAMES)
categories = dict(ETF_CATEGORY_MAP)
for t in custom:
    names.setdefault(t, t)
    categories.setdefault(t, "Wlasne")

valid_ranking = ranking.dropna(subset=["Wynik"])
if not valid_ranking.empty:
    top_etf_cards(valid_ranking, names, categories, n=5)

    st.divider()
    st.markdown("### Top 10 — wykres momentum")
    fig = ranking_bar_chart(valid_ranking, top_n=10)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Brak danych do wyswietlenia rankingu.")

# Info
with st.expander("Jak czytac sygnal GEM?"):
    st.markdown("""
    **Klasyczny GEM** analizuje 5 aktywow:
    1. Jesli zwrot QQQ 12M < stopa wolna → **kup obligacje (AGG)**
    2. Jesli momentum dodatni → **kup najlepszy z QQQ / VEA / EEM / ACWI** (porownanie relatywne)

    **Momentum 12-1 (skip-month):** zwrot 12M jest liczony od 13 mies. wstecz do 1 mies. wstecz,
    pomijajac ostatni miesiac. To eliminuje efekt krotkoterminowej rewersji (short-term reversal).

    **Rozszerzony ranking** oblicza wynik kompozytowy:
    `12M × 50% + 6M × 25% + 3M × 15% + 1M × 10%`

    **Momentum absolutny:** TAK = zwrot 12M (skip-month) > stopa wolna od ryzyka
    """)

render_footer()
