"""Strona 0: Podsumowanie — centrum dowodzenia z kluczowymi sygnalami."""

import streamlit as st
import pandas as pd
import numpy as np
from components.sidebar import setup_sidebar, get_risk_free, render_footer
from data.etf_universe import ALL_TICKERS, ETF_NAMES, ETF_CATEGORY_MAP
from data.downloader import download_prices, download_single
from data.momentum import (
    gem_classic_signal, build_ranking, backtest_gem, calc_stats,
)
from components.cards import (
    signal_card, metric_row, top_etf_cards, stats_table,
    data_status_card, alert_banner,
)
from components.charts import sparkline_chart
from components.formatting import fmt_pct, color_for_value, MUTED, BG_CARD, BORDER
from components.constants import GREEN, RED, GOLD

st.set_page_config(page_title="Podsumowanie", page_icon="🏠", layout="wide")
setup_sidebar()

st.markdown("# 🏠 Podsumowanie")
st.caption("Centrum dowodzenia — najwazniejsze sygnaly i metryki w jednym miejscu")

# --- Dane ---
tickers = list(set(ALL_TICKERS + st.session_state.get("custom_tickers", [])))
prices = download_prices(tickers)
rf = get_risk_free()

# =====================================================================
# Status danych (F3)
# =====================================================================
data_status_card()

# =====================================================================
# Alerty cenowe (F1)
# =====================================================================
alerts = st.session_state.get("alerts", [])
if alerts:
    ALERT_PERIOD_DAYS = {"1D": 1, "1W": 5, "1M": 21}
    for a in alerts:
        s = download_single(a["ticker"], period="3mo")
        if s is not None and len(s) > ALERT_PERIOD_DAYS.get(a["period"], 1):
            days = ALERT_PERIOD_DAYS.get(a["period"], 1)
            actual_chg = s.iloc[-1] / s.iloc[-1 - days] - 1
            alert_banner(a["ticker"], a["condition"], a["threshold"],
                         a["period"], actual_chg)

# =====================================================================
# Sekcja 1: Sygnal GEM
# =====================================================================
st.markdown("### Sygnal GEM")
gem_data = gem_classic_signal(prices, rf)
signal_card(gem_data)
metric_row(
    gem_data["qqq_12m"], gem_data["vea_12m"], gem_data["eem_12m"],
    gem_data["acwi_12m"], gem_data["agg_12m"], rf,
)

st.divider()

# =====================================================================
# Sekcja 2: Macro Regime (Risk-On/Off + VIX)
# =====================================================================
st.markdown("### Regime rynkowy")

# Pobierz dane do regime
regime_tickers = {"SPY": "S&P 500", "AGG": "Obligacje", "GC=F": "Zloto",
                  "DX-Y.NYB": "Dolar (DXY)", "CL=F": "Ropa WTI"}
regime_data = {}
for t in regime_tickers:
    s = download_single(t, period="1y")
    if s is not None and len(s) > 0:
        regime_data[t] = s

# VIX
vix_data = download_single("^VIX", period="1y")

col_regime, col_vix = st.columns(2)

# --- Risk-On / Risk-Off ---
with col_regime:
    signals = {}
    for t, s in regime_data.items():
        if len(s) > 63:
            mom_3m = s.iloc[-1] / s.iloc[-63] - 1
            signals[t] = mom_3m

    risk_on_count = 0
    risk_off_count = 0
    for t, mom in signals.items():
        if t == "SPY":
            if mom > 0:
                risk_on_count += 2
            else:
                risk_off_count += 2
        elif t in ("AGG", "GC=F"):
            if mom > 0:
                risk_off_count += 1
            else:
                risk_on_count += 1
        elif t == "DX-Y.NYB":
            if mom > 0:
                risk_off_count += 1
            else:
                risk_on_count += 1
        elif t == "CL=F":
            if mom > 0:
                risk_on_count += 1
            else:
                risk_off_count += 1

    total = risk_on_count + risk_off_count
    risk_on_pct = risk_on_count / total * 100 if total > 0 else 50

    if risk_on_pct >= 65:
        regime_color, regime_label = GREEN, "Risk-On"
        regime_desc = "Srodowisko sprzyjajace akcjom"
    elif risk_on_pct <= 35:
        regime_color, regime_label = RED, "Risk-Off"
        regime_desc = "Awersja do ryzyka — rozwazyc obligacje"
    else:
        regime_color, regime_label = "#F59E0B", "Neutralny"
        regime_desc = "Mieszane sygnaly miedzy klasami aktywow"

    st.html(
        f'<div style="background:{BG_CARD};border:2px solid {regime_color};border-radius:16px;padding:24px;text-align:center">'
        f'<div style="font-size:0.75rem;color:{MUTED};text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px">Regime rynkowy</div>'
        f'<div style="font-size:1.8rem;font-weight:800;color:{regime_color}">{regime_label}</div>'
        f'<div style="font-size:0.85rem;color:{MUTED};margin-top:6px">{regime_desc}</div>'
        f'<div style="font-size:0.8rem;color:{MUTED};margin-top:12px">Risk-On score: {risk_on_pct:.0f}%</div>'
        f'</div>'
    )

# --- VIX ---
with col_vix:
    if vix_data is not None and len(vix_data) > 0:
        vix_val = vix_data.iloc[-1]
        if vix_val < 15:
            vix_color, vix_label = GREEN, "Niski strach"
        elif vix_val < 25:
            vix_color, vix_label = "#F59E0B", "Umiarkowany"
        else:
            vix_color, vix_label = RED, "Wysoki strach"

        # Zmiana 1D
        vix_chg = ""
        if len(vix_data) > 1:
            chg = vix_data.iloc[-1] - vix_data.iloc[-2]
            chg_color = RED if chg > 0 else GREEN
            sign = "+" if chg > 0 else ""
            vix_chg = f'<div style="font-size:0.8rem;color:{chg_color};margin-top:8px">1D: {sign}{chg:.2f} pkt</div>'

        st.html(
            f'<div style="background:{BG_CARD};border:2px solid {vix_color};border-radius:16px;padding:24px;text-align:center">'
            f'<div style="font-size:0.75rem;color:{MUTED};text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px">VIX — Indeks strachu</div>'
            f'<div style="font-size:1.8rem;font-weight:800;color:{vix_color}">{vix_val:.2f}</div>'
            f'<div style="font-size:0.85rem;color:{MUTED};margin-top:6px">{vix_label}</div>'
            f'{vix_chg}'
            f'</div>'
        )
    else:
        st.warning("Nie udalo sie pobrac danych VIX.")

st.divider()

# =====================================================================
# Sekcja 3: Top 5 ETFs
# =====================================================================
st.markdown("### Top 5 ETF-ow wg momentum")
ranking = build_ranking(prices, rf)
names = dict(ETF_NAMES)
categories = dict(ETF_CATEGORY_MAP)
for t in st.session_state.get("custom_tickers", []):
    names.setdefault(t, t)
    categories.setdefault(t, "Wlasne")

valid_ranking = ranking.dropna(subset=["Wynik"])
if not valid_ranking.empty:
    top_etf_cards(valid_ranking, names, categories, n=5)
else:
    st.warning("Brak danych do wyswietlenia rankingu.")

st.divider()

# =====================================================================
# Sekcja 4: Sparklines kluczowych aktywow
# =====================================================================
st.markdown("### Kluczowe aktywa")

spark_tickers = [
    ("QQQ", "Nasdaq 100"),
    ("AGG", "Obligacje USA"),
    ("GC=F", "Zloto (USD/oz)"),
    ("BTC-USD", "Bitcoin"),
]

spark_cols = st.columns(len(spark_tickers))
for col, (ticker, label) in zip(spark_cols, spark_tickers):
    with col:
        s = download_single(ticker, period="6mo")
        if s is not None and len(s) > 21:
            current = s.iloc[-1]
            chg_1m = s.iloc[-1] / s.iloc[-21] - 1

            chg_color = color_for_value(chg_1m)
            sign = "+" if chg_1m > 0 else ""

            st.html(
                f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;padding:12px;text-align:center">'
                f'<div style="font-size:0.7rem;color:{MUTED};text-transform:uppercase;letter-spacing:0.05em">{label}</div>'
                f'<div style="font-size:1.2rem;font-weight:700;color:#E5E7EB;margin:4px 0">{current:,.2f}</div>'
                f'<div style="font-size:0.8rem;color:{chg_color};font-weight:600">{sign}{chg_1m*100:.1f}% (1M)</div>'
                f'</div>'
            )
            st.plotly_chart(sparkline_chart(s, height=100), use_container_width=True)
        else:
            st.caption(f"{label}: brak danych")

# =====================================================================
# Sekcja 4b: Ulubione tickery (F8)
# =====================================================================
favorites = st.session_state.get("favorites", set())
if favorites:
    st.divider()
    st.markdown("### ⭐ Ulubione")
    fav_list = sorted(favorites)
    fav_cols = st.columns(min(4, len(fav_list)))
    for i, ticker in enumerate(fav_list):
        with fav_cols[i % min(4, len(fav_list))]:
            s = download_single(ticker, period="6mo")
            if s is not None and len(s) > 21:
                current = s.iloc[-1]
                chg_1m = s.iloc[-1] / s.iloc[-21] - 1
                chg_color = color_for_value(chg_1m)
                sign = "+" if chg_1m > 0 else ""

                st.html(
                    f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:12px;padding:12px;text-align:center">'
                    f'<div style="font-size:0.7rem;color:{MUTED};text-transform:uppercase;letter-spacing:0.05em">{ticker}</div>'
                    f'<div style="font-size:1.2rem;font-weight:700;color:#E5E7EB;margin:4px 0">{current:,.2f}</div>'
                    f'<div style="font-size:0.8rem;color:{chg_color};font-weight:600">{sign}{chg_1m*100:.1f}% (1M)</div>'
                    f'</div>'
                )
                st.plotly_chart(sparkline_chart(s, height=80), use_container_width=True)
            else:
                st.caption(f"{ticker}: brak danych")

st.divider()

# =====================================================================
# Sekcja 5: Podsumowanie strategii (GEM 5Y backtest)
# =====================================================================
st.markdown("### Podsumowanie strategii (5 lat)")

bt_prices = download_prices(["QQQ", "VEA", "EEM", "ACWI", "AGG"], period="7y")
bt_result = backtest_gem(bt_prices, rf)

if bt_result is not None:
    bt_stats = bt_result["stats"]
    # Pokaz GEM vs QQQ B&H
    show_stats = {}
    if "GEM" in bt_stats:
        show_stats["GEM"] = bt_stats["GEM"]
    if "QQQ B&H" in bt_stats:
        show_stats["QQQ B&H"] = bt_stats["QQQ B&H"]
    if "ACWI B&H" in bt_stats:
        show_stats["ACWI B&H"] = bt_stats["ACWI B&H"]
    if "AGG B&H" in bt_stats:
        show_stats["AGG B&H"] = bt_stats["AGG B&H"]

    if show_stats:
        stats_table(show_stats)
else:
    st.info("Za malo danych do backtestu GEM (wymagane 273+ sesji).")

st.divider()

# =====================================================================
# Sekcja 6: Export PDF (F10)
# =====================================================================
with st.expander("📄 Eksport raportu PDF"):
    st.caption("Wybierz sekcje do wlaczenia w raport")

    pdf_gem = st.checkbox("Sygnal GEM", value=True, key="pdf_gem")
    pdf_regime = st.checkbox("Regime rynkowy", value=True, key="pdf_regime")
    pdf_top5 = st.checkbox("Top 5 ETF-ow", value=True, key="pdf_top5")
    pdf_sparks = st.checkbox("Kluczowe aktywa", value=True, key="pdf_sparks")
    pdf_backtest = st.checkbox("Statystyki strategii", value=True, key="pdf_bt")
    pdf_ranking = st.checkbox("Ranking ETF top 10", value=True, key="pdf_rank")

    if st.button("Generuj raport PDF", key="pdf_gen_btn"):
        from components.pdf_report import generate_report

        report_sections = {}

        if pdf_gem:
            report_sections["gem_signal"] = gem_data

        if pdf_regime:
            report_sections["regime"] = {"label": regime_label, "score": risk_on_pct}

        if pdf_top5 and not valid_ranking.empty:
            top5_list = []
            for ticker, row in valid_ranking.head(5).iterrows():
                top5_list.append((ticker, names.get(ticker, ticker), row.get("Wynik", 0)))
            report_sections["top_etfs"] = top5_list

        if pdf_sparks:
            sparks_list = []
            for ticker, label in spark_tickers:
                s = download_single(ticker, period="6mo")
                if s is not None and len(s) > 21:
                    sparks_list.append((ticker, label, s.iloc[-1], s.iloc[-1] / s.iloc[-21] - 1))
            report_sections["sparklines"] = sparks_list

        if pdf_backtest and bt_result is not None:
            report_sections["backtest_stats"] = show_stats if show_stats else {}

        if pdf_ranking and not valid_ranking.empty:
            rank_list = []
            for ticker, row in valid_ranking.head(10).iterrows():
                rank_list.append((
                    ticker, names.get(ticker, ticker),
                    row.get("Wynik", 0), row.get("Momentum_abs", "—"),
                ))
            report_sections["ranking_top10"] = rank_list

        if report_sections:
            pdf_bytes = generate_report(report_sections)
            st.download_button(
                "📥 Pobierz PDF",
                data=pdf_bytes,
                file_name=f"gem_raport_{pd.Timestamp.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
            )
        else:
            st.warning("Wybierz co najmniej jedna sekcje.")

render_footer()
