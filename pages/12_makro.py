"""Strona 12: Makro Dashboard — kontekst makroekonomiczny dla GEM."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from components.sidebar import setup_sidebar, render_footer
from data.downloader import download_single
from components.formatting import (
    GOLD, GREEN, RED, MUTED, BG_CARD, BORDER,
)
from components.charts import sparkline_chart, _base_layout, COLORS, BG2, GRID
from components.cards import macro_card
from components.auth import require_premium

st.set_page_config(page_title="Makro Dashboard", page_icon="🌍", layout="wide")
setup_sidebar()
if not require_premium(12): st.stop()

st.markdown("# 🌍 Makro Dashboard")
st.caption("Kluczowe wskazniki makroekonomiczne — kontekst dla strategii GEM")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
MACRO_PERIOD = "1y"


@st.cache_data(ttl=3600, show_spinner=False)
def _download_macro(ticker: str, period: str = MACRO_PERIOD) -> pd.Series | None:
    """Pobiera dane dla jednego tickera makro."""
    return download_single(ticker, period=period)


def _pct_change_safe(series: pd.Series, periods: int) -> float | None:
    """Bezpieczna zmiana procentowa."""
    if series is None or len(series) < periods + 1:
        return None
    old = series.iloc[-(periods + 1)]
    new = series.iloc[-1]
    if old == 0 or pd.isna(old) or pd.isna(new):
        return None
    return ((new / old) - 1) * 100


def _changes_dict(series: pd.Series | None, absolute: bool = False) -> dict:
    """Buduje dict zmian 1D/1W/1M.

    Args:
        series: seria danych
        absolute: jesli True, zwraca zmiane absolutna zamiast procentowej (np. dla yield spread)
    """
    if series is None or len(series) < 2:
        return {"1D": None, "1W": None, "1M": None}
    if absolute:
        def _abs_change(s, p):
            if len(s) < p + 1:
                return None
            old = s.iloc[-(p + 1)]
            new = s.iloc[-1]
            if pd.isna(old) or pd.isna(new):
                return None
            return (new - old) * 100  # w bp (basis points / pp*100)
        return {
            "1D": _abs_change(series, 1),
            "1W": _abs_change(series, 5),
            "1M": _abs_change(series, 21),
        }
    return {
        "1D": _pct_change_safe(series, 1),
        "1W": _pct_change_safe(series, 5),
        "1M": _pct_change_safe(series, 21),
    }


def _vix_traffic_light(value: float) -> tuple[str, str]:
    """Sygnal swietlny VIX."""
    if value < 15:
        return GREEN, "Niski strach"
    elif value < 25:
        return "#F59E0B", "Umiarkowany"
    elif value < 35:
        return RED, "Wysoki strach"
    else:
        return RED, "Ekstremum"


def _sp500_trend(prices: pd.Series, ma: int = 200) -> tuple[str, str]:
    """Trend S&P 500 vs 200MA."""
    if prices is None or len(prices) < ma:
        return MUTED, "Brak danych"
    ma_val = prices.rolling(ma).mean().iloc[-1]
    current = prices.iloc[-1]
    if current > ma_val:
        return GREEN, "Powyzej 200MA"
    else:
        return RED, "Ponizej 200MA"


def _yield_curve_spread(tnx: pd.Series | None, irx: pd.Series | None) -> pd.Series | None:
    """Spread 10Y-13W (yield curve)."""
    if tnx is None or irx is None:
        return None
    # Align by date
    df = pd.DataFrame({"10Y": tnx, "13W": irx}).dropna()
    if df.empty:
        return None
    return df["10Y"] - df["13W"]


# ---------------------------------------------------------------------------
# Download all macro data
# ---------------------------------------------------------------------------
with st.spinner("Pobieram dane makro..."):
    vix_data = _download_macro("^VIX")
    tnx_data = _download_macro("^TNX")
    irx_data = _download_macro("^IRX")
    dxy_data = _download_macro("DX-Y.NYB")
    gld_data = _download_macro("GLD")
    oil_data = _download_macro("CL=F")
    sp500_data = _download_macro("^GSPC")

# ---------------------------------------------------------------------------
# Grid 2x3
# ---------------------------------------------------------------------------
row1_col1, row1_col2 = st.columns(2)
row2_col1, row2_col2 = st.columns(2)
row3_col1, row3_col2 = st.columns(2)

# --- VIX ---
with row1_col1:
    if vix_data is not None and len(vix_data) > 0:
        vix_val = float(vix_data.iloc[-1])
        tl_color, tl_label = _vix_traffic_light(vix_val)
        macro_card("VIX — Fear Index", f"{vix_val:.2f}", "pkt",
                   _changes_dict(vix_data), tl_color, tl_label)
        st.plotly_chart(sparkline_chart(vix_data, color="#F59E0B"), use_container_width=True)
    else:
        st.warning("Brak danych VIX")

# --- Yield Curve ---
with row1_col2:
    spread = _yield_curve_spread(tnx_data, irx_data)
    if spread is not None and len(spread) > 0:
        spread_val = float(spread.iloc[-1])
        if spread_val < 0:
            yc_color, yc_label = RED, "Inwersja"
        elif spread_val < 0.5:
            yc_color, yc_label = "#F59E0B", "Plaszczenie"
        else:
            yc_color, yc_label = GREEN, "Normalna"

        macro_card("Yield Curve (10Y - 13W)", f"{spread_val:.2f}", "pp",
                   _changes_dict(spread, absolute=True), yc_color, yc_label)

        # Special chart with zero line and red fill below 0
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=spread.index, y=spread.values, mode="lines",
            line=dict(color=GOLD, width=1.5),
            fill="tozeroy",
            fillcolor="rgba(201,168,76,0.12)",
            hovertemplate="%{x|%Y-%m-%d}<br>Spread: %{y:.2f} pp<extra></extra>",
        ))
        # Red fill below zero
        neg = spread.copy()
        neg[neg > 0] = 0
        fig.add_trace(go.Scatter(
            x=neg.index, y=neg.values, mode="lines",
            line=dict(color=RED, width=0),
            fill="tozeroy",
            fillcolor="rgba(239,68,68,0.25)",
            showlegend=False,
            hoverinfo="skip",
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.4)", line_width=1)
        fig.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", height=120,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Brak danych yield curve")

# --- DXY ---
with row2_col1:
    if dxy_data is not None and len(dxy_data) > 0:
        dxy_val = float(dxy_data.iloc[-1])
        # DXY > 105 = strong dollar (negative for EM/commodities)
        if dxy_val > 105:
            dxy_color, dxy_label = RED, "Silny dolar"
        elif dxy_val > 95:
            dxy_color, dxy_label = "#F59E0B", "Neutralny"
        else:
            dxy_color, dxy_label = GREEN, "Slaby dolar"
        macro_card("US Dollar Index (DXY)", f"{dxy_val:.2f}", "pkt",
                   _changes_dict(dxy_data), dxy_color, dxy_label)
        st.plotly_chart(sparkline_chart(dxy_data, color="#3B82F6"), use_container_width=True)
    else:
        st.warning("Brak danych DXY")

# --- S&P 500 + 200MA ---
with row2_col2:
    if sp500_data is not None and len(sp500_data) > 0:
        sp_val = float(sp500_data.iloc[-1])
        sp_color, sp_label = _sp500_trend(sp500_data)
        macro_card("S&P 500", f"{sp_val:,.0f}".replace(",", " "), "pkt",
                   _changes_dict(sp500_data), sp_color, sp_label)

        # Chart with 200MA line
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=sp500_data.index, y=sp500_data.values, mode="lines",
            line=dict(color=GOLD, width=1.5), name="S&P 500",
            hovertemplate="%{x|%Y-%m-%d}<br>%{y:,.0f}<extra></extra>",
        ))
        if len(sp500_data) >= 200:
            ma200 = sp500_data.rolling(200).mean()
            fig.add_trace(go.Scatter(
                x=ma200.index, y=ma200.values, mode="lines",
                line=dict(color="#EF4444", width=1, dash="dash"), name="200MA",
                hovertemplate="%{x|%Y-%m-%d}<br>200MA: %{y:,.0f}<extra></extra>",
            ))
        fig.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", height=120,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Brak danych S&P 500")

# --- Gold ---
with row3_col1:
    if gld_data is not None and len(gld_data) > 0:
        gld_val = float(gld_data.iloc[-1])
        gld_changes = _changes_dict(gld_data)
        m1 = gld_changes.get("1M")
        if m1 is not None and m1 > 5:
            g_color, g_label = GREEN, "Silny trend"
        elif m1 is not None and m1 > 0:
            g_color, g_label = "#F59E0B", "Wzrostowy"
        else:
            g_color, g_label = RED, "Spadkowy"
        macro_card("Zloto (GLD)", f"${gld_val:.2f}", "USD",
                   gld_changes, g_color, g_label)
        st.plotly_chart(sparkline_chart(gld_data, color=GOLD), use_container_width=True)
    else:
        st.warning("Brak danych GLD")

# --- Oil WTI ---
with row3_col2:
    if oil_data is not None and len(oil_data) > 0:
        oil_val = float(oil_data.iloc[-1])
        oil_changes = _changes_dict(oil_data)
        if oil_val > 90:
            o_color, o_label = RED, "Wysoka cena"
        elif oil_val > 60:
            o_color, o_label = "#F59E0B", "Umiarkowana"
        else:
            o_color, o_label = GREEN, "Niska cena"
        macro_card("Ropa WTI (CL=F)", f"${oil_val:.2f}", "USD",
                   oil_changes, o_color, o_label)
        st.plotly_chart(sparkline_chart(oil_data, color="#A855F7"), use_container_width=True)
    else:
        st.warning("Brak danych ropy WTI")

# ---------------------------------------------------------------------------
# Interpretacja makro
# ---------------------------------------------------------------------------
with st.expander("📖 Interpretacja makro dla GEM", expanded=False):
    st.markdown("""
**VIX (Fear Index)**
- < 15: Rynek spokojny, niski strach — sprzyjajace warunki dla akcji
- 15-25: Normalna zmiennosc
- 25-35: Wysoki strach — mozliwa korekta, rozwazyc obligacje
- &gt; 35: Panika rynkowa — historycznie czesto dno rynku

**Yield Curve (10Y - 13W)**
- Dodatni spread: Normalna krzywa — zdrowa gospodarka
- Bliski zeru: Splaszczenie — spowolnienie gospodarcze
- Ujemny (inwersja): Historycznie poprzedza recesje o 6-18 miesiecy
- Dla GEM: inwersja → sygnaly ostrzegawcze, momentum moze sie pogorszyc

**US Dollar (DXY)**
- Silny dolar (>105): Negatywny dla rynkow wschodzacych i surowcow
- Slaby dolar (<95): Pozytywny dla VEA, VWO, zlota, surowcow
- Dla GEM: silny dolar sprzyja SPY vs VEA

**S&P 500 vs 200MA**
- Powyzej 200MA: Trend wzrostowy — utrzymuj pozycje w akcjach
- Ponizej 200MA: Trend spadkowy — rozwazyc przejscie na obligacje (AGG)
- Kluczowy wskaznik dla momentum absolutnego w GEM

**Zloto (GLD)**
- Rosnie przy: niskich realnych stopach, slabym dolarze, niepewnosci
- Safe haven w okresach paniki rynkowej
- Dla GEM: silne zloto moze sygnalizowac slabe momentum akcji

**Ropa WTI**
- Wysoka cena (>$90): Ryzyko inflacji → wyzsze stopy → presja na akcje
- Niska cena (<$60): Spowolnienie gospodarcze lub nadpodaz
- Dla GEM: szoki naftowe historycznie poprzedzaly zmiany sygnalow
    """)

render_footer()
