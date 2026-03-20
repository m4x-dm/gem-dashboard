"""Strona 3: Wykresy — cena, momentum, drawdown."""

import streamlit as st
from components.sidebar import setup_sidebar, render_footer
from data.etf_universe import ALL_TICKERS, ETF_NAMES
from data.downloader import download_prices
from components.charts import price_chart, momentum_chart, drawdown_chart
from components.auth import require_premium

st.set_page_config(page_title="Wykresy", page_icon="📉", layout="wide")
setup_sidebar()
if not require_premium(3): st.stop()

st.markdown("# 📉 Wykresy")

# Wybor ETF-ow
available = ALL_TICKERS + st.session_state.get("custom_tickers", [])
options = {t: f"{t} — {ETF_NAMES.get(t, t)}" for t in available}

selected = st.multiselect(
    "Wybierz ETF-y (maks. 5)",
    options=list(options.keys()),
    default=["QQQ", "VEA", "AGG"],
    format_func=lambda x: options[x],
    max_selections=5,
)

# Okres
period_map = {
    "Strategia 12-1": "2y",
    "1 miesiac": "1mo",
    "3 miesiace": "3mo",
    "6 miesiecy": "6mo",
    "1 rok": "1y",
    "2 lata": "2y",
    "5 lat": "5y",
    "10 lat": "10y",
    "Maksymalny": "max",
}
period_label = st.selectbox("Okres", list(period_map.keys()), index=0)
period = period_map[period_label]
is_strategy_view = period_label == "Strategia 12-1"

_ok = True
if not selected:
    st.info("Wybierz co najmniej 1 ETF.")
    _ok = False

if _ok:
    # Pobierz dane — dla Strategii 12-1 pobierz wiecej, zeby momentum mialo z czego liczyc
    dl_period = "5y" if is_strategy_view else period
    prices_full = download_prices(selected, period=dl_period)

    # Strategia 12-1: przytnij do okna 13M-1M wstecz dla ceny/drawdown
    if is_strategy_view and len(prices_full) > 273:
        prices = prices_full.iloc[-273:-21]
    elif is_strategy_view:
        st.warning("Za malo danych dla widoku Strategia 12-1. Wyswietlam dostepne dane.")
        prices = prices_full
    else:
        prices = prices_full

    if prices.empty:
        st.error("Nie udalo sie pobrac danych.")
        _ok = False

if _ok:
    # Zakladki
    tab1, tab2, tab3 = st.tabs(["📈 Cena", "🚀 Momentum", "📉 Drawdown"])

    with tab1:
        normalize = st.checkbox("Normalizuj (baza = 100)", value=True)
        title = "Cena znormalizowana (baza = 100)" if normalize else "Cena (USD)"
        fig = price_chart(prices, title=title, normalize=normalize)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        # Momentum uzywa pelnych danych (nie przycinanych), zeby rolling mial wystarczajaco historii
        mom_data = prices_full if is_strategy_view else prices
        max_window = min(504, len(mom_data) - 1) if len(mom_data) > 21 else 21
        default_window = min(252, max_window)
        window = st.slider("Okno momentum (dni)", 21, max_window, default_window, step=21)
        fig = momentum_chart(mom_data, window=window, title=f"Momentum {window}D (rolling)")
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        fig = drawdown_chart(prices)
        st.plotly_chart(fig, use_container_width=True)

render_footer()
