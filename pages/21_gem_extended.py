"""Strona 21: GEM Extended — backtest GEM z konfigurowalnym universe.

Rozszerzenie klasycznego GEM Antonacciego (5 ETF, top 1) o:
- Dowolne risk_assets (do 10+ ETF, krypto, sektorow)
- Top N equal-weight (1/2/3/5) zamiast 100% all-in
- Konfigurowalne safe_asset (AGG / TLT / SHV)
"""

import streamlit as st
import pandas as pd
from components.sidebar import setup_sidebar, get_risk_free, render_footer
from data.downloader import download_prices
from data.momentum import backtest_gem_extended
from components.cards import stats_table
from components.charts import equity_chart
from components.formatting import GOLD, MUTED, GREEN, RED, BG_CARD, BORDER
from components.auth import require_premium

st.set_page_config(page_title="GEM Extended", page_icon="🚀", layout="wide")
setup_sidebar()
if not require_premium(21):
    st.stop()

st.markdown("# 🚀 GEM Extended — backtest rozszerzonego universe")
st.caption(
    "Klasyczny GEM (Antonacci 2014) trzyma 100% w jednym aktywie z 5 ETF (QQQ/VEA/EEM/ACWI/AGG). "
    "GEM Extended pozwala dodac wiecej kandydatow (GLD, TLT, VNQ, IWM, BTC) i trzymac top N "
    "equal-weight — wiekszy CAGR za cene wiekszego drawdownu."
)

# ====== Presets ======
PRESETS = {
    "5-ETF baseline (klasyczny GEM)": {
        "risk": ["QQQ", "VEA", "EEM", "ACWI"],
        "safe": "AGG",
        "top_n": 1,
    },
    "8-ETF z gold/REIT/TLT (no crypto)": {
        "risk": ["QQQ", "VEA", "EEM", "ACWI", "GLD", "TLT", "VNQ"],
        "safe": "AGG",
        "top_n": 2,
    },
    "10-ETF z BTC + IWM + SPY (agresywny)": {
        "risk": ["QQQ", "SPY", "VEA", "EEM", "GLD", "TLT", "VNQ", "IWM", "BTC-USD"],
        "safe": "AGG",
        "top_n": 2,
    },
    "10-ETF z BTC, TLT fallback": {
        "risk": ["QQQ", "SPY", "VEA", "EEM", "GLD", "TLT", "VNQ", "IWM", "BTC-USD"],
        "safe": "TLT",
        "top_n": 2,
    },
    "10-ETF z BTC, Top-3 zdywersyfikowany": {
        "risk": ["QQQ", "SPY", "VEA", "EEM", "GLD", "TLT", "VNQ", "IWM", "BTC-USD"],
        "safe": "AGG",
        "top_n": 3,
    },
    "Custom": None,
}

AVAILABLE_RISK = [
    "QQQ", "SPY", "VEA", "EEM", "ACWI",      # akcje globalne
    "GLD", "SLV",                              # metale szlachetne
    "TLT", "IEF",                              # dlugie obligacje USA
    "VNQ", "REM",                              # REIT
    "IWM", "IJR",                              # small cap USA
    "VTV", "VUG",                              # US value / growth
    "XLE", "XLF", "XLK", "XLV",                # sektory USA
    "BTC-USD", "ETH-USD",                      # krypto
]
AVAILABLE_SAFE = ["AGG", "TLT", "IEF", "BIL", "SHV", "BND"]

# ====== UI ======
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    preset_label = st.selectbox(
        "Preset universe",
        list(PRESETS.keys()),
        index=2,
        help="Wybierz gotowy zestaw albo Custom dla wlasnej konfiguracji.",
    )
with col2:
    period_options = ["5y", "7y", "10y", "15y", "max"]
    period = st.selectbox("Okres backtestu", period_options, index=3)
with col3:
    start_capital = st.number_input(
        "Kapital poczatkowy ($)", min_value=1000, value=10000, step=1000
    )

if preset_label == "Custom":
    risk_default = ["QQQ", "VEA", "EEM", "GLD", "TLT", "BTC-USD"]
    safe_default = "AGG"
    top_n_default = 2
else:
    preset = PRESETS[preset_label]
    risk_default = preset["risk"]
    safe_default = preset["safe"]
    top_n_default = preset["top_n"]

col4, col5, col6 = st.columns([3, 1, 1])
with col4:
    risk_assets = st.multiselect(
        "Risk assets (aktywa ryzykowne — kandydaci do top N)",
        AVAILABLE_RISK,
        default=risk_default,
        help="Z tych aktywow strategia wybiera top N po momentum 12M.",
    )
with col5:
    safe_asset = st.selectbox(
        "Safe asset (fallback)",
        AVAILABLE_SAFE,
        index=AVAILABLE_SAFE.index(safe_default) if safe_default in AVAILABLE_SAFE else 0,
        help="Gdy zaden risk asset nie ma momentum > rf, portfel idzie tu.",
    )
with col6:
    top_n = st.selectbox(
        "Top N (ile aktywow equal-weight)",
        [1, 2, 3, 5],
        index=[1, 2, 3, 5].index(top_n_default) if top_n_default in [1, 2, 3, 5] else 1,
    )

col7, col8, col9 = st.columns(3)
with col7:
    lookback = st.selectbox(
        "Lookback momentum (dni)",
        [126, 189, 252, 273],
        index=2,
        format_func=lambda x: {126: "6M", 189: "9M", 252: "12M (default)", 273: "13M"}[x],
    )
with col8:
    skip = st.selectbox(
        "Skip (dni od konca)",
        [0, 21],
        index=0,
        format_func=lambda x: "0 (no skip — default dla ETF)" if x == 0 else "21 (skip-month — klasyczny Jegadeesh)",
    )
with col9:
    benchmark_choice = st.selectbox(
        "Benchmark B&H",
        ["SPY", "QQQ", "VWCE", "ACWI", "Brak"],
        index=0,
    )

with st.expander("Koszty transakcji i podatek Belki"):
    cc1, cc2 = st.columns(2)
    with cc1:
        transaction_cost = st.slider(
            "Koszt transakcji (%)", 0.0, 0.5, 0.0, 0.05,
            help="Roundtrip cost, skalowany frakcja zmienionych aktywow (turnover).",
        )
    with cc2:
        tax_belka = st.slider(
            "Podatek Belki (%)", 0.0, 19.0, 0.0, 1.0,
            help="Pobierany od zysku segmentu przy zmianie holdings (uproszczenie — brak rolowania strat).",
        )

st.divider()

# ====== Walidacja ======
if len(risk_assets) < top_n:
    st.error(
        f"❌ Musisz wybrac co najmniej {top_n} risk asset (obecnie wybrane: {len(risk_assets)})."
    )
    st.stop()
if not risk_assets:
    st.error("❌ Wybierz przynajmniej 1 risk asset.")
    st.stop()

# ====== Pobierz dane + uruchom backtest ======
rf = get_risk_free()
needed_tickers = list(set(risk_assets + [safe_asset]))
if benchmark_choice != "Brak" and benchmark_choice not in needed_tickers:
    needed_tickers.append(benchmark_choice)

with st.spinner(f"Pobieram dane ({len(needed_tickers)} aktywow, {period})..."):
    prices = download_prices(needed_tickers, period=period)

if prices is None or prices.empty:
    st.error("❌ Nie udalo sie pobrac danych. Sprobuj odswiezyc strone.")
    st.stop()

# Sprawdz dostepnosc
available_in_prices = list(prices.columns)
missing = [t for t in needed_tickers if t not in available_in_prices]
if missing:
    st.warning(f"⚠️ Brakuje danych dla: {', '.join(missing)}. Pomijam te aktywa.")
    risk_assets = [r for r in risk_assets if r in available_in_prices]
    if safe_asset not in available_in_prices:
        st.error(f"❌ Brak danych dla safe asset {safe_asset}. Wybierz inny.")
        st.stop()
    if len(risk_assets) < top_n:
        st.error(f"❌ Po pominieciu brakujacych aktywow zostalo {len(risk_assets)} < top_n={top_n}.")
        st.stop()

with st.spinner("Licze backtest..."):
    res = backtest_gem_extended(
        prices=prices,
        risk_free_annual=rf,
        risk_assets=risk_assets,
        safe_asset=safe_asset,
        top_n=top_n,
        lookback=lookback,
        skip=skip,
        start_capital=float(start_capital),
        transaction_cost=transaction_cost / 100.0,
        tax_belka=tax_belka / 100.0,
        benchmark_ticker=benchmark_choice if benchmark_choice != "Brak" else None,
    )

if res is None:
    st.error(
        f"❌ Za malo danych. Wybrany okres ({period}) ma mniej niz {lookback + 10} sesji "
        "dla wszystkich wybranych aktywow. Wybierz dluzszy okres lub usun aktywa z krotka historia "
        "(np. BTC-USD od 2014, ETH-USD od 2017)."
    )
    st.stop()

st.success(
    f"✅ Backtest gotowy — {len(res['equity'])} dni handlowych, "
    f"od {res['equity'].index[0].date()} do {res['equity'].index[-1].date()} "
    f"(~{len(res['equity'])/252:.1f} lat)"
)

# ====== Wyniki ======
st.markdown(f"## 📊 Statystyki ({len(risk_assets)} risk + {safe_asset}, Top-{top_n}, momentum {lookback}d skip={skip})")
stats_table(res["stats"])

st.markdown("## 📈 Equity curve")
equity_dict = {f"GEM Ext Top-{top_n}": res["equity"]}
if "equity_benchmark" in res:
    equity_dict[f"{benchmark_choice} B&H"] = res["equity_benchmark"]
equity_dict[f"{safe_asset} B&H"] = res["equity_safe"]
equity_chart(equity_dict)

# ====== Historia trzymanych pozycji ======
st.markdown("## 🔄 Historia rotacji (kazda zmiana holdings)")
hist = res["holdings_history"]
if hist:
    hist_df = pd.DataFrame([
        {"Data": d.date(), "Holdings": " + ".join(h)} for d, h in hist
    ])
    st.dataframe(hist_df, hide_index=True, use_container_width=True)
    st.caption(f"Lacznie {len(hist)} zmian holdings w {len(res['equity'])/252:.1f}-letnim oknie "
               f"(~{len(hist)/(len(res['equity'])/252):.1f} zmian/rok).")

# ====== Disclaimer ======
st.divider()
with st.expander("⚠️ Wazne ostrzezenia (kliknij)"):
    st.markdown("""
    **GEM Extended to NIE jest klasyczny GEM Antonacciego.** Klasyczny GEM trzyma 100% w jednym
    z 5 ETF — to filozofia "dual momentum" testowana akademicko. Dodanie kandydatow (BTC, sektory,
    REIT, gold) i top N equal-weight to **trend-following na multi-asset**, ktore historycznie
    daje wiekszy CAGR ale wymaga wiekszej tolerancji na drawdown.

    **Najwazniejsze pulapki:**
    - **Hindsight bias** — BTC ma 50% CAGR od 2014, ale w 2014 nikt nie wiedzial, ze tak bedzie.
      Wybor "BTC w universe" w 2026 jest oczywisty; w 2014 — nie.
    - **Drawdown moze przekraczac -50%** — strategia z BTC + Top-1 miala MaxDD -82% (krach krypto 2022).
      Backtest pokazuje liczby, ale przezycie tego psychicznie jest inna sprawa.
    - **Backtest != live** — nie uwzglednia slippage, spreadu bid-ask, podatkow dla obrotow w krypto
      (19% Belki + tracking transakcji), opoznien w realizacji.
    - **Survivorship bias** — universe ETF/krypto, ktore istnieja dzisiaj, to te ktore przetrwaly.
      Te ktore upadly (Luna, FTX-related tokens) sa wykluczone — to zawysza wyniki.
    - **Z BTC zmienia sie filozofia** — strategia przestaje byc "Global EQUITY Momentum" a staje
      sie "multi-asset trend following". To nie jest gorsza strategia — ale to nie jest GEM.

    **Praktyczna rekomendacja:** zacznij od **5-ETF baseline** (klasyczny GEM). Jesli akceptujesz
    wiekszy drawdown za wieksze CAGR, sprobuj **8-ETF z gold/REIT/TLT (no crypto)**. Krypto dodawaj
    DOPIERO gdy rozumiesz risk i masz maksymalnie 5-10% portfela w tej alokacji.
    """)

render_footer()
