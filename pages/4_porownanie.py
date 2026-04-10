"""Strona 4: Porownanie — head-to-head 2-4 ETF-ow."""

import streamlit as st
import pandas as pd
from components.sidebar import setup_sidebar, render_footer, get_risk_free
from data.etf_universe import ALL_TICKERS, ETF_NAMES, ETF_CATEGORY_MAP
from data.downloader import download_single, download_stooq, STOOQ_TICKERS
from data.momentum import latest_returns, correlation_matrix, calc_stats, relative_strength
from components.formatting import fmt_pct, color_for_value, GOLD, BG_CARD, BORDER, MUTED
from components.charts import price_chart, correlation_heatmap, rs_chart
from components.cards import comparison_card, stats_table
from components.auth import require_premium

st.set_page_config(page_title="Porownanie ETF", page_icon="⚖️", layout="wide")
setup_sidebar()
if not require_premium(4): st.stop()

st.markdown("# ⚖️ Porownanie")

# Indeksy GPW (dane ze stooq.com)
GPW_INDEX_NAMES = {"WIG20": "WIG20 (GPW)", "mWIG40": "mWIG40 (GPW)", "sWIG80": "sWIG80 (GPW)"}
GPW_INDEX_CAT = {t: "Indeksy GPW" for t in GPW_INDEX_NAMES}

all_names = {**ETF_NAMES, **GPW_INDEX_NAMES}
all_categories = {**ETF_CATEGORY_MAP, **GPW_INDEX_CAT}
for t in st.session_state.get("custom_tickers", []):
    all_names.setdefault(t, t)
    all_categories.setdefault(t, "Wlasne")

available = ALL_TICKERS + list(GPW_INDEX_NAMES.keys()) + st.session_state.get("custom_tickers", [])
options = {t: f"{t} — {all_names.get(t, t)}" for t in available}

col_sel, col_period = st.columns([3, 1])
with col_sel:
    selected = st.multiselect(
        "Wybierz 2-4 instrumenty do porownania",
        options=list(options.keys()),
        default=["QQQ", "VEA"],
        format_func=lambda x: options[x],
        max_selections=4,
    )
with col_period:
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

if len(selected) < 2:
    st.info("Wybierz co najmniej 2 ETF-y.")
    st.stop()

# Dane — rozdziel tickery yfinance vs stooq
yf_tickers = [t for t in selected if t not in STOOQ_TICKERS]
stooq_tickers = [t for t in selected if t in STOOQ_TICKERS]

prices = pd.DataFrame()
for _t in yf_tickers:
    _s = download_single(_t, period=period)
    if _s is not None and len(_s) > 0:
        prices[_t] = _s

for t in stooq_tickers:
    s = download_stooq(t, period=period)
    if s is not None:
        prices[t] = s

prices = prices.dropna(how="all")

# Strategia 12-1: pokaz okres od 13 mies. wstecz do 1 mies. wstecz
if is_strategy_view and len(prices) > 273:
    prices = prices.iloc[-273:-21]
elif is_strategy_view:
    st.warning("Za malo danych dla widoku Strategia 12-1. Wyswietlam dostepne dane.")
if prices.empty:
    st.error("Brak danych.")
    st.stop()

# Metryki
st.markdown("### Stopy zwrotu")
rets = latest_returns(prices)

cols = st.columns(len(selected))
for i, ticker in enumerate(selected):
    with cols[i]:
        r = rets.loc[ticker] if ticker in rets.index else pd.Series()
        comparison_card(
            ticker, all_names.get(ticker, ticker),
            all_categories.get(ticker, "Wlasne"), r, i,
        )

st.divider()

# Overlay cenowy
st.markdown("### Cena znormalizowana (baza = 100)")
fig = price_chart(prices, title=f"Porownanie cenowe — {period_label}")
st.plotly_chart(fig, use_container_width=True)

st.divider()

# Statystyki
st.markdown("### Statystyki")
rf = get_risk_free()
rf_decimal = rf / 100.0
cmp_stats = {}
for t in selected:
    if t in prices.columns:
        cmp_stats[t] = calc_stats(prices[t].dropna(), 252, rf_decimal)
if cmp_stats:
    stats_table(cmp_stats)

st.divider()

# Macierz korelacji
st.markdown("### Macierz korelacji (252 dni)")
corr = correlation_matrix(prices, period=252)
fig = correlation_heatmap(corr)
st.plotly_chart(fig, use_container_width=True)

# Interpretacja
with st.expander("Jak czytac korelacje?"):
    st.markdown("""
    - **1.0** = doskonala korelacja dodatnia (ruchy w tym samym kierunku)
    - **0.0** = brak korelacji (niezalezne ruchy)
    - **-1.0** = doskonala korelacja ujemna (ruchy w przeciwnym kierunku)

    Dobrze zdywersyfikowany portfel powinien zawierac aktywa o **niskiej lub ujemnej korelacji**.
    """)

st.divider()

# =====================================================================
# Relative Strength
# =====================================================================
st.markdown("### Relative Strength")

rs_benchmark = st.selectbox(
    "Benchmark RS", [t for t in selected], index=0, key="rs_bench",
)
rs_assets = [t for t in selected if t != rs_benchmark]

if rs_assets and rs_benchmark in prices.columns:
    for asset_t in rs_assets:
        if asset_t in prices.columns:
            rs_data = relative_strength(prices[asset_t].dropna(), prices[rs_benchmark].dropna())
            if not rs_data.empty:
                fig = rs_chart(rs_data, asset_t, rs_benchmark)
                st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Wybierz co najmniej 2 instrumenty.")

render_footer()
