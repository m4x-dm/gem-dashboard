"""Strona 24: Top Picks — miesieczna piatka spolek z S&P 500 i GPW.

Strona NIC nie liczy. Sklad i symulacja przychodza z artefaktow generowanych
przez scripts/update_top_picks.py (GitHub Action, 1. dnia miesiaca).
"""

import json

import pandas as pd
import streamlit as st

from components.auth import require_premium
from components.charts import equity_chart
from components.formatting import fmt_pct
from components.sidebar import render_footer, setup_sidebar
from data.downloader import download_prices
from data.financials import bulk_fetch_universe
from data.top_picks import (
    HISTORY_PATH,
    RULE_VERSION,
    SIM_PATH,
    load_history,
    portfolio_equity,
)

st.set_page_config(page_title="Top Picks", page_icon="🎯", layout="wide")
setup_sidebar()
if not require_premium(24):
    st.stop()

MARKET_LABELS = {"sp500": "🇺🇸 S&P 500", "gpw": "🇵🇱 GPW"}
BENCHMARKS = {"sp500": "SPY", "gpw": "WIG20.WA"}
CURRENCY = {"sp500": "USD", "gpw": "PLN"}

st.markdown("# 🎯 Top Picks — piatka miesiaca")
st.caption(
    "Piatka spolek z kazdego rynku, wybierana pierwszego dnia miesiaca deterministyczna "
    "regula: momentum (12M/6M/3M/1M) + maks. 2 spolki na sektor + prog plynnosci. "
    "Sklad nie jest recznie korygowany."
)

history = load_history()
if not history:
    st.warning(
        f"Brak pliku `{HISTORY_PATH.name}`. Uruchom `python scripts/update_top_picks.py`, "
        "zeby wygenerowac pierwszy snapshot."
    )
    render_footer()
    st.stop()

latest_key = sorted(history)[-1]
latest = history[latest_key]

versions = {snap.get("rule_version", 0) for snap in history.values()}
if len(versions) > 1:
    st.warning(
        f"⚠️ Log zawiera snapshoty z roznych wersji reguly ({sorted(versions)}). "
        f"Wyniki sprzed zmiany nie sa porownywalne z obecnymi (aktualna: v{RULE_VERSION})."
    )

# ====== Sekcja 1: aktualna piatka ======
st.markdown(f"## Sklad na {latest_key}")
st.caption(
    f"Policzony na zamkniecie {latest.get('asof', '—')} · regula v{latest.get('rule_version', '?')}"
)

for market, label in MARKET_LABELS.items():
    picks = latest.get(market) or []
    if not picks:
        continue

    st.markdown(f"### {label}")
    tickers = [p["ticker"] for p in picks]
    prices = download_prices(tickers, period="1y")
    funda = bulk_fetch_universe(tuple(tickers))

    rows = []
    for pick in picks:
        ticker = pick["ticker"]
        now = None
        if ticker in prices.columns:
            series = prices[ticker].dropna()
            now = float(series.iloc[-1]) if not series.empty else None
        entry = pick["entry_price"]
        info = funda.get(ticker, {}) or {}
        rows.append({
            "Ticker": ticker,
            "Nazwa": pick.get("name", ""),
            "Sektor": pick.get("group", ""),
            "Score": round(pick["score"], 3),
            f"Wejscie ({CURRENCY[market]})": round(entry, 2),
            "Teraz": round(now, 2) if now else None,
            "Zwrot": (now / entry - 1) if now else None,
            "P/E": info.get("pe"),
            "Fwd P/E": info.get("fwd_pe"),
            "ROE": info.get("roe"),
            "Dyw. %": info.get("dividend_yield"),
        })

    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Zwrot": st.column_config.NumberColumn("Zwrot od rebalansu", format="percent"),
            "ROE": st.column_config.NumberColumn("ROE", format="%.2f"),
        },
    )

st.info(
    "Kolumny fundamentalne (P/E, Fwd P/E, ROE, dywidenda) sa **kontekstem do samodzielnej "
    "oceny** — nie biora udzialu w wyborze spolek. Regula patrzy wylacznie na momentum, "
    "plynnosc i limit sektorowy."
)

# ====== Sekcja 2: wyniki live ======
st.markdown("---")
st.markdown("## Wyniki live")

if len(history) < 2:
    st.info(
        f"Track record narasta od pierwszego snapshotu ({sorted(history)[0]}). "
        "Krzywa kapitalu pojawi sie po pierwszym rebalansie — wroc za miesiac."
    )
else:
    for market, label in MARKET_LABELS.items():
        all_tickers = sorted({p["ticker"] for snap in history.values()
                              for p in (snap.get(market) or [])})
        if not all_tickers:
            continue
        bench = BENCHMARKS[market]
        prices = download_prices(all_tickers + [bench], period="5y")
        equity = portfolio_equity(history, prices, market)
        if equity.empty:
            continue

        curves = {f"Top Picks {label}": equity}
        if bench in prices.columns:
            bench_series = prices[bench].reindex(equity.index, method="ffill")
            curves[bench] = bench_series / bench_series.iloc[0] * 10000.0

        st.markdown(f"### {label}")
        col1, col2, col3 = st.columns(3)
        total = float(equity.iloc[-1] / equity.iloc[0] - 1)
        col1.metric("Zwrot od startu", fmt_pct(total))
        col2.metric("Rebalansow", str(len(history)))
        col3.metric("Kapital startowy", f"10 000 {CURRENCY[market]}")

        st.plotly_chart(equity_chart(curves, title=f"Top Picks {label} vs {bench}"),
                        use_container_width=True)

# ====== Sekcja 3: symulacja reguly ======
st.markdown("---")
with st.expander("🔬 Symulacja reguly wstecz — przeczytaj zastrzezenie", expanded=False):
    st.error(
        "**To nie jest track record.** Sklad historyczny liczony z DZISIEJSZEGO universe "
        "(SP500_TOP100 i obecne sklady WIG20/mWIG40/sWIG80). Spolki, ktore wypadly z "
        "indeksow, w danych nie istnieja — survivorship bias zawyza wynik. Traktuj to jako "
        "test spojnosci reguly, nie jako obietnice zwrotu."
    )

    if not SIM_PATH.exists():
        st.info(f"Brak pliku `{SIM_PATH.name}`. Uruchom `python scripts/update_top_picks.py`.")
    else:
        sim = json.loads(SIM_PATH.read_text(encoding="utf-8"))
        params = sim.get("params", {})
        st.caption(
            f"Wygenerowano: {sim.get('generated_at', '—')} · regula v{sim.get('rule_version', '?')} · "
            f"koszty {params.get('transaction_cost', 0):.1%} + Belka {params.get('tax_belka', 0):.0%}"
        )

        for market, label in MARKET_LABELS.items():
            block = sim.get(market)
            if not block:
                continue
            index = pd.DatetimeIndex(block["dates"])
            curves = {
                f"Regula {label}": pd.Series(block["equity"], index=index),
                block.get("benchmark_name", "Benchmark"): pd.Series(block["benchmark"], index=index),
            }
            stats = block.get("stats", {})

            st.markdown(f"#### {label}")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("CAGR", fmt_pct(stats.get("cagr")))
            col2.metric("Max DD", fmt_pct(stats.get("max_dd")))
            col3.metric("Sharpe", f"{stats.get('sharpe', 0):.2f}")
            col4.metric("Trafnosc vs benchmark", fmt_pct(stats.get("hit_rate")))
            st.plotly_chart(equity_chart(curves, title=f"Symulacja reguly — {label}"),
                            use_container_width=True)

render_footer()
