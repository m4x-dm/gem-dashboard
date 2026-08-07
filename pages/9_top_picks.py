"""Strona 9: Top Picks — miesieczna piatka spolek z S&P 500 i GPW.

Strona NIC nie liczy. Sklad i symulacja przychodza z artefaktow generowanych
przez scripts/update_top_picks.py (GitHub Action, 1. dnia miesiaca).
"""

import json
from collections import Counter
from datetime import date

import pandas as pd
import streamlit as st

from components.auth import require_premium
from components.cards import kpi_card, section_band, top_pick_cards
from components.charts import category_pie, equity_chart, picks_return_bar
from components.formatting import GREEN, MUTED, RED, fmt_number, fmt_pct
from components.sidebar import render_footer, setup_sidebar
from data.downloader import download_prices, download_stooq
from data.financials import bulk_fetch_universe
from data.top_picks import (
    HISTORY_PATHS,
    RULE_VERSIONS,
    SIM_PATH,
    STRATEGY_MARKETS,
    load_history,
    portfolio_equity,
)

st.set_page_config(page_title="Top Picks", page_icon="🎯", layout="wide")
setup_sidebar()
if not require_premium(9):
    st.stop()

MARKET_LABELS = {"sp500": "🇺🇸 S&P 500", "gpw": "🇵🇱 GPW"}
# GPW leci przez stooq — yfinance nie ma historii indeksow WIG (zwraca 1 wiersz).
BENCHMARKS = {
    "sp500": {"ticker": "SPY", "source": "yfinance"},
    "gpw": {"ticker": "WIG20", "source": "stooq"},
}
CURRENCY = {"sp500": "USD", "gpw": "PLN"}
SPARK_SESSIONS = 63  # ~3 miesiace sesji

EXTRA_COLUMNS = {
    "momentum": {"P/E": "pe", "Fwd P/E": "fwd_pe", "ROE": "roe",
                 "Dyw. %": "dividend_yield"},
    "earnings": {"P/E": "pe", "Fwd P/E": "fwd_pe", "ROE": "roe",
                 "Marza %": "profit_margin"},
    "quality": {"ROE": "roe", "Marza %": "profit_margin",
                "Wzrost przych. %": "revenue_growth", "Debt/Eq": "debt_to_equity"},
}

STRATEGY_INFO = {
    "momentum": (
        "Momentum",
        "Ranking po momentum cenowym (12M/6M/3M/1M z anti-1M), "
        "maks. 2 spolki na sektor, prog plynnosci.",
    ),
    "earnings": (
        "Earnings Momentum",
        "Ranking po jakosci wynikow: seria pobic konsensusu (0-4 kwartaly), "
        "wielkosc zaskoczenia EPS i rewizje prognoz analitykow w oknie 90 dni.",
    ),
    "quality": (
        "Jakosc biznesu",
        "Ranking po ROE, marzy netto, wzroscie przychodow i niskim zadluzeniu. "
        "Dla bankow komponent zadluzenia jest pomijany, a wagi renormalizowane.",
    ),
}


def _next_rebalance(today: date) -> date:
    """Pierwszy dzien nastepnego miesiaca — wtedy GitHub Action liczy nowa piatke."""
    if today.month == 12:
        return date(today.year + 1, 1, 1)
    return date(today.year, today.month + 1, 1)


# ====== Sekcja 0: naglowek ze skladem ======

def render_naglowek(latest_key: str, latest: dict, markets: tuple) -> None:
    """Karta z data ostatniego skladu i odliczaniem do rebalansu."""
    today = date.today()
    nxt = _next_rebalance(today)
    days_left = (nxt - today).days
    n_picks = sum(len(latest.get(m) or []) for m in markets)
    rynki = "rynki" if len(markets) > 1 else "rynek"

    st.html(
        f'<div style="background:#141929;border:1px solid rgba(201,168,76,0.2);border-radius:14px;'
        f'padding:16px 20px;margin:8px 0 4px;display:flex;flex-wrap:wrap;gap:12px;'
        f'justify-content:space-between;align-items:center">'
        f'<div>'
        f'<div style="font-size:0.68rem;color:{MUTED};text-transform:uppercase;'
        f'letter-spacing:0.08em">Sklad na</div>'
        f'<div style="font-size:1.5rem;font-weight:800;color:#C9A84C;line-height:1.2">{latest_key}</div>'
        f'</div>'
        f'<div style="font-size:0.75rem;color:{MUTED};line-height:1.7;text-align:right">'
        f'{n_picks} spolek &middot; {len(markets)} {rynki} &middot; '
        f'regula v{latest.get("rule_version", "?")}<br>'
        f'nastepny rebalans <span style="color:#E5E7EB;font-weight:600">'
        f'{nxt.strftime("%d.%m.%Y")}</span> (za {days_left} dni)'
        f'</div>'
        f'</div>'
    )


# ====== Sekcja 1: aktualna piatka ======

def render_sklad(latest: dict, markets: tuple, strategy: str) -> None:
    """Karty, wykresy i tabela fundamentalna dla najnowszego snapshotu."""
    for market in markets:
        label = MARKET_LABELS[market]
        picks = latest.get(market) or []
        if not picks:
            continue

        # Data z entry_date pickow, NIE z pola asof — rynki koncza sesje w roznych
        # momentach (GPW zamyka sie wczesniej niz USA), a asof w snapshocie trzyma
        # tylko jedna, wspolna wartosc.
        sesje = sorted({p.get("entry_date", "") for p in picks if p.get("entry_date")})
        dzien = sesje[-1] if sesje else latest.get("asof", "—")
        icon, market_name = label.split(" ", 1)
        section_band(icon, market_name, f"policzone na zamkniecie {dzien}")

        tickers = [p["ticker"] for p in picks]
        prices = download_prices(tickers, period="1y")
        funda = bulk_fetch_universe(tuple(tickers))

        cards, rows = [], []
        for pick in picks:
            ticker = pick["ticker"]
            series = pd.Series(dtype=float)
            if ticker in prices.columns:
                series = prices[ticker].dropna()
            now = float(series.iloc[-1]) if not series.empty else None
            entry = pick["entry_price"]
            ret = (now / entry - 1) if (now is not None and entry) else None
            sector = pick.get("group", "") or "—"
            info = funda.get(ticker, {}) or {}

            cards.append({
                "ticker": ticker,
                "name": pick.get("name", ""),
                "sector": sector,
                "score": pick["score"],
                "entry": entry,
                "now": now,
                "ret": ret,
                "spark": series.tail(SPARK_SESSIONS) if not series.empty else None,
            })
            row = {
                "Ticker": ticker,
                "Nazwa": pick.get("name", ""),
                "Sektor": sector,
                "Score": round(pick["score"], 3),
                f"Wejscie ({CURRENCY[market]})": round(entry, 2),
                "Teraz": round(now, 2) if now is not None else None,
                "Zwrot": ret,
            }
            for column, key in EXTRA_COLUMNS[strategy].items():
                row[column] = info.get(key)
            rows.append(row)

        top_pick_cards(cards, CURRENCY[market])

        chart_col, pie_col = st.columns([3, 2])
        with chart_col:
            st.plotly_chart(
                picks_return_bar([c["ticker"] for c in cards], [c["ret"] for c in cards],
                                 title="Zwrot od rebalansu"),
                width="stretch",
                key=f"bar_{strategy}_{market}",
            )
        with pie_col:
            sector_counts = Counter(c["sector"] for c in cards)
            st.plotly_chart(
                category_pie(dict(sector_counts), title="Sektory w piatce (limit 2)"),
                width="stretch",
                key=f"pie_{strategy}_{market}",
            )

        with st.expander(f"📋 Szczegoly fundamentalne — {market_name}"):
            st.dataframe(
                pd.DataFrame(rows),
                hide_index=True,
                width="stretch",
                key=f"tabela_{strategy}_{market}",
                column_config={
                    "Zwrot": st.column_config.NumberColumn("Zwrot od rebalansu", format="percent"),
                    "ROE": st.column_config.NumberColumn("ROE", format="%.2f"),
                },
            )

    if strategy == "momentum":
        st.info(
            "Kolumny fundamentalne (P/E, Fwd P/E, ROE, dywidenda) sa **kontekstem do samodzielnej "
            "oceny** — nie biora udzialu w wyborze spolek. Regula patrzy wylacznie na momentum, "
            "plynnosc i limit sektorowy."
        )


# ====== Sekcja 2: wyniki live ======

def render_wyniki_live(history: dict, markets: tuple, strategy: str) -> None:
    """Krzywa kapitalu portfela typow vs benchmark rynku."""
    st.markdown("---")
    st.markdown("## Wyniki live")

    if len(history) < 2:
        st.info(
            f"Track record narasta od pierwszego snapshotu ({sorted(history)[0]}). "
            "Krzywa kapitalu pojawi sie po pierwszym rebalansie — wroc za miesiac."
        )
        return

    for market in markets:
        label = MARKET_LABELS[market]
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
        bench_total = None
        if bench_raw is not None and not bench_raw.empty:
            aligned = bench_raw.reindex(equity.index, method="ffill").dropna()
            if not aligned.empty and float(aligned.iloc[0]) != 0:
                bench_curve = (bench_raw.reindex(equity.index, method="ffill")
                               / float(aligned.iloc[0]) * 10000.0)
                curves[bench] = bench_curve
                bench_clean = bench_curve.dropna()
                if not bench_clean.empty:
                    bench_total = float(bench_clean.iloc[-1] / bench_clean.iloc[0] - 1)

        icon, market_name = label.split(" ", 1)
        section_band(icon, market_name, f"benchmark: {bench}")

        total = float(equity.iloc[-1] / equity.iloc[0] - 1)
        cols = st.columns(4)
        kpi_card(cols[0], "Zwrot od startu", fmt_pct(total), f"kapital 10 000 {CURRENCY[market]}",
                 GREEN if total > 0 else RED if total < 0 else "#E5E7EB")
        if bench_total is None:
            kpi_card(cols[1], f"vs {bench}", "—", "brak danych benchmarku")
        else:
            diff = (total - bench_total) * 100
            kpi_card(cols[1], f"vs {bench}",
                     f"{diff:+.1f} p.p.".replace(".", ","),
                     f"{bench}: {fmt_pct(bench_total)}",
                     GREEN if diff > 0 else RED if diff < 0 else "#E5E7EB")
        kpi_card(cols[2], "Rebalansow", str(len(history)), "snapshotow w logu")
        kpi_card(cols[3], "Wartosc portfela",
                 f"{fmt_number(float(equity.iloc[-1]), 0)} {CURRENCY[market]}",
                 f"start 10 000 {CURRENCY[market]}")

        st.plotly_chart(equity_chart(curves, title=f"Top Picks {label} vs {bench}"),
                        width="stretch",
                        key=f"equity_{strategy}_{market}")


# ====== Sekcja 3: symulacja reguly ======

def render_symulacja() -> None:
    """Backtest reguly momentum wstecz — tylko dla strategii cenowej."""
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
            return

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

            icon, market_name = label.split(" ", 1)
            section_band(icon, market_name, "symulacja — survivorship bias")
            cols = st.columns(4)
            kpi_card(cols[0], "CAGR", fmt_pct(stats.get("cagr")), "srednioroczny zwrot")
            kpi_card(cols[1], "Max DD", fmt_pct(stats.get("max_dd")), "najglebszy spadek", RED)
            kpi_card(cols[2], "Sharpe", f"{stats.get('sharpe', 0):.2f}".replace(".", ","),
                     "zwrot / zmiennosc")
            kpi_card(cols[3], "Trafnosc vs benchmark",
                     fmt_pct(stats.get("hit_rate")) if has_bench else "—",
                     "% miesiecy lepszych" if has_bench else "brak benchmarku")
            st.plotly_chart(equity_chart(curves, title=f"Symulacja reguly — {label}"),
                            width="stretch")


# ====== Zakladka jednej strategii ======

def render_strategia(strategy: str) -> None:
    """Cala zakladka jednej strategii."""
    title, opis = STRATEGY_INFO[strategy]
    markets = STRATEGY_MARKETS[strategy]

    st.markdown(f"### {title}")
    st.caption(opis)

    history = load_history(HISTORY_PATHS[strategy])
    if not history:
        st.warning(
            f"Brak pliku `{HISTORY_PATHS[strategy].name}`. Uruchom "
            f"`python scripts/update_top_picks.py --only {strategy}`, "
            "zeby wygenerowac pierwszy snapshot."
        )
        return

    latest_key = sorted(history)[-1]
    latest = history[latest_key]

    versions = {snap.get("rule_version", 0) for snap in history.values()}
    if len(versions) > 1:
        st.warning(
            f"⚠️ Log zawiera snapshoty z roznych wersji reguly ({sorted(versions)}). "
            f"Wyniki sprzed zmiany nie sa porownywalne z obecnymi "
            f"(aktualna: v{RULE_VERSIONS[strategy]})."
        )

    render_naglowek(latest_key, latest, markets)
    render_sklad(latest, markets, strategy)

    if strategy == "earnings":
        st.info(
            "**Tylko S&P 500.** yfinance nie ma historii wynikow kwartalnych dla "
            "ok. 80% spolek z GPW (pomiar na probce 30 spolek, 2026-08-07), wiec "
            "regula nie mialaby z czego wybierac. To samo ograniczenie dotyczy "
            "strony Insider Screener."
        )
    elif strategy == "quality":
        st.info(
            "Dla bankow z GPW komponent zadluzenia jest pomijany — struktura "
            "bilansu banku nie jest porownywalna ze spolka przemyslowa. Wagi "
            "pozostalych trzech skladnikow sa wtedy renormalizowane do 100%."
        )

    render_wyniki_live(history, markets, strategy)

    if strategy == "momentum":
        render_symulacja()
    else:
        st.markdown("---")
        st.info(
            "**Bez symulacji wstecz.** Ta strategia opiera sie na danych "
            "fundamentalnych, ktore yfinance udostepnia wylacznie w wersji "
            "„na dzis\" — nie da sie odtworzyc, jak wygladaly rok temu. "
            "Symulacja liczylaby historyczne miesiace dzisiejszymi danymi "
            "(lookahead bias), wiec swiadomie jej nie ma. Track record narasta "
            "od pierwszego snapshotu."
        )


# ====== Render strony ======

st.markdown("# 🎯 Top Picks — piatka miesiaca")
st.caption(
    "Trzy niezalezne reguly wybieraja po piatce spolek pierwszego dnia miesiaca. "
    "Kazda patrzy na co innego: cenowe momentum, jakosc wynikow kwartalnych albo "
    "jakosc biznesu. Sklad nie jest recznie korygowany."
)

tab_mom, tab_earn, tab_qual = st.tabs([
    "📈 Momentum", "📊 Earnings Momentum", "🏛️ Jakosc biznesu",
])
with tab_mom:
    render_strategia("momentum")
with tab_earn:
    render_strategia("earnings")
with tab_qual:
    render_strategia("quality")

render_footer()
