"""Strona 17: Monte Carlo — symulacja przyszlych zwrotow."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from components.sidebar import setup_sidebar, get_risk_free, render_footer
from data.downloader import download_prices
from data.etf_universe import ALL_TICKERS, ETF_NAMES
from data.momentum import monte_carlo_simulation, backtest_gem
from components.charts import fan_chart, _base_layout, GOLD, BG2, COLORS
from components.formatting import fmt_number, MUTED, BG_CARD, BORDER
from components.constants import GREEN, RED

st.set_page_config(page_title="Monte Carlo", page_icon="🎲", layout="wide")
setup_sidebar()

st.markdown("# 🎲 Monte Carlo")
st.caption("Symulacja przyszlych zwrotow — ile mozesz miec za N lat?")

# --- Config ---
col1, col2, col3 = st.columns(3)

with col1:
    source = st.selectbox("Zrodlo danych", ["Strategia GEM", "Pojedynczy ETF"], key="mc_source")
with col2:
    years = st.slider("Horyzont (lata)", 1, 30, 10, key="mc_years")
with col3:
    n_sims = st.select_slider("Liczba symulacji", [100, 500, 1000, 2000, 5000], value=1000, key="mc_nsims")

start_capital = st.number_input("Kapital poczatkowy (USD)", 1000, 10_000_000, 10000, step=1000, key="mc_capital")

rf = get_risk_free()

# --- Get equity curve ---
equity = None
equity_label = ""

if source == "Strategia GEM":
    with st.spinner("Obliczam krzywa kapitalu GEM..."):
        required = ["QQQ", "VEA", "EEM", "ACWI", "AGG"]
        prices = download_prices(required, period="max")
        result = backtest_gem(prices, rf, start_capital=start_capital)
        if result is not None:
            equity = result["equity_gem"]
            equity_label = "GEM"
        else:
            st.error("Brak danych do backtestu GEM.")
else:
    custom = st.session_state.get("custom_tickers", [])
    all_available = ALL_TICKERS + custom
    ticker = st.selectbox("Wybierz ETF", all_available,
                           index=all_available.index("QQQ") if "QQQ" in all_available else 0,
                           format_func=lambda t: f"{t} — {ETF_NAMES.get(t, t)}",
                           key="mc_ticker")
    with st.spinner(f"Pobieram dane {ticker}..."):
        prices = download_prices([ticker], period="max")
    if not prices.empty and ticker in prices.columns:
        series = prices[ticker].dropna()
        # Normalize to start_capital
        equity = series / series.iloc[0] * start_capital
        equity_label = ticker
    else:
        st.error(f"Brak danych dla {ticker}")

if equity is None or len(equity) < 252:
    st.warning("Za malo danych historycznych do symulacji (min. 1 rok).")
    render_footer()
    st.stop()

# --- Run simulation ---
with st.spinner(f"Uruchamiam Monte Carlo ({n_sims} symulacji, {years} lat)..."):
    sims = monte_carlo_simulation(equity, years=years, n_sims=n_sims)

# Scale simulations to start from start_capital
scale = start_capital / equity.iloc[-1]
sims = sims * scale

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📈 Fan Chart", "📊 Rozklad koncowy", "🎯 Prawdopodobienstwa"])

with tab1:
    st.plotly_chart(
        fan_chart(sims, title=f"Monte Carlo — {equity_label} ({n_sims} symulacji, {years} lat)"),
        use_container_width=True,
    )
    st.caption("Ciemniejszy pas = P25-P75 (50% sciezek). Jasniejszy = P5-P95 (90% sciezek). Linia = mediana.")

with tab2:
    st.subheader("Rozklad wartosci koncowej")
    final_values = sims.iloc[-1].values

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=final_values, nbinsx=50,
        marker_color=GOLD, opacity=0.75,
    ))

    # Percentile lines
    for p, dash in [(5, "dot"), (25, "dash"), (50, "solid"), (75, "dash"), (95, "dot")]:
        pval = np.percentile(final_values, p)
        fig.add_vline(x=pval, line_dash=dash, line_color="rgba(255,255,255,0.5)", line_width=1,
                      annotation_text=f"P{p}: {fmt_number(pval, 0)}", annotation_position="top")

    fig.update_layout(**_base_layout(f"Rozklad wartosci koncowej po {years} latach", height=450))
    fig.update_xaxes(title_text="Wartosc portfela (USD)")
    fig.update_yaxes(title_text="Liczba symulacji")
    st.plotly_chart(fig, use_container_width=True)

    # Stats
    cols = st.columns(5)
    pcts = [5, 25, 50, 75, 95]
    labels = ["P5 (pesymistyczny)", "P25", "P50 (mediana)", "P75", "P95 (optymistyczny)"]
    for i, (p, label) in enumerate(zip(pcts, labels)):
        val = np.percentile(final_values, p)
        cols[i].metric(label, f"{fmt_number(val, 0)} USD")

with tab3:
    st.subheader("Prawdopodobienstwa")
    final_values = sims.iloc[-1].values

    p_positive = (final_values > start_capital).mean() * 100
    p_double = (final_values > start_capital * 2).mean() * 100
    p_triple = (final_values > start_capital * 3).mean() * 100
    p_loss_50 = (final_values < start_capital * 0.5).mean() * 100
    p_loss_any = (final_values < start_capital).mean() * 100

    median_ret = (np.median(final_values) / start_capital - 1) * 100
    median_cagr = ((np.median(final_values) / start_capital) ** (1 / years) - 1) * 100

    # Cards
    cols = st.columns(3)

    def _prob_card(col, title, prob, color, icon):
        col.html(
            f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;padding:20px;text-align:center">'
            f'<div style="font-size:2rem;margin-bottom:4px">{icon}</div>'
            f'<div style="font-size:0.8rem;color:{MUTED};text-transform:uppercase;margin-bottom:8px">{title}</div>'
            f'<div style="font-size:2rem;font-weight:800;color:{color}">{prob:.1f}%</div>'
            f'</div>'
        )

    _prob_card(cols[0], "Zysk > 0%", p_positive, GREEN, "📈")
    _prob_card(cols[1], "Podwojenie kapitalu", p_double, GREEN, "🚀")
    _prob_card(cols[2], "Potrojenie kapitalu", p_triple, GOLD, "⭐")

    st.markdown("")
    cols2 = st.columns(3)
    _prob_card(cols2[0], "Strata > 50%", p_loss_50, RED, "⚠️")
    _prob_card(cols2[1], "Jakakolwiek strata", p_loss_any, RED, "📉")

    cols2[2].html(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;padding:20px;text-align:center">'
        f'<div style="font-size:2rem;margin-bottom:4px">📊</div>'
        f'<div style="font-size:0.8rem;color:{MUTED};text-transform:uppercase;margin-bottom:8px">Medianowy CAGR</div>'
        f'<div style="font-size:2rem;font-weight:800;color:{GOLD}">{median_cagr:.1f}%</div>'
        f'</div>'
    )

    with st.expander("📖 Jak interpretowac wyniki Monte Carlo?"):
        st.markdown(f"""
**Metodologia:** Bootstrap dziennych zwrotow historycznych. Kazda symulacja losuje dzienne zwroty
z rozkladem historycznym i buduje sciezke ceny do przodu na {years} lat.

**Ograniczenia:**
- Zaklada, ze przyszlosc bedzie "podobna" do historii
- Nie uwzglednia zmian rezimu rynkowego
- Nie uwzglednia kosztow transakcyjnych ani podatkow
- Rozklad zwrotow moze byc niestacjonarny

**Kapital poczatkowy:** {fmt_number(start_capital, 0)} USD
**Medianowa wartosc koncowa:** {fmt_number(np.median(final_values), 0)} USD
**Medianowy calkowity zwrot:** {median_ret:.1f}%
        """)

render_footer()
