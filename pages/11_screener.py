"""Strona 11: Cross-Asset Screener — jednolity ranking z 4 universow."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from components.sidebar import setup_sidebar, get_risk_free, render_footer
from data.etf_universe import ALL_TICKERS as ETF_TICKERS, ETF_NAMES, ETF_CATEGORY_MAP
from data.gpw_universe import ALL_GPW_TICKERS, GPW_NAMES, GPW_CATEGORY_MAP
from data.sp500_universe import ALL_SP500_TICKERS, SP500_NAMES, SP500_SECTOR_MAP
from data.crypto_universe import ALL_CRYPTO_TICKERS, CRYPTO_NAMES, CRYPTO_CATEGORY_MAP
from data.downloader import download_prices
from data.momentum import build_ranking
from components.formatting import (
    fmt_pct, color_for_value,
    GOLD, GREEN, RED, MUTED, BG_CARD, BORDER,
)
from components.charts import _base_layout, COLORS
from components.auth import require_premium

st.set_page_config(page_title="Cross-Asset Screener", page_icon="🔎", layout="wide")
setup_sidebar()
if not require_premium(11): st.stop()

st.markdown("# 🔎 Cross-Asset Screener")
st.caption("Jednolity ranking momentum ze wszystkich klas aktywow")

# ---------------------------------------------------------------------------
# Kolory klas aktywow
# ---------------------------------------------------------------------------
CLASS_COLORS = {
    "ETF": "#C9A84C",
    "S&P 500": "#3B82F6",
    "GPW": "#EF4444",
    "Kryptowaluty": "#22C55E",
}

# ---------------------------------------------------------------------------
# Filtry
# ---------------------------------------------------------------------------
fcol1, fcol2, fcol3, fcol4 = st.columns(4)
with fcol1:
    asset_classes = st.multiselect(
        "Klasy aktywow",
        ["ETF", "S&P 500", "GPW", "Kryptowaluty"],
        default=["ETF", "S&P 500", "GPW", "Kryptowaluty"],
    )
with fcol2:
    min_score = st.number_input("Min. wynik kompozytowy (%)", value=-100.0, step=1.0, format="%.1f")
with fcol3:
    mom_abs_filter = st.selectbox("Momentum absolutny", ["Wszystkie", "TAK", "NIE"])
with fcol4:
    top_n = st.selectbox("Top N", ["20", "50", "100", "200", "Wszystkie"], index=1)

if not asset_classes:
    st.warning("Wybierz co najmniej jedna klase aktywow.")
    st.stop()

# ---------------------------------------------------------------------------
# Download & build ranking per universe
# ---------------------------------------------------------------------------
rf = get_risk_free()
all_rankings = []


@st.cache_data(ttl=3600, show_spinner=False)
def _build_class_ranking(_tickers_tuple, _rf, class_name, period="2y"):
    """Download + ranking dla jednej klasy aktywow (cached)."""
    tickers = list(_tickers_tuple)
    if not tickers:
        return pd.DataFrame()
    prices = download_prices(tickers, period=period)
    if prices.empty:
        return pd.DataFrame()
    ranking = build_ranking(prices, _rf)
    ranking["Klasa"] = class_name
    return ranking


with st.spinner("Pobieram dane i buduje ranking..."):
    if "ETF" in asset_classes:
        r = _build_class_ranking(tuple(ETF_TICKERS), rf, "ETF")
        if not r.empty:
            r["Nazwa"] = r.index.map(lambda t: ETF_NAMES.get(t, t))
            r["Kategoria"] = r.index.map(lambda t: ETF_CATEGORY_MAP.get(t, "—"))
            all_rankings.append(r)

    if "S&P 500" in asset_classes:
        r = _build_class_ranking(tuple(ALL_SP500_TICKERS), rf, "S&P 500")
        if not r.empty:
            r["Nazwa"] = r.index.map(lambda t: SP500_NAMES.get(t, t))
            r["Kategoria"] = r.index.map(lambda t: SP500_SECTOR_MAP.get(t, "—"))
            all_rankings.append(r)

    if "GPW" in asset_classes:
        r = _build_class_ranking(tuple(ALL_GPW_TICKERS), rf, "GPW")
        if not r.empty:
            r["Nazwa"] = r.index.map(lambda t: GPW_NAMES.get(t, t))
            r["Kategoria"] = r.index.map(lambda t: GPW_CATEGORY_MAP.get(t, "—"))
            all_rankings.append(r)

    if "Kryptowaluty" in asset_classes:
        r = _build_class_ranking(tuple(ALL_CRYPTO_TICKERS), rf, "Kryptowaluty")
        if not r.empty:
            r["Nazwa"] = r.index.map(lambda t: CRYPTO_NAMES.get(t, t))
            r["Kategoria"] = r.index.map(lambda t: CRYPTO_CATEGORY_MAP.get(t, "—"))
            all_rankings.append(r)

if not all_rankings:
    st.error("Nie udalo sie pobrac danych dla zadnej klasy aktywow.")
    st.stop()

# ---------------------------------------------------------------------------
# Merge, filter, sort
# ---------------------------------------------------------------------------
combined = pd.concat(all_rankings)
combined = combined.dropna(subset=["Wynik"])
combined = combined.sort_values("Wynik", ascending=False)

# Apply filters
min_score_dec = min_score / 100.0
combined = combined[combined["Wynik"] >= min_score_dec]

if mom_abs_filter != "Wszystkie":
    combined = combined[combined["Momentum_abs"] == mom_abs_filter]

if top_n != "Wszystkie":
    combined = combined.head(int(top_n))

if combined.empty:
    st.info("Brak wynikow po zastosowaniu filtrow.")
    st.stop()

# ---------------------------------------------------------------------------
# Summary cards
# ---------------------------------------------------------------------------
class_counts = combined["Klasa"].value_counts()
scols = st.columns(len(asset_classes))
for i, cls in enumerate(asset_classes):
    count = class_counts.get(cls, 0)
    color = CLASS_COLORS.get(cls, MUTED)
    scols[i].html(
        f'<div style="background:{BG_CARD};border:1px solid {color}40;border-radius:12px;padding:14px;text-align:center">'
        f'<div style="font-size:0.75rem;color:{color};text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px">{cls}</div>'
        f'<div style="font-size:1.4rem;font-weight:700;color:#E5E7EB">{count}</div>'
        f'<div style="font-size:0.7rem;color:{MUTED}">w rankingu</div>'
        f'</div>'
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# Display table
# ---------------------------------------------------------------------------
display_df = combined[["Nazwa", "Klasa", "Kategoria", "1M", "3M", "6M", "12M", "Wynik", "Momentum_abs"]].copy()
display_df["Ticker"] = display_df.index
display_df = display_df[["Ticker", "Nazwa", "Klasa", "Kategoria", "1M", "3M", "6M", "12M", "Wynik", "Momentum_abs"]]

# Format percentage columns for display
for col in ["1M", "3M", "6M", "12M", "Wynik"]:
    display_df[col] = display_df[col].apply(lambda x: fmt_pct(x) if pd.notna(x) else "—")

display_df = display_df.rename(columns={"Momentum_abs": "Mom. abs."})

st.dataframe(display_df, use_container_width=True, hide_index=True, height=500)

# ---------------------------------------------------------------------------
# Bar chart colored by asset class
# ---------------------------------------------------------------------------
st.markdown("### Wynik kompozytowy — top aktywa")

chart_df = combined.head(min(30, len(combined))).copy()
chart_df = chart_df.sort_values("Wynik", ascending=True)
bar_colors = [CLASS_COLORS.get(cls, MUTED) for cls in chart_df["Klasa"]]

fig = go.Figure(go.Bar(
    x=chart_df["Wynik"] * 100,
    y=chart_df.index,
    orientation="h",
    marker_color=bar_colors,
    text=[f"{v*100:.1f}%" for v in chart_df["Wynik"]],
    textposition="outside",
    textfont=dict(size=10),
    hovertemplate="%{y}<br>Wynik: %{x:.1f}%<br><extra></extra>",
))
fig.update_layout(**_base_layout("Top aktywa wg wyniku kompozytowego", height=max(400, len(chart_df) * 25)))
fig.update_xaxes(title_text="Wynik kompozytowy (%)")

# Add legend for asset classes
for cls, color in CLASS_COLORS.items():
    if cls in asset_classes:
        fig.add_trace(go.Bar(
            x=[None], y=[None], name=cls,
            marker_color=color, showlegend=True,
        ))

st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------
st.markdown("---")
export_df = combined[["Nazwa", "Klasa", "Kategoria", "1M", "3M", "6M", "12M", "Wynik", "Momentum_abs"]].copy()
export_df.index.name = "Ticker"
csv = export_df.to_csv()

st.download_button(
    label="📥 Eksport CSV",
    data=csv,
    file_name="cross_asset_ranking.csv",
    mime="text/csv",
)

render_footer()
