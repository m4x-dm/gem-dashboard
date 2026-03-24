"""Strona 20: Side-by-Side — porownanie dwoch aktywow obok siebie."""

import streamlit as st
import pandas as pd
from components.sidebar import setup_sidebar, get_risk_free, render_footer
from data.etf_universe import ALL_TICKERS, ETF_NAMES, ETF_CATEGORY_MAP
from data.sp500_universe import ALL_SP500_TICKERS, SP500_NAMES, SP500_SECTOR_MAP
from data.gpw_universe import ALL_GPW_TICKERS, GPW_NAMES, GPW_CATEGORY_MAP
from data.crypto_universe import CRYPTO_BY_MCAP, CRYPTO_NAMES, CRYPTO_CATEGORY_MAP
from data.downloader import download_prices
from data.momentum import (
    latest_returns, calc_stats, correlation_matrix, relative_strength,
)
from components.formatting import fmt_pct, color_for_value, MUTED, BG_CARD, BORDER
from components.charts import (
    price_chart, drawdown_chart, correlation_heatmap, rs_chart,
)
from components.cards import comparison_card, stats_table
from components.auth import require_premium

st.set_page_config(page_title="Side-by-Side", page_icon="🔀", layout="wide")
setup_sidebar()
if not require_premium(20): st.stop()

st.markdown("# 🔀 Side-by-Side")
st.caption("Porownaj dwa aktywa obok siebie — cena, drawdown, statystyki i Relative Strength")

# --- Polaczony universe ---
all_names = {**ETF_NAMES, **SP500_NAMES, **GPW_NAMES, **CRYPTO_NAMES}
all_categories = {**ETF_CATEGORY_MAP, **SP500_SECTOR_MAP, **GPW_CATEGORY_MAP, **CRYPTO_CATEGORY_MAP}

# Top aktywa (zredukowana lista dla szybkosci)
top_tickers = (
    ALL_TICKERS
    + ALL_SP500_TICKERS[:50]
    + ALL_GPW_TICKERS[:30]
    + CRYPTO_BY_MCAP[:30]
    + st.session_state.get("custom_tickers", [])
)
# Usun duplikaty zachowujac kolejnosc
seen = set()
unique_tickers = []
for t in top_tickers:
    if t not in seen:
        seen.add(t)
        unique_tickers.append(t)

options_map = {t: f"{t} — {all_names.get(t, t)}" for t in unique_tickers}

# --- Selektory ---
col_a, col_b, col_period = st.columns([2, 2, 1])
with col_a:
    ticker_a = st.selectbox("Aktywo A", unique_tickers, index=0,
                            format_func=lambda x: options_map[x], key="sbs_a")
with col_b:
    default_b = min(1, len(unique_tickers) - 1)
    ticker_b = st.selectbox("Aktywo B", unique_tickers, index=default_b,
                            format_func=lambda x: options_map[x], key="sbs_b")
with col_period:
    period_map = {
        "6 miesiecy": "6mo", "1 rok": "1y", "2 lata": "2y",
        "5 lat": "5y", "10 lat": "10y", "Maksymalny": "max",
    }
    period_label = st.selectbox("Okres", list(period_map.keys()), index=2, key="sbs_period")
    period = period_map[period_label]

if ticker_a == ticker_b:
    st.warning("Wybierz dwa rozne aktywa.")
    st.stop()

# --- Pobierz dane ---
with st.spinner("Pobieram dane..."):
    prices = download_prices([ticker_a, ticker_b], period=period)

if prices.empty or ticker_a not in prices.columns or ticker_b not in prices.columns:
    st.error("Nie udalo sie pobrac danych dla wybranych aktywow.")
    st.stop()

rf = get_risk_free()
rf_decimal = rf / 100.0
rets = latest_returns(prices)

# --- Karty porownawcze ---
col_left, col_right = st.columns(2)
for col, ticker in [(col_left, ticker_a), (col_right, ticker_b)]:
    with col:
        r = rets.loc[ticker] if ticker in rets.index else pd.Series()
        comparison_card(
            ticker, all_names.get(ticker, ticker),
            all_categories.get(ticker, ""), r, 0 if ticker == ticker_a else 1,
        )

st.divider()

# --- Side-by-side: Cena + Drawdown ---
col_left, col_right = st.columns(2)

with col_left:
    st.markdown(f"#### {ticker_a}")
    fig = price_chart(prices[[ticker_a]], title=f"Cena — {ticker_a}", normalize=True)
    st.plotly_chart(fig, use_container_width=True)
    fig = drawdown_chart(prices[[ticker_a]], title=f"Drawdown — {ticker_a}")
    st.plotly_chart(fig, use_container_width=True)

    s_a = calc_stats(prices[ticker_a].dropna(), 252, rf_decimal)
    stats_table({ticker_a: s_a})

with col_right:
    st.markdown(f"#### {ticker_b}")
    fig = price_chart(prices[[ticker_b]], title=f"Cena — {ticker_b}", normalize=True)
    st.plotly_chart(fig, use_container_width=True)
    fig = drawdown_chart(prices[[ticker_b]], title=f"Drawdown — {ticker_b}")
    st.plotly_chart(fig, use_container_width=True)

    s_b = calc_stats(prices[ticker_b].dropna(), 252, rf_decimal)
    stats_table({ticker_b: s_b})

st.divider()

# --- Wspolna sekcja: Korelacja + Relative Strength ---
st.markdown("### Porownanie wspolne")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Korelacja")
    corr = correlation_matrix(prices, period=252)
    fig = correlation_heatmap(corr, title="Macierz korelacji")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("#### Relative Strength")
    rs_data = relative_strength(prices[ticker_a].dropna(), prices[ticker_b].dropna())
    if not rs_data.empty:
        fig = rs_chart(rs_data, ticker_a, ticker_b)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Za malo wspolnych danych do RS.")

render_footer()
