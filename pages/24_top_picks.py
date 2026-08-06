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
from data.downloader import download_prices, download_stooq
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
# GPW leci przez stooq — yfinance nie ma historii indeksow WIG (zwraca 1 wiersz).
BENCHMARKS = {
    "sp500": {"ticker": "SPY", "source": "yfinance"},
    "gpw": {"ticker": "WIG20", "source": "stooq"},
}
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
st.caption(f"Regula v{latest.get('rule_version', '?')}")

for market, label in MARKET_LABELS.items():
    picks = latest.get(market) or []
    if not picks:
        continue

    # Data z entry_date pickow, NIE z pola asof — rynki koncza sesje w roznych
    # momentach (GPW zamyka sie wczesniej niz USA), a asof w snapshocie trzyma
    # tylko jedna, wspolna wartosc.
    sesje = sorted({p.get("entry_date", "") for p in picks if p.get("entry_date")})
    dzien = sesje[-1] if sesje else latest.get("asof", "—")
    st.markdown(f"### {label}")
    st.caption(f"Policzone na zamkniecie {dzien}")
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
        width="stretch",
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
        cfg = BENCHMARKS[market]
        bench = cfg["ticker"]
        if cfg["source"] == "stooq":
            prices = download_prices(all_tickers, period="5y")
            bench_raw = download_stooq(bench, period="5y")
        else:
            prices = download_prices(all_tickers + [bench], period="5y")
            bench_raw = prices[bench] if bench in prices.columns else None

        equity = portfolio_equity(history, prices, market)
        if equity.empty:
            continue

        curves = {f"Top Picks {label}": equity}
        if bench_raw is not None and not bench_raw.empty:
            aligned = bench_raw.reindex(equity.index, method="ffill").dropna()
            if not aligned.empty and float(aligned.iloc[0]) != 0:
                curves[bench] = (bench_raw.reindex(equity.index, method="ffill")
                                 / float(aligned.iloc[0]) * 10000.0)

        st.markdown(f"### {label}")
        col1, col2, col3 = st.columns(3)
        total = float(equity.iloc[-1] / equity.iloc[0] - 1)
        col1.metric("Zwrot od startu", fmt_pct(total))
        col2.metric("Rebalansow", str(len(history)))
        col3.metric("Kapital startowy", f"10 000 {CURRENCY[market]}")

        st.plotly_chart(equity_chart(curves, title=f"Top Picks {label} vs {bench}"),
                        width="stretch")

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
            curves = {f"Regula {label}": pd.Series(block["equity"], index=index)}
            bench_name = block.get("benchmark_name")
            bench_values = block.get("benchmark") or []
            has_bench = bool(bench_name) and len(bench_values) == len(index)
            if has_bench:
                curves[bench_name] = pd.Series(bench_values, index=index)
            stats = block.get("stats", {})

            st.markdown(f"#### {label}")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("CAGR", fmt_pct(stats.get("cagr")))
            col2.metric("Max DD", fmt_pct(stats.get("max_dd")))
            col3.metric("Sharpe", f"{stats.get('sharpe', 0):.2f}")
            col4.metric("Trafnosc vs benchmark",
                        fmt_pct(stats.get("hit_rate")) if has_bench else "—")
            st.plotly_chart(equity_chart(curves, title=f"Symulacja reguly — {label}"),
                            width="stretch")

render_footer()
