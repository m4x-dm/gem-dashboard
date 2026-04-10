"""Strona 14: Waluta PLN/USD — wplyw kursu na zwroty ETF-ow."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from components.sidebar import setup_sidebar, render_footer
from data.downloader import download_single
from data.etf_universe import ALL_TICKERS, ETF_NAMES
from data.momentum import latest_returns
from components.charts import price_chart, _base_layout, COLORS, GOLD, BG2
from components.formatting import fmt_pct, color_for_value, MUTED, BG_CARD, BORDER
from components.constants import PERIOD_MAP_FULL
from components.auth import require_premium

st.set_page_config(page_title="Waluta PLN/USD", page_icon="💱", layout="wide")
setup_sidebar()
if not require_premium(14): st.stop()

st.markdown("# 💱 Waluta PLN/USD")
st.caption("Wplyw kursu USD/PLN na zwroty ETF-ow — realne zwroty polskiego inwestora")

USDPLN_TICKER = "USDPLN=X"

period_labels = list(PERIOD_MAP_FULL.keys())
period = st.selectbox("Okres danych", period_labels, index=5, key="waluta_period")
yf_period = PERIOD_MAP_FULL[period]

# Tickers
default_etfs = ["QQQ", "VEA", "AGG", "GLD"]
custom = st.session_state.get("custom_tickers", [])
all_available = ALL_TICKERS + custom
selected = st.multiselect("ETF-y do porownania", all_available, default=default_etfs,
                            max_selections=6, key="waluta_etfs")

if not selected:
    st.warning("Wybierz przynajmniej jeden ETF.")
    render_footer()
    st.stop()

# Download
with st.spinner("Pobieram dane..."):
    usdpln = download_single(USDPLN_TICKER, period=yf_period)
    _parts = {}
    for _t in selected:
        _s = download_single(_t, period=yf_period)
        if _s is not None and len(_s) > 0:
            _parts[_t] = _s
    etf_prices = pd.DataFrame(_parts) if _parts else pd.DataFrame()

if usdpln is None or usdpln.empty:
    st.error("Brak danych kursu USD/PLN.")
    render_footer()
    st.stop()

# Trim if "Strategia 12-1"
if period == "Strategia 12-1":
    if len(usdpln) > 273:
        usdpln = usdpln.iloc[-273:-21]
    if len(etf_prices) > 273:
        etf_prices = etf_prices.iloc[-273:-21]

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["📈 Kurs USD/PLN", "📊 Zwroty USD vs PLN",
                                    "🔀 Overlay", "📖 Hedging"])

with tab1:
    st.subheader("Kurs USD/PLN")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=usdpln.index, y=usdpln.values, mode="lines",
        line=dict(color=GOLD, width=2), name="USD/PLN",
    ))
    fig.update_layout(**_base_layout("Kurs USD/PLN", height=450))
    fig.update_yaxes(title_text="PLN za 1 USD")
    st.plotly_chart(fig, use_container_width=True)

    # Metrics
    rets = latest_returns(pd.DataFrame({"USDPLN": usdpln}))
    cols = st.columns(4)
    for i, p in enumerate(["1M", "3M", "6M", "12M"]):
        val = rets.loc["USDPLN", p] if "USDPLN" in rets.index and p in rets.columns else None
        c = color_for_value(val)
        cols[i].metric(f"Zmiana {p}", fmt_pct(val))

with tab2:
    st.subheader("Zwroty USD vs PLN")
    st.caption("ret_PLN = (1 + ret_USD) × (1 + ret_USDPLN) − 1")

    # Align dates
    combined = etf_prices.copy()
    combined["USDPLN"] = usdpln
    combined = combined.dropna()

    if len(combined) < 22:
        st.warning("Za malo wspolnych danych.")
    else:
        periods_map = {"1M": 21, "3M": 63, "6M": 126, "12M": 252}
        rows = []
        for t in selected:
            if t not in combined.columns:
                continue
            row = {"Ticker": t, "Nazwa": ETF_NAMES.get(t, t)}
            for label, days in periods_map.items():
                if len(combined) > days:
                    ret_usd = combined[t].iloc[-1] / combined[t].iloc[-1 - days] - 1
                    ret_fx = combined["USDPLN"].iloc[-1] / combined["USDPLN"].iloc[-1 - days] - 1
                    ret_pln = (1 + ret_usd) * (1 + ret_fx) - 1
                    row[f"{label} USD"] = ret_usd
                    row[f"{label} PLN"] = ret_pln
                    row[f"{label} Roznica"] = ret_pln - ret_usd
                else:
                    row[f"{label} USD"] = np.nan
                    row[f"{label} PLN"] = np.nan
                    row[f"{label} Roznica"] = np.nan
            rows.append(row)

        if rows:
            df = pd.DataFrame(rows).set_index("Ticker")

            # Build HTML table
            html = (
                f'<table style="width:100%;border-collapse:collapse;margin:16px 0">'
                f'<thead><tr style="border-bottom:2px solid {BORDER}">'
                f'<th style="text-align:left;padding:8px;color:{GOLD}">Ticker</th>'
            )
            for p in ["1M", "3M", "6M", "12M"]:
                html += f'<th style="text-align:right;padding:8px;color:{GOLD}">{p} USD</th>'
                html += f'<th style="text-align:right;padding:8px;color:{GOLD}">{p} PLN</th>'
            html += '</tr></thead><tbody>'

            for _, row in df.iterrows():
                html += f'<tr style="border-bottom:1px solid {BORDER}">'
                html += f'<td style="padding:8px;font-weight:600">{row["Nazwa"]}</td>'
                for p in ["1M", "3M", "6M", "12M"]:
                    usd_val = row.get(f"{p} USD")
                    pln_val = row.get(f"{p} PLN")
                    c_usd = color_for_value(usd_val)
                    c_pln = color_for_value(pln_val)
                    html += f'<td style="text-align:right;padding:8px;color:{c_usd}">{fmt_pct(usd_val)}</td>'
                    html += f'<td style="text-align:right;padding:8px;color:{c_pln};font-weight:600">{fmt_pct(pln_val)}</td>'
                html += '</tr>'
            html += '</tbody></table>'
            st.html(html)

            # FX impact summary
            if len(combined) > 252:
                fx_12m = combined["USDPLN"].iloc[-1] / combined["USDPLN"].iloc[-253] - 1
                sign = "+" if fx_12m > 0 else ""
                impact = "korzystny" if fx_12m > 0 else "niekorzystny"
                st.info(f"Zmiana kursu USD/PLN (12M): **{sign}{fx_12m*100:.2f}%** — wplyw {impact} dla polskiego inwestora")

with tab3:
    st.subheader("Overlay: ETF vs USD/PLN")
    overlay_ticker = st.selectbox("Wybierz ETF", selected, key="overlay_ticker")

    if overlay_ticker in etf_prices.columns:
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Normalize both to 100
        etf_s = etf_prices[overlay_ticker].dropna()
        usd_s = usdpln.copy()

        # Align
        common_idx = etf_s.index.intersection(usd_s.index)
        if len(common_idx) > 1:
            etf_s = etf_s.loc[common_idx]
            usd_s = usd_s.loc[common_idx]
            etf_norm = etf_s / etf_s.iloc[0] * 100
            usd_norm = usd_s / usd_s.iloc[0] * 100

            fig.add_trace(go.Scatter(
                x=etf_norm.index, y=etf_norm.values, name=overlay_ticker,
                line=dict(color=GOLD, width=2),
            ), secondary_y=False)
            fig.add_trace(go.Scatter(
                x=usd_norm.index, y=usd_norm.values, name="USD/PLN",
                line=dict(color="#3B82F6", width=2),
            ), secondary_y=True)

            fig.update_layout(**_base_layout(f"{overlay_ticker} vs USD/PLN (baza=100)", height=450))
            fig.update_yaxes(title_text=f"{overlay_ticker} (baza=100)", secondary_y=False)
            fig.update_yaxes(title_text="USD/PLN (baza=100)", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Za malo wspolnych dat.")

with tab4:
    st.subheader("Koszt hedgingu walutowego")
    st.markdown("""
**Czym jest hedging walutowy?**

Polski inwestor kupujacy ETF-y denominowane w USD jest narazony na ryzyko walutowe.
Gdy zloty sie umacnia (USD/PLN spada), zwrot w PLN jest nizszy niz w USD.

**Forward spread (koszt hedgingu)**

Zabezpieczenie walutowe przez kontrakty forward kosztuje okolo **roznica stop procentowych** miedzy USA a Polska.
Przy wyzszych stopach w Polsce, hedging jest "darmowy" lub nawet korzystny.

**Hedged vs Unhedged — kiedy co sie oplaca?**

| Scenariusz | Unhedged | Hedged |
|---|---|---|
| USD/PLN rosnie (zloty slabnie) | Lepszy | Gorszy |
| USD/PLN spada (zloty sie umacnia) | Gorszy | Lepszy |
| USD/PLN stabilny | Podobny | Koszt hedgingu |

**Dla strategii GEM:**
- GEM nie uwzglednia ryzyka walutowego w sygnalach
- Dlugoterminowo, roznice walutowe czesto sie uśredniaja
- Hedging ma sens gdy PLN systematycznie sie umacnia
- Alternatywa: ETF-y hedged (np. z suffiksem PLN-H)

**Praktyczna wskazowka:**
Jesli inwestujesz >5 lat, ryzyko walutowe ma mniejsze znaczenie.
Przy krotszym horyzoncie, wahania USD/PLN moga dominowac nad zwrotem z ETF-a.
    """)

render_footer()
