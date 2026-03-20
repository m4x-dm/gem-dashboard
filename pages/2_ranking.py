"""Strona 2: Ranking Momentum — tabela sortowalna + filtry."""

import streamlit as st
import pandas as pd
from components.sidebar import setup_sidebar, get_risk_free, render_footer
from data.etf_universe import ALL_TICKERS, ETF_NAMES, ETF_CATEGORY_MAP, ETF_CATEGORIES
from data.downloader import download_prices
from data.momentum import build_ranking
from components.formatting import fmt_pct
from components.charts import ranking_bar_chart, category_pie

st.set_page_config(page_title="Ranking Momentum", page_icon="📊", layout="wide")
setup_sidebar()

st.markdown("# 📊 Ranking Momentum")

# Pobierz dane
tickers = list(set(ALL_TICKERS + st.session_state.get("custom_tickers", [])))
prices = download_prices(tickers)

rf = get_risk_free()

ranking = build_ranking(prices, rf)

# Dodaj nazwy i kategorie
ranking["Nazwa"] = ranking.index.map(lambda t: ETF_NAMES.get(t, t))
ranking["Kategoria"] = ranking.index.map(lambda t: ETF_CATEGORY_MAP.get(t, "Wlasne"))

# Filtry
col1, col2 = st.columns(2)
with col1:
    categories = ["Wszystkie"] + list(ETF_CATEGORIES.keys()) + ["Wlasne"]
    cat_filter = st.selectbox("Kategoria", categories)
with col2:
    mom_filter = st.selectbox("Momentum absolutny", ["Wszystkie", "TAK", "NIE"])

# Filtrowanie
filtered = ranking.copy()
if cat_filter != "Wszystkie":
    filtered = filtered[filtered["Kategoria"] == cat_filter]
if mom_filter != "Wszystkie":
    filtered = filtered[filtered["Momentum_abs"] == mom_filter]

# Tabela
st.markdown(f"**{len(filtered)}** ETF-ow | Stopa wolna: **{rf:.2f}%**")

display_df = filtered[["Nazwa", "Kategoria", "1M", "3M", "6M", "12M", "Wynik", "Momentum_abs"]].copy()
display_df.index.name = "Ticker"

# Formatowanie
for col in ["1M", "3M", "6M", "12M", "Wynik"]:
    display_df[col] = display_df[col].apply(lambda x: fmt_pct(x) if pd.notna(x) else "—")

display_df = display_df.rename(columns={"Momentum_abs": "Mom. abs."})

st.dataframe(
    display_df,
    use_container_width=True,
    height=min(700, 40 + len(display_df) * 35),
)

# Eksport CSV
csv = filtered[["Nazwa", "Kategoria", "1M", "3M", "6M", "12M", "Wynik", "Momentum_abs"]].copy()
csv.index.name = "Ticker"
st.download_button(
    "📥 Eksportuj CSV",
    csv.to_csv(),
    "gem_ranking.csv",
    "text/csv",
)

st.divider()

# Wykresy
col1, col2 = st.columns(2)
with col1:
    valid = ranking.dropna(subset=["Wynik"])
    if not valid.empty:
        fig = ranking_bar_chart(valid, top_n=min(15, len(valid)), title="Ranking momentum")
        st.plotly_chart(fig, use_container_width=True)

with col2:
    cat_counts = ranking["Kategoria"].value_counts().to_dict()
    fig = category_pie(cat_counts, title="ETF-y wg kategorii")
    st.plotly_chart(fig, use_container_width=True)

render_footer()
