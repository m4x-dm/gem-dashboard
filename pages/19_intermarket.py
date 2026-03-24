"""Strona 19: Intermarket — relacje miedzy klasami aktywow."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from components.sidebar import setup_sidebar, render_footer
from data.downloader import download_prices, download_single
from data.momentum import correlation_matrix, strategy_correlations
from components.charts import (
    price_chart, correlation_heatmap, _base_layout, COLORS, GOLD, BG2,
)
from components.formatting import MUTED, BG_CARD, BORDER
from components.constants import GREEN, RED, PERIOD_MAP_FULL
from components.cards import macro_card
from components.sidebar import get_risk_free
from components.auth import require_premium

st.set_page_config(page_title="Intermarket", page_icon="🔗", layout="wide")
setup_sidebar()
if not require_premium(19): st.stop()

st.markdown("# 🔗 Analiza Intermarket")
st.caption("Relacje miedzy klasami aktywow: akcje, obligacje, zloto, dolar, ropa")

# Assets
INTERMARKET = {
    "SPY": "S&P 500",
    "^TNX": "Obligacje USA (10Y yield)",
    "GC=F": "Zloto",
    "DX-Y.NYB": "Dolar (DXY)",
    "CL=F": "Ropa WTI",
}
IM_TICKERS = list(INTERMARKET.keys())

period = st.selectbox("Okres danych", list(PERIOD_MAP_FULL.keys())[3:], index=4, key="im_period")
yf_period = PERIOD_MAP_FULL[period]

# Download
with st.spinner("Pobieram dane intermarket..."):
    all_data = {}
    for t in IM_TICKERS:
        s = download_single(t, period=yf_period)
        if s is not None and len(s) > 0:
            all_data[t] = s

if len(all_data) < 3:
    st.error("Za malo danych intermarket.")
    render_footer()
    st.stop()

# Combine to DataFrame
prices = pd.DataFrame(all_data)
prices = prices.dropna(how="all")

# Trim if "Strategia 12-1"
if period == "Strategia 12-1" and len(prices) > 273:
    prices = prices.iloc[-273:-21]

available = [t for t in IM_TICKERS if t in prices.columns]

# --- Tabs ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["📈 Overlay", "📊 Ratio", "🔄 Korelacja rolling", "🗺️ Macierz korelacji",
     "🚦 Regime", "📊 Korelacja strategii"])

with tab1:
    st.subheader("Wszystkie aktywa znormalizowane (baza=100)")
    st.plotly_chart(
        price_chart(prices[available].rename(columns=INTERMARKET),
                    title="Intermarket — baza = 100"),
        use_container_width=True,
    )

with tab2:
    st.subheader("Ratio miedzy aktywami")
    pairs = []
    for i, a in enumerate(available):
        for b in available[i+1:]:
            pairs.append(f"{a} / {b}")

    pair = st.selectbox("Wybierz pare", pairs, key="im_pair")
    parts = pair.split(" / ")
    t1, t2 = parts[0], parts[1]

    if t1 in prices.columns and t2 in prices.columns:
        ratio = prices[t1] / prices[t2]
        ratio = ratio.dropna()
        if len(ratio) > 1:
            name1 = INTERMARKET.get(t1, t1)
            name2 = INTERMARKET.get(t2, t2)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=ratio.index, y=ratio.values, mode="lines",
                line=dict(color=GOLD, width=2), name=f"{name1}/{name2}",
            ))
            # Add mean line
            mean_val = ratio.mean()
            fig.add_hline(y=mean_val, line_dash="dash", line_color="rgba(255,255,255,0.4)",
                          line_width=1, annotation_text=f"Srednia: {mean_val:.2f}")
            fig.update_layout(**_base_layout(f"Ratio {name1} / {name2}", height=450))
            fig.update_yaxes(title_text="Ratio")
            st.plotly_chart(fig, use_container_width=True)

            # Interpretation
            current = ratio.iloc[-1]
            if current > mean_val * 1.1:
                st.info(f"Ratio {current:.2f} — powyzej sredniej ({mean_val:.2f}). {name1} relatywnie drogi vs {name2}.")
            elif current < mean_val * 0.9:
                st.info(f"Ratio {current:.2f} — ponizej sredniej ({mean_val:.2f}). {name1} relatywnie tani vs {name2}.")
            else:
                st.info(f"Ratio {current:.2f} — blisko sredniej ({mean_val:.2f}).")

with tab3:
    st.subheader("Rolling korelacja (63 dni)")

    col1, col2 = st.columns(2)
    with col1:
        t1_sel = st.selectbox("Aktywo 1", available, index=0, key="rc_t1",
                               format_func=lambda t: INTERMARKET.get(t, t))
    with col2:
        t2_opts = [t for t in available if t != t1_sel]
        t2_sel = st.selectbox("Aktywo 2", t2_opts, index=0, key="rc_t2",
                               format_func=lambda t: INTERMARKET.get(t, t))

    window = st.slider("Okno korelacji (dni)", 21, 252, 63, key="rc_window")

    if t1_sel in prices.columns and t2_sel in prices.columns:
        rets = prices[[t1_sel, t2_sel]].pct_change().dropna()
        if len(rets) > window:
            rolling_corr = rets[t1_sel].rolling(window).corr(rets[t2_sel]).dropna()

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=rolling_corr.index, y=rolling_corr.values, mode="lines",
                line=dict(color=GOLD, width=2),
                name=f"Korelacja {INTERMARKET.get(t1_sel, t1_sel)} vs {INTERMARKET.get(t2_sel, t2_sel)}",
            ))
            fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)", line_width=1)
            fig.add_hline(y=0.5, line_dash="dot", line_color="rgba(34,197,94,0.3)", line_width=1)
            fig.add_hline(y=-0.5, line_dash="dot", line_color="rgba(239,68,68,0.3)", line_width=1)
            fig.update_layout(**_base_layout(
                f"Rolling {window}D korelacja: {INTERMARKET.get(t1_sel, t1_sel)} vs {INTERMARKET.get(t2_sel, t2_sel)}",
                height=400))
            fig.update_yaxes(title_text="Korelacja", range=[-1, 1])
            st.plotly_chart(fig, use_container_width=True)

            current_corr = rolling_corr.iloc[-1]
            if current_corr > 0.5:
                st.info(f"Aktualna korelacja: **{current_corr:.2f}** — silna pozytywna")
            elif current_corr < -0.5:
                st.info(f"Aktualna korelacja: **{current_corr:.2f}** — silna negatywna")
            else:
                st.info(f"Aktualna korelacja: **{current_corr:.2f}** — slaba/umiarkowana")
        else:
            st.warning("Za malo danych dla wybranego okna korelacji.")

with tab4:
    st.subheader("Macierz korelacji")
    corr_period = st.slider("Okres korelacji (dni)", 63, 504, 252, key="im_corr_period")
    avail_prices = prices[available].dropna()
    if len(avail_prices) > corr_period:
        corr = correlation_matrix(avail_prices.rename(columns=INTERMARKET), period=corr_period)
        st.plotly_chart(
            correlation_heatmap(corr, title=f"Macierz korelacji ({corr_period} dni)"),
            use_container_width=True,
        )
    else:
        st.warning("Za malo danych dla wybranego okresu korelacji.")

with tab5:
    st.subheader("Regime: Risk-On vs Risk-Off")

    # Simple regime classifier based on current momentum
    signals = {}
    for t in available:
        s = prices[t].dropna()
        if len(s) > 63:
            mom_3m = s.iloc[-1] / s.iloc[-63] - 1
            signals[t] = mom_3m

    risk_on_count = 0
    risk_off_count = 0

    for t, mom in signals.items():
        if t in ("SPY",):
            if mom > 0:
                risk_on_count += 2  # double weight for equities
            else:
                risk_off_count += 2
        elif t == "^TNX":
            # Rosnaca rentownosc = spadek cen obligacji = risk-on
            if mom > 0:
                risk_on_count += 1
            else:
                risk_off_count += 1
        elif t == "GC=F":
            if mom > 0:
                risk_off_count += 1
            else:
                risk_on_count += 1
        elif t == "DX-Y.NYB":
            if mom > 0:
                risk_off_count += 1  # strong dollar = risk off
            else:
                risk_on_count += 1
        elif t == "CL=F":
            if mom > 0:
                risk_on_count += 1
            else:
                risk_off_count += 1

    total = risk_on_count + risk_off_count
    if total > 0:
        risk_on_pct = risk_on_count / total * 100
    else:
        risk_on_pct = 50

    if risk_on_pct >= 65:
        regime_color, regime_label = GREEN, "Risk-On"
        regime_desc = "Srodowisko sprzyjajace akcjom. Momentum pozytywny, apetyt na ryzyko."
    elif risk_on_pct <= 35:
        regime_color, regime_label = RED, "Risk-Off"
        regime_desc = "Srodowisko awersji do ryzyka. Rozwazyc obligacje lub zloto."
    else:
        regime_color, regime_label = "#F59E0B", "Neutralny"
        regime_desc = "Mieszane sygnaly. Brak wyraznego kierunku miedzy klasami aktywow."

    st.html(
        f'<div style="background:{BG_CARD};border:2px solid {regime_color};border-radius:16px;padding:32px;text-align:center;margin-bottom:24px">'
        f'<div style="font-size:0.8rem;color:{MUTED};text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px">Biezacy regime</div>'
        f'<div style="font-size:2rem;font-weight:800;color:{regime_color}">{regime_label}</div>'
        f'<div style="font-size:1rem;color:{MUTED};margin-top:8px">{regime_desc}</div>'
        f'<div style="font-size:0.85rem;color:{MUTED};margin-top:16px">Risk-On score: {risk_on_pct:.0f}%</div>'
        f'</div>'
    )

    # Detail per asset
    st.markdown("#### Sygnaly per klasa aktywow")
    for t in available:
        if t in signals:
            mom = signals[t]
            name = INTERMARKET.get(t, t)
            color = GREEN if mom > 0 else RED
            sign = "+" if mom > 0 else ""
            st.html(
                f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center">'
                f'<span style="color:#E5E7EB;font-weight:600">{name} ({t})</span>'
                f'<span style="color:{color};font-weight:700">{sign}{mom*100:.1f}% (3M)</span>'
                f'</div>'
            )

    with st.expander("📖 Jak czytac analilze intermarket?"):
        st.markdown("""
**Kluczowe relacje:**

| Para | Typowa korelacja | Znaczenie |
|---|---|---|
| SPY vs 10Y yield | Pozytywna | Rosnace rentownosci = risk-on (obie rosna) |
| SPY vs Zloto | Slaba/zmienna | Zloto to hedge, ale nie zawsze odwrotny |
| Zloto vs DXY | Negatywna | Slaby dolar → droge zloto |
| SPY vs CL=F | Pozytywna | Ropa rosnie z gospodarka (ale szoki sa negatywne) |
| 10Y yield vs DXY | Pozytywna | Rosnace stopy przyciagaja kapital → silny dolar |

**Dla strategii GEM:**
- Risk-On: GEM prawdopodobnie wskazuje QQQ/VEA/EEM/ACWI
- Risk-Off: GEM prawdopodobnie przechodzi na obligacje (AGG)
- Zwracaj uwage na divergencje — np. SPY rosnie ale zloto tez (niepewnosc)

**Ratio SPY / 10Y yield:**
- Rosnace = akcje wygrywaja vs obligacje (risk-on)
- Spadajace = rentownosci rosna szybciej niz akcje (zaostrzanie polityki monetarnej)
        """)

with tab6:
    st.subheader("Rolling korelacja miedzy strategiami")
    st.caption("Porownanie equity curves: GEM Klasyczny, QQQ+SMA200, TQQQ+Momentum")

    rf = get_risk_free()

    # Potrzebujemy QQQ, VEA, EEM, ACWI, AGG
    strat_tickers = ["QQQ", "VEA", "EEM", "ACWI", "AGG"]
    with st.spinner("Pobieram dane do backtestow strategii..."):
        from data.downloader import download_prices
        strat_prices = download_prices(strat_tickers, period=yf_period)

    strat_window = st.slider("Okno korelacji (dni)", 63, 252, 63, key="strat_corr_window")

    corr_result = strategy_correlations(strat_prices, rf, window=strat_window)

    if corr_result is not None and len(corr_result) > 0:
        # Wykres 3 linii korelacji
        fig = go.Figure()
        pair_colors = [GOLD, "#3B82F6", GREEN]
        for i, col in enumerate(corr_result.columns):
            fig.add_trace(go.Scatter(
                x=corr_result.index, y=corr_result[col].values,
                mode="lines", name=col,
                line=dict(color=pair_colors[i], width=2),
            ))
        fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)", line_width=1)
        fig.add_hline(y=0.5, line_dash="dot", line_color="rgba(255,255,255,0.15)", line_width=1)
        fig.add_hline(y=-0.5, line_dash="dot", line_color="rgba(255,255,255,0.15)", line_width=1)
        fig.update_layout(**_base_layout(
            f"Rolling {strat_window}D korelacja miedzy strategiami", height=450))
        fig.update_yaxes(title_text="Korelacja", range=[-1, 1])
        st.plotly_chart(fig, use_container_width=True)

        # Aktualne wartosci
        st.markdown("#### Aktualne korelacje")
        corr_cols = st.columns(3)
        for i, col in enumerate(corr_result.columns):
            val = corr_result[col].iloc[-1]
            if val > 0.7:
                c_color = GREEN
                c_label = "Silna pozytywna"
            elif val > 0.3:
                c_color = "#F59E0B"
                c_label = "Umiarkowana"
            elif val > -0.3:
                c_color = MUTED
                c_label = "Slaba"
            elif val > -0.7:
                c_color = "#F59E0B"
                c_label = "Umiarkowana negatywna"
            else:
                c_color = RED
                c_label = "Silna negatywna"

            corr_cols[i].html(
                f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;padding:16px;text-align:center">'
                f'<div style="font-size:0.7rem;color:{MUTED};text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px">{col}</div>'
                f'<div style="font-size:1.4rem;font-weight:700;color:{c_color}">{val:.2f}</div>'
                f'<div style="font-size:0.75rem;color:{MUTED};margin-top:4px">{c_label}</div>'
                f'</div>'
            )

        with st.expander("📖 Jak interpretowac korelacje strategii?"):
            st.markdown("""
**GEM vs QQQ+SMA200:**
- Obie strategie uzywaja QQQ i AGG, wiec korelacja jest zazwyczaj umiarkowana-wysoka
- Roznica: GEM rebalansuje miesiecznie (momentum 12-1), SMA200 dziennie (trend)
- Niska korelacja = strategie uzupelniaja sie (dywersyfikacja)

**GEM vs TQQQ+Momentum:**
- TQQQ uzywa 3x lewara — wieksze wahania
- Wysoka korelacja w trendzie wzrostowym (obie w akcjach)
- Niska korelacja w trendzie bocznym (rozne progi wejscia/wyjscia)

**SMA200 vs TQQQ+Momentum:**
- SMA200 reaguje dziennie, TQQQ+Mom miesiecznie
- Rozne czestotliwosci rebalansu = rozne momenty przelaczen

**Praktyczne wnioski:**
- Korelacja < 0.5 → warto rozwazyc alokacje do obu strategii (dywersyfikacja)
- Korelacja > 0.8 → strategie zachowuja sie podobnie — mala wartosc laczenia
            """)
    else:
        st.warning("Za malo danych do obliczenia korelacji strategii (wymagane 273+ sesji + okno korelacji).")

render_footer()
