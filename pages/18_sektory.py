"""Strona 18: Rotacja Sektorowa — momentum sektorow GICS w czasie."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from components.sidebar import setup_sidebar, render_footer
from data.downloader import download_prices
from data.momentum import latest_returns
from components.charts import (
    price_chart, ranking_bar_chart, _base_layout, COLORS, GOLD, BG2,
)
from components.formatting import fmt_pct, color_for_value, MUTED, BG_CARD, BORDER
from components.constants import GREEN, RED, PERIOD_MAP_FULL

st.set_page_config(page_title="Rotacja Sektorowa", page_icon="🔄", layout="wide")
setup_sidebar()

st.markdown("# 🔄 Rotacja Sektorowa")
st.caption("Momentum 11 sektorow GICS — ktory sektor prowadzi?")

# Sector ETFs (SPDR Select Sector)
SECTOR_ETFS = {
    "XLK": "Technologia",
    "XLF": "Finanse",
    "XLE": "Energia",
    "XLV": "Ochrona zdrowia",
    "XLI": "Przemysl",
    "XLY": "Konsumpcja cykliczna",
    "XLP": "Konsumpcja podstawowa",
    "XLC": "Komunikacja",
    "XLRE": "Nieruchomosci",
    "XLU": "Uzytecznosc publ.",
    "XLB": "Materialy",
}
SECTOR_TICKERS = list(SECTOR_ETFS.keys())

period = st.selectbox("Okres danych", list(PERIOD_MAP_FULL.keys())[3:], index=4, key="sektory_period")
yf_period = PERIOD_MAP_FULL[period]

with st.spinner("Pobieram dane sektorowe..."):
    prices = download_prices(SECTOR_TICKERS, period=yf_period)

available = [t for t in SECTOR_TICKERS if t in prices.columns]
if len(available) < 3:
    st.error("Za malo danych sektorowych.")
    render_footer()
    st.stop()

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Heatmapa", "📊 Ranking", "📖 Cykl koniunkturalny", "📈 Porownanie"])

with tab1:
    st.subheader("Heatmapa momentum sektorow")

    # Rolling 3M momentum per sector per month
    monthly_prices = prices[available].resample("ME").last()
    rolling_mom = monthly_prices.pct_change(periods=3) * 100  # 3M rolling

    if len(rolling_mom.dropna()) < 2:
        st.warning("Za malo danych do heatmapy.")
    else:
        mom_clean = rolling_mom.dropna()
        # Rename columns to sector names
        mom_display = mom_clean.rename(columns=SECTOR_ETFS)

        # Transpose: sectors as rows, months as columns
        z = mom_display.T.values
        x_labels = [d.strftime("%Y-%m") for d in mom_display.index]
        y_labels = mom_display.columns.tolist()

        labels = np.where(np.isnan(z), "", np.vectorize(lambda v: f"{v:.1f}%")(z))

        fig = go.Figure(go.Heatmap(
            z=z, x=x_labels, y=y_labels,
            colorscale=[[0, "#EF4444"], [0.5, BG2], [1, "#22C55E"]],
            zmid=0,
            text=labels, texttemplate="%{text}", textfont=dict(size=9),
            hovertemplate="Sektor: %{y}<br>Okres: %{x}<br>Mom 3M: %{text}<extra></extra>",
        ))
        h = max(400, len(y_labels) * 35)
        fig.update_layout(**_base_layout("Momentum 3M sektorow w czasie (%)", height=h))
        fig.update_xaxes(side="top", tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Ranking biezacy sektorow")

    rets = latest_returns(prices[available])
    rets["Nazwa"] = rets.index.map(SECTOR_ETFS)

    # Composite score (manual)
    weights = {"12M": 0.50, "6M": 0.25, "3M": 0.15, "1M": 0.10}
    def _score(row):
        s = 0.0
        for p, w in weights.items():
            v = row.get(p, np.nan)
            if pd.notna(v):
                s += v * w
            else:
                return np.nan
        return s

    rets["Wynik"] = rets.apply(_score, axis=1)
    rets = rets.sort_values("Wynik", ascending=False)

    # Bar chart
    df_bar = rets.dropna(subset=["Wynik"]).copy()
    if not df_bar.empty:
        df_bar_sorted = df_bar.sort_values("Wynik", ascending=True)
        colors = [GREEN if v > 0 else RED for v in df_bar_sorted["Wynik"]]
        names = [SECTOR_ETFS.get(t, t) for t in df_bar_sorted.index]

        fig = go.Figure(go.Bar(
            x=df_bar_sorted["Wynik"] * 100, y=names,
            orientation="h", marker_color=colors,
            text=[f"{v*100:.1f}%" for v in df_bar_sorted["Wynik"]],
            textposition="outside", textfont=dict(size=11),
        ))
        fig.update_layout(**_base_layout("Ranking sektorow — wynik momentum", height=max(350, len(df_bar) * 35)))
        fig.update_xaxes(title_text="Wynik kompozytowy (%)")
        st.plotly_chart(fig, use_container_width=True)

    # Table
    display = rets[["Nazwa", "1M", "3M", "6M", "12M", "Wynik"]].copy()
    for col in ["1M", "3M", "6M", "12M", "Wynik"]:
        display[col] = display[col].apply(lambda v: fmt_pct(v) if pd.notna(v) else "—")
    st.dataframe(display, use_container_width=True)

with tab3:
    st.subheader("Cykl koniunkturalny a rotacja sektorowa")
    st.markdown("""
**Wczesna ekspansja** (po recesji):
- Liderzy: **Technologia** (XLK), **Konsumpcja cykliczna** (XLY), **Finanse** (XLF)
- Niska inflacja, obnizki stop, odbudowa zaufania

**Srodkowa ekspansja:**
- Liderzy: **Przemysl** (XLI), **Materialy** (XLB), **Energia** (XLE)
- Rosnaacy popyt, inwestycje w infrastrukture, rosnace ceny surowcow

**Pozna ekspansja** (przed szczytem):
- Liderzy: **Energia** (XLE), **Materialy** (XLB)
- Wysokia inflacja, rosnace stopy procentowe
- Defensywne sektory zaczynaja sie umacniac

**Recesja / spowolnienie:**
- Liderzy: **Uzytecznosc publ.** (XLU), **Ochrona zdrowia** (XLV), **Konsumpcja podstawowa** (XLP)
- Inwestorzy szukaja bezpieczenstwa i dywidend
- Nieruchomosci (XLRE) moga ucierpiec przez wyzsze stopy

**Jak to laczyc z GEM?**
- Gdy GEM wskazuje AGG (obligacje), rynek czesto jest w poznej ekspansji lub recesji
- Sektory defensywne (XLU, XLV, XLP) potwierdzaja trend spadkowy
- Powrot QQQ/VEA w GEM czesto pokrywa sie z rotacja do sektorow cyklicznych
    """)

with tab4:
    st.subheader("Porownanie sektorow")
    compare = st.multiselect("Wybierz 2-4 sektory", available,
                              default=available[:3],
                              max_selections=4, key="sektory_compare",
                              format_func=lambda t: f"{t} ({SECTOR_ETFS.get(t, t)})")
    if len(compare) >= 2:
        st.plotly_chart(
            price_chart(prices[compare], title="Porownanie sektorow (baza=100)"),
            use_container_width=True,
        )
    else:
        st.info("Wybierz co najmniej 2 sektory.")

render_footer()
