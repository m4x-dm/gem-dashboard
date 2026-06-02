"""Strona 9: Amerykanskie Akcje S&P 500 — 11 sektorow GICS."""

import streamlit as st
import pandas as pd
import numpy as np
from components.sidebar import setup_sidebar, get_risk_free, render_footer
from data.sp500_universe import (
    ALL_SP500_TICKERS, SP500_NAMES, SP500_SECTOR_MAP, SP500_SECTORS,
)
from data.downloader import download_prices, download_single
from data.momentum import (
    latest_returns, build_ranking, backtest_rotation, calc_stats,
    correlation_matrix, relative_strength,
)
from components.formatting import (
    fmt_pct, fmt_number, color_for_value,
    GOLD, GREEN, RED, MUTED, BG_CARD, BORDER,
)
from components.charts import (
    price_chart, momentum_chart, drawdown_chart,
    ranking_bar_chart, correlation_heatmap, equity_chart, rs_chart,
)
from components.cards import (
    stats_table, comparison_card, final_value_card,
    ratios_card, forward_consensus_card, earnings_history_card, analyst_recos_card,
)
from data.financials import (
    get_ratios_snapshot, get_forward_consensus,
    get_earnings_history, get_analyst_recos,
)
from components.financials_ui import (
    render_sprawozdania_screener,
    render_sprawozdania_deep_dive,
)
from components.auth import require_premium

st.set_page_config(page_title="S&P 500 — Amerykanskie Akcje", page_icon="🇺🇸", layout="wide")
setup_sidebar()
if not require_premium(7): st.stop()

st.markdown("# 🇺🇸 Amerykanskie Akcje S&P 500")

# ---------------------------------------------------------------------------
# Wspolne: wybor sektora
# ---------------------------------------------------------------------------
SECTOR_OPTIONS = ["Wszystkie"] + list(SP500_SECTORS.keys())


def _tickers_for_sector(sector_name: str) -> list[str]:
    """Zwraca liste tickerow dla wybranego sektora."""
    if sector_name == "Wszystkie":
        return ALL_SP500_TICKERS
    return list(SP500_SECTORS.get(sector_name, {}).keys())


# ===========================================================================
# Screener fundamentalny — helpers (page-local, uzywane przez tab Screening)
# Definicje MUSZA byc PRZED `with tab6:` — Streamlit @st.fragment wykonuje
# fragment przy linii `_screener_fragment()`, ktora woła te helpery.
# ===========================================================================

def _apply_screener_filters(
    df: pd.DataFrame,
    *,
    pe_max: float,
    roe_min_pct: float,
    ev_ebitda_max: float,
    sectors: list[str],
    cap_min_usd: float,
    buy_only: bool,
    div_yld_min_pct: float,
    rev_growth_min_pct: float,
    debt_eq_max: float,
    profit_margin_min_pct: float,
    pb_max: float,
) -> pd.DataFrame:
    """Aplikuje 11 filtrow (6 main + 5 advanced). NaN-aware:
    spolki z brakujacym wskaznikiem sa WYKLUCZONE gdy filtr aktywny.
    """
    out = df.copy()
    # 6 main
    out = out[out["pe"].fillna(np.inf) <= pe_max]
    out = out[out["roe"].fillna(-np.inf) >= roe_min_pct / 100.0]
    out = out[out["ev_ebitda"].fillna(np.inf) <= ev_ebitda_max]
    if sectors:
        out = out[out["sector"].isin(sectors)]
    out = out[out["market_cap"].fillna(0) >= cap_min_usd]
    if buy_only:
        out = out[out["is_buy"]]
    # 5 advanced
    out = out[out["dividend_yield"].fillna(-np.inf) >= div_yld_min_pct]
    out = out[out["revenue_growth"].fillna(-np.inf) >= rev_growth_min_pct / 100.0]
    out = out[out["debt_to_equity"].fillna(np.inf) <= debt_eq_max]
    out = out[out["profit_margin"].fillna(-np.inf) >= profit_margin_min_pct / 100.0]
    out = out[out["price_to_book"].fillna(np.inf) <= pb_max]
    return out


def _format_screener_df(df: pd.DataFrame, currency_sym: str = "$") -> pd.DataFrame:
    """Format kolumn na display strings. Zachowuje ticker jako index."""
    from data.financials import format_large_number
    out = df.copy()
    out["P/E"] = out["pe"].apply(lambda v: f"{v:.1f}" if pd.notna(v) else "—")
    out["Fwd P/E"] = out["fwd_pe"].apply(lambda v: f"{v:.1f}" if pd.notna(v) else "—")
    out["EV/EBITDA"] = out["ev_ebitda"].apply(lambda v: f"{v:.1f}" if pd.notna(v) else "—")
    out["ROE"] = out["roe"].apply(lambda v: f"{v*100:.0f}%" if pd.notna(v) else "—")
    out["Marza"] = out["profit_margin"].apply(lambda v: f"{v*100:.1f}%" if pd.notna(v) else "—")
    out["Div Yld"] = out["dividend_yield"].apply(lambda v: f"{v:.2f}%" if pd.notna(v) else "—")
    out["Cap"] = out["market_cap"].apply(lambda v: f"{currency_sym}{format_large_number(v)}" if pd.notna(v) else "—")
    out["Rev Gr."] = out["revenue_growth"].apply(lambda v: f"{v*100:+.1f}%" if pd.notna(v) else "—")
    out["Reco"] = out["recommendation_key"].fillna("").astype(str).str.upper().str.replace("_", " ")
    out["Nazwa"] = out["name"]
    out["Sektor"] = out["sector"].fillna("—")
    return out[["Nazwa", "Sektor", "P/E", "Fwd P/E", "EV/EBITDA", "ROE", "Marza",
                "Div Yld", "Rev Gr.", "Cap", "Reco"]]


def _render_screener_summary(df: pd.DataFrame, total: int) -> None:
    """4 summary cards: liczba, median P/E, median ROE, top sektor."""
    n = len(df)
    pe_med = df["pe"].median() if "pe" in df.columns and n > 0 else None
    roe_med = df["roe"].median() if "roe" in df.columns and n > 0 else None
    top_sec = df["sector"].value_counts().head(1) if "sector" in df.columns else pd.Series(dtype=int)

    c1, c2, c3, c4 = st.columns(4)
    c1.html(
        f'<div style="background:{BG_CARD};border:1px solid {GOLD}40;border-radius:8px;padding:10px;text-align:center">'
        f'<div style="color:{GOLD};font-size:10px;text-transform:uppercase">Spolek</div>'
        f'<div style="color:#fff;font-size:18px;font-weight:700">{n} / {total}</div></div>'
    )
    pe_text = f"{pe_med:.1f}" if pe_med is not None and pd.notna(pe_med) else "—"
    c2.html(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:10px;text-align:center">'
        f'<div style="color:{MUTED};font-size:10px;text-transform:uppercase">Med. P/E</div>'
        f'<div style="color:#fff;font-size:18px;font-weight:700">{pe_text}</div></div>'
    )
    roe_text = f"{roe_med*100:.0f}%" if roe_med is not None and pd.notna(roe_med) else "—"
    c3.html(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:10px;text-align:center">'
        f'<div style="color:{MUTED};font-size:10px;text-transform:uppercase">Med. ROE</div>'
        f'<div style="color:#71C77E;font-size:18px;font-weight:700">{roe_text}</div></div>'
    )
    if not top_sec.empty:
        sec_name = top_sec.index[0]
        sec_count = int(top_sec.iloc[0])
        c4.html(
            f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:10px;text-align:center">'
            f'<div style="color:{MUTED};font-size:10px;text-transform:uppercase">Top sektor</div>'
            f'<div style="color:#fff;font-size:12px;font-weight:700;line-height:1.3">{sec_name}<br>'
            f'<span style="font-size:10px;color:{MUTED}">({sec_count} spolek)</span></div></div>'
        )
    else:
        c4.html(
            f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:10px;text-align:center">'
            f'<div style="color:{MUTED};font-size:10px;text-transform:uppercase">Top sektor</div>'
            f'<div style="color:#fff;font-size:18px;font-weight:700">—</div></div>'
        )


# ---------------------------------------------------------------------------
# TABY
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 Ranking momentum",
    "📉 Wykresy",
    "⚖️ Porownanie",
    "🧪 Backtest momentum",
    "💪 Relative Strength",
    "📊 Screening",
    "💰 Finanse",
    "📈 Sprawozdania Q",
])

# ========================== TAB 1: RANKING ==========================
with tab1:
    @st.fragment
    def _ranking_fragment():
        st.markdown("### Ranking momentum — S&P 500")

        col1, col2 = st.columns(2)
        with col1:
            sector_filter = st.selectbox("Sektor", SECTOR_OPTIONS, key="sp_rank_sec")
        with col2:
            mom_filter = st.selectbox("Momentum absolutny", ["Wszystkie", "TAK", "NIE"], key="sp_rank_mom")

        tickers = _tickers_for_sector(sector_filter)
        _tab1_ok = bool(tickers)
        if not _tab1_ok:
            st.warning("Brak tickerow dla wybranego sektora.")
        else:
            with st.spinner("Pobieram dane S&P 500..."):
                prices = download_prices(tickers, period="2y")

            if prices.empty:
                st.error("Nie udalo sie pobrac danych.")
                _tab1_ok = False

        if _tab1_ok:
            rf = get_risk_free()
            ranking = build_ranking(prices, rf)

            # Zapisz top ticker dla pre-fill selectbox w tabie "Finanse".
            if len(ranking) > 0:
                st.session_state["sp_finanse_default"] = str(ranking.index[0])

            # Dodaj nazwy i sektor
            ranking["Nazwa"] = ranking.index.map(lambda t: SP500_NAMES.get(t, t))
            ranking["Sektor"] = ranking.index.map(lambda t: SP500_SECTOR_MAP.get(t, "—"))

            # Filtr
            filtered = ranking.copy()
            if sector_filter != "Wszystkie":
                filtered = filtered[filtered["Sektor"] == sector_filter]
            if mom_filter != "Wszystkie":
                filtered = filtered[filtered["Momentum_abs"] == mom_filter]

            st.markdown(f"**{len(filtered)}** spolek | Stopa wolna: **{rf:.2f}%**")

            display_df = filtered[["Nazwa", "Sektor", "1M", "3M", "6M", "12M", "Wynik", "Momentum_abs"]].copy()
            display_df.index.name = "Ticker"
            for col in ["1M", "3M", "6M", "12M", "Wynik"]:
                display_df[col] = display_df[col].apply(lambda x: fmt_pct(x) if pd.notna(x) else "—")
            display_df = display_df.rename(columns={"Momentum_abs": "Mom. abs."})

            st.dataframe(display_df, use_container_width=True, height=min(700, 40 + len(display_df) * 35))

            # Eksport CSV
            csv = filtered[["Nazwa", "Sektor", "1M", "3M", "6M", "12M", "Wynik", "Momentum_abs"]].copy()
            csv.index.name = "Ticker"
            st.download_button("📥 Eksportuj CSV", csv.to_csv(), "sp500_ranking.csv", "text/csv")

            st.divider()

            # Wykres slupkowy top 15
            valid = filtered.dropna(subset=["Wynik"])
            if not valid.empty:
                fig = ranking_bar_chart(valid, top_n=min(15, len(valid)), title="Top 15 — wynik momentum S&P 500")
                st.plotly_chart(fig, use_container_width=True)

    _ranking_fragment()

# ========================== TAB 2: WYKRESY ==========================
with tab2:
    st.markdown("### Wykresy — S&P 500")

    options_map = {t: f"{t} — {SP500_NAMES.get(t, t)}" for t in ALL_SP500_TICKERS}

    selected_charts = st.multiselect(
        "Wybierz spolki (maks. 5)",
        options=list(options_map.keys()),
        default=["AAPL", "MSFT", "NVDA"],
        format_func=lambda x: options_map[x],
        max_selections=5,
        key="sp_chart_sel",
    )

    period_map = {
        "Strategia 12-1": "2y",
        "1 miesiac": "1mo", "3 miesiace": "3mo", "6 miesiecy": "6mo",
        "1 rok": "1y", "2 lata": "2y", "5 lat": "5y", "10 lat": "10y", "Maksymalny": "max",
    }
    period_label = st.selectbox("Okres", list(period_map.keys()), index=5, key="sp_chart_period")
    period = period_map[period_label]
    is_strategy_view = period_label == "Strategia 12-1"

    if not selected_charts:
        st.info("Wybierz co najmniej 1 spolke.")
    else:
        with st.spinner("Pobieram dane..."):
            chart_prices = pd.DataFrame()
            for t in selected_charts:
                s = download_single(t, period=period)
                if s is not None:
                    chart_prices[t] = s
            chart_prices = chart_prices.dropna(how="all")

        if is_strategy_view and len(chart_prices) > 273:
            chart_prices = chart_prices.iloc[-273:-21]
        elif is_strategy_view:
            st.warning("Za malo danych dla widoku Strategia 12-1.")

        if chart_prices.empty:
            st.error("Nie udalo sie pobrac danych.")
        else:
            sub1, sub2, sub3 = st.tabs(["📈 Cena", "🚀 Momentum", "📉 Drawdown"])

            with sub1:
                normalize = st.checkbox("Normalizuj (baza = 100)", value=True, key="sp_norm")
                title = "Cena znormalizowana (baza = 100)" if normalize else "Cena (USD)"
                fig = price_chart(chart_prices, title=title, normalize=normalize)
                st.plotly_chart(fig, use_container_width=True)

            with sub2:
                window = st.slider("Okno momentum (dni)", 21, 504, 252, step=21, key="sp_mom_win")
                fig = momentum_chart(chart_prices, window=window, title=f"Momentum {window}D (rolling)")
                st.plotly_chart(fig, use_container_width=True)

            with sub3:
                fig = drawdown_chart(chart_prices)
                st.plotly_chart(fig, use_container_width=True)

# ========================== TAB 3: POROWNANIE ==========================
with tab3:
    st.markdown("### Porownanie spolek S&P 500")

    options_cmp = {t: f"{t} — {SP500_NAMES.get(t, t)}" for t in ALL_SP500_TICKERS}

    col_sel, col_period = st.columns([3, 1])
    with col_sel:
        selected_cmp = st.multiselect(
            "Wybierz 2-4 spolki do porownania",
            options=list(options_cmp.keys()),
            default=["AAPL", "MSFT"],
            format_func=lambda x: options_cmp[x],
            max_selections=4,
            key="sp_cmp_sel",
        )
    with col_period:
        cmp_period_map = {
            "Strategia 12-1": "2y",
            "1 miesiac": "1mo",
            "3 miesiace": "3mo",
            "6 miesiecy": "6mo",
            "1 rok": "1y",
            "2 lata": "2y",
            "5 lat": "5y",
            "10 lat": "10y",
            "Maksymalny": "max",
        }
        cmp_period_label = st.selectbox("Okres", list(cmp_period_map.keys()), index=0, key="sp_cmp_period")
        cmp_period = cmp_period_map[cmp_period_label]
        cmp_is_strategy = cmp_period_label == "Strategia 12-1"

    if len(selected_cmp) < 2:
        st.info("Wybierz co najmniej 2 spolki.")
    else:
        with st.spinner("Pobieram dane..."):
            cmp_prices = pd.DataFrame()
            for t in selected_cmp:
                s = download_single(t, period=cmp_period)
                if s is not None:
                    cmp_prices[t] = s
            cmp_prices = cmp_prices.dropna(how="all")

        if cmp_is_strategy and len(cmp_prices) > 273:
            cmp_prices = cmp_prices.iloc[-273:-21]
        elif cmp_is_strategy:
            st.warning("Za malo danych dla widoku Strategia 12-1. Wyswietlam dostepne dane.")

        if cmp_prices.empty:
            st.error("Brak danych.")
        else:
            # Karty ze stopami zwrotu
            st.markdown("#### Stopy zwrotu")
            rets = latest_returns(cmp_prices)

            cols = st.columns(len(selected_cmp))
            for i, ticker in enumerate(selected_cmp):
                with cols[i]:
                    r = rets.loc[ticker] if ticker in rets.index else pd.Series()
                    comparison_card(
                        ticker, SP500_NAMES.get(ticker, ticker),
                        SP500_SECTOR_MAP.get(ticker, ""), r, i,
                    )

            st.divider()

            # Overlay cenowy
            st.markdown("#### Cena znormalizowana (baza = 100)")
            fig = price_chart(cmp_prices, title=f"Porownanie cenowe — {cmp_period_label}")
            st.plotly_chart(fig, use_container_width=True)

            st.divider()

            # Statystyki
            st.markdown("#### Statystyki")
            rf = get_risk_free()
            rf_decimal = rf / 100.0
            cmp_stats = {}
            for t in selected_cmp:
                if t in cmp_prices.columns:
                    cmp_stats[t] = calc_stats(cmp_prices[t].dropna(), 252, rf_decimal)
            if cmp_stats:
                stats_table(cmp_stats)

            st.divider()

            # Macierz korelacji
            st.markdown("#### Macierz korelacji (252 dni)")
            corr = correlation_matrix(cmp_prices, period=252)
            fig = correlation_heatmap(corr)
            st.plotly_chart(fig, use_container_width=True)

# ========================== TAB 4: BACKTEST ==========================
with tab4:
    @st.fragment
    def _backtest_fragment():
        st.markdown("### Backtest rotacji momentum — S&P 500")
        st.caption("Co miesiac kupuj top N spolek wg wyniku kompozytowego. Porownanie z equal-weight B&H i SPY B&H.")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            bt_sector = st.selectbox("Sektor", SECTOR_OPTIONS, key="sp_bt_sec")
        with col2:
            top_n = st.selectbox("Top N spolek", [1, 3, 5, 10], index=1, key="sp_bt_topn")
        with col3:
            bt_period_map = {"2 lata": "2y", "5 lat": "5y", "10 lat": "10y", "Maksymalny": "max"}
            bt_period_label = st.selectbox("Okres", list(bt_period_map.keys()), index=1, key="sp_bt_period")
            bt_period = bt_period_map[bt_period_label]
        with col4:
            start_capital = st.number_input("Kapital (USD)", value=10000, step=1000, min_value=100, key="sp_bt_cap")

        with st.expander("⚙️ Metoda scoringu + koszty", expanded=False):
            rank_based = st.checkbox(
                "Rank-based score (percentyle + anty-1M)",
                value=False,
                key="sp_bt_rank",
                help="Zamiast wazonej sumy surowych zwrotow, rankuje tickery per okres "
                     "(0-1). 1M flipowany jako anti-signal (short-term reversal). "
                     "Odporny na outliery i skew miedzy aktywami.",
            )
            costs_on_sp = st.checkbox(
                "Koszty i podatki (realistycznie)",
                value=False,
                key="sp_bt_costs",
                help="Koszt transakcji skalowany turnoverem (frakcja tickerow wymienionych "
                     "przy rebalansie) + Belka 19% od zyskownych segmentow.",
            )
            col_sp_tc, col_sp_belka = st.columns(2)
            with col_sp_tc:
                tc_sp_pct = st.slider(
                    "Koszt roundtrip (%)", 0.0, 0.5, 0.1, 0.01,
                    disabled=not costs_on_sp,
                    key="sp_bt_tc",
                    help="US akcje: IBKR ~0.02-0.05%, ale + spread ~0.05-0.1% dla mid-capow. Default 0.1%.",
                ) / 100.0
            with col_sp_belka:
                belka_on_sp = st.checkbox(
                    "Belka 19%",
                    value=False,
                    disabled=not costs_on_sp,
                    key="sp_bt_belka",
                    help="Rozliczany od frakcji portfela faktycznie rotowanej w rebalansie.",
                )
            tc_sp = tc_sp_pct if costs_on_sp else 0.0
            tax_sp = 0.19 if (costs_on_sp and belka_on_sp) else 0.0
            regime_on_sp = st.checkbox(
                "Filtr breadth (regime)",
                value=False,
                key="sp_bt_regime",
                help="Gdy mniej niz X% spolek w universum jest powyzej SMA200 → "
                     "strategia przechodzi do cash (pomija rebalans). Chroni przed bessa. "
                     "Default 40% = Faber-style breadth filter.",
            )
            breadth_sp_pct = st.slider(
                "Prog breadth (% > SMA200)", 20, 70, 40, 5,
                disabled=not regime_on_sp,
                key="sp_bt_breadth",
            ) / 100.0
            breadth_sp = breadth_sp_pct if regime_on_sp else None

        bt_tickers = _tickers_for_sector(bt_sector)
        _tab4_ok = len(bt_tickers) >= top_n
        if not _tab4_ok:
            st.warning(f"Za malo spolek ({len(bt_tickers)}) dla top {top_n}.")
        else:
            # Dodaj SPY do pobrania jesli go nie ma
            dl_tickers = list(set(bt_tickers + ["SPY"]))

            with st.spinner("Pobieram dane i licze backtest..."):
                bt_prices = download_prices(dl_tickers, period=bt_period)

            if bt_prices.empty or len(bt_prices) < 273:
                st.error("Za malo danych do backtestu. Sprobuj dluzszy okres.")
                _tab4_ok = False

        if _tab4_ok:
            # Kolumny do momentum rotation (bez SPY — benchmark osobno)
            mom_cols = [c for c in bt_prices.columns if c in bt_tickers]

            # Benchmarki
            bm = {"Equal-Weight B&H": mom_cols}
            if "SPY" in bt_prices.columns and bt_prices["SPY"].dropna().shape[0] > 273:
                bm["SPY B&H"] = "SPY"

            result = backtest_rotation(
                bt_prices[mom_cols].dropna(how="all"), top_n=top_n,
                start_capital=start_capital, trading_days=252,
                benchmarks=bm,
                rank_based=rank_based,
                transaction_cost=tc_sp, tax_belka=tax_sp,
                breadth_threshold=breadth_sp,
            )

            if result is None:
                st.error("Za malo danych do backtestu.")
            else:
                # Dodaj SPY benchmark jesli jest
                if "SPY B&H" in bm and "SPY" in bt_prices.columns:
                    spy_prices = bt_prices["SPY"].dropna()
                    mom_eq = result["equity_curves"][f"Momentum Top {top_n}"]
                    spy_slice = spy_prices.loc[spy_prices.index.isin(mom_eq.index)]
                    if len(spy_slice) > 0:
                        result["equity_curves"]["SPY B&H"] = start_capital * spy_slice / spy_slice.iloc[0]
                        rf = get_risk_free()
                        result["stats"]["SPY B&H"] = calc_stats(result["equity_curves"]["SPY B&H"], 252, rf / 100.0)

                # Krzywa kapitalu
                st.markdown("#### Krzywa kapitalu")
                fig = equity_chart(result["equity_curves"])
                st.plotly_chart(fig, use_container_width=True)

                # Statystyki — przelicz z rf
                rf = get_risk_free()
                rf_decimal = rf / 100.0
                bt_stats = {}
                for name, eq in result["equity_curves"].items():
                    bt_stats[name] = calc_stats(eq, 252, rf_decimal)

                st.markdown("#### Statystyki")
                stats_table(bt_stats)

                # Wartosci koncowe
                st.divider()
                strategies = list(result["equity_curves"].items())
                final_cols = st.columns(len(strategies))
                for i, (name, eq) in enumerate(strategies):
                    with final_cols[i]:
                        final_value_card(name, eq.iloc[-1], start_capital, "USD")

    _backtest_fragment()

# ========================== TAB 5: RELATIVE STRENGTH ==========================
with tab5:
    st.markdown("### Relative Strength vs SPY")
    st.caption("RS > 100 = spolka outperformuje benchmark (SPY)")

    rs_options = {t: f"{t} — {SP500_NAMES.get(t, t)}" for t in ALL_SP500_TICKERS}
    rs_selected = st.multiselect(
        "Wybierz spolki (maks. 5)",
        options=list(rs_options.keys()),
        default=["AAPL", "NVDA", "MSFT"],
        format_func=lambda x: rs_options[x],
        max_selections=5,
        key="sp_rs_sel",
    )

    rs_period_map = {
        "1 rok": "1y", "2 lata": "2y", "5 lat": "5y", "Maksymalny": "max",
    }
    rs_period_label = st.selectbox("Okres", list(rs_period_map.keys()), index=1, key="sp_rs_period")
    rs_period = rs_period_map[rs_period_label]

    if rs_selected:
        with st.spinner("Pobieram dane..."):
            rs_prices = pd.DataFrame()
            for t in list(set(rs_selected + ["SPY"])):
                s = download_single(t, period=rs_period)
                if s is not None:
                    rs_prices[t] = s

        if "SPY" in rs_prices.columns:
            for t in rs_selected:
                if t in rs_prices.columns and t != "SPY":
                    rs_data = relative_strength(rs_prices[t].dropna(), rs_prices["SPY"].dropna())
                    if not rs_data.empty:
                        fig = rs_chart(rs_data, t, "SPY")
                        st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nie udalo sie pobrac danych SPY.")
    else:
        st.info("Wybierz co najmniej 1 spolke.")

# ========================== TAB 6: SCREENING ==========================
with tab6:
    @st.fragment
    def _screener_fragment():
        from data.financials import bulk_fetch_universe, to_screener_df
        from data.sp500_universe import SP500_TOP100

        st.markdown("### Screening fundamentalny — top 100 S&P 500")
        st.caption(
            "Pelna tabela 11 wskaznikow (P/E, ROE, EV/EBITDA, marze, FCF, "
            "div yield, target). Filtruj + sortuj wg kryteriow. "
            "Dane z yfinance, cache 24h."
        )

        # Bulk fetch (cached) — pierwsze ladowanie tabu 30-60s
        with st.spinner("Pobieram dane fundamentalne universe..."):
            bulk = bulk_fetch_universe(tuple(SP500_TOP100))
        df_full = to_screener_df(bulk)
        if df_full.empty:
            st.error("Nie udalo sie pobrac danych z yfinance. Sprobuj odswiezyc strone.")
            return

        if len(bulk) < len(SP500_TOP100) * 0.7:
            st.warning(
                f"⚠️ Pobrano dane dla {len(bulk)}/{len(SP500_TOP100)} spolek. "
                f"Yahoo Finance moze byc throttled. Sprobuj odswiezyc za chwile."
            )

        # 1. Filtry glowne (6 w 3-col × 2-row)
        st.markdown("**Filtry glowne**")
        col1, col2, col3 = st.columns(3)
        pe_max = col1.slider("P/E max", 5.0, 100.0, 25.0, step=1.0, key="sp_scr_pe")
        roe_min = col2.slider("ROE min (%)", 0, 50, 15, key="sp_scr_roe")
        ev_ebitda_max = col3.slider("EV/EBITDA max", 1.0, 60.0, 20.0, step=1.0, key="sp_scr_ev")

        col4, col5, col6 = st.columns(3)
        available_sectors = sorted([s for s in df_full["sector"].dropna().unique() if s])
        sectors_sel = col4.multiselect("Sektory", available_sectors, default=available_sectors, key="sp_scr_sec")
        cap_min_b = col5.number_input("Market cap min ($B)", 0.0, 5000.0, 10.0, step=5.0, key="sp_scr_cap")
        buy_only = col6.checkbox("Tylko BUY", value=False, key="sp_scr_buy",
                                  help="Tylko spolki z rekomendacja BUY/STRONG_BUY/OUTPERFORM")

        # 2. Expander zaawansowane (5 filtrow)
        with st.expander("Zaawansowane filtry", expanded=False):
            a1, a2, a3 = st.columns(3)
            div_yld_min = a1.slider("Div Yield min (%)", 0.0, 15.0, 0.0, key="sp_scr_div")
            rev_growth_min = a2.slider("Revenue Growth min (%)", -20, 100, -20, key="sp_scr_rev")
            debt_eq_max = a3.slider("Debt/E max", 0, 500, 500, key="sp_scr_de")
            a4, a5 = st.columns(2)
            profit_margin_min = a4.slider("Profit Margin min (%)", -20, 50, -20, key="sp_scr_pm")
            pb_max = a5.slider("P/B max", 0.0, 30.0, 30.0, step=0.5, key="sp_scr_pb")

        # 3. Aplikuj filtry
        df_filtered = _apply_screener_filters(
            df_full,
            pe_max=pe_max, roe_min_pct=roe_min, ev_ebitda_max=ev_ebitda_max,
            sectors=sectors_sel, cap_min_usd=cap_min_b * 1e9, buy_only=buy_only,
            div_yld_min_pct=div_yld_min, rev_growth_min_pct=rev_growth_min,
            debt_eq_max=debt_eq_max, profit_margin_min_pct=profit_margin_min, pb_max=pb_max,
        )

        if df_filtered.empty:
            st.info("Brak wynikow po zastosowaniu filtrow. Sprobuj rozluznic kryteria.")
            return

        # 4. Sort + Top N
        sort_options = {
            "ROE (desc)": ("roe", False),
            "P/E (asc, tansze)": ("pe", True),
            "Forward P/E (asc)": ("fwd_pe", True),
            "EV/EBITDA (asc)": ("ev_ebitda", True),
            "Profit Margin (desc)": ("profit_margin", False),
            "Revenue Growth (desc)": ("revenue_growth", False),
            "Dividend Yield (desc)": ("dividend_yield", False),
            "Upside % (desc)": ("upside_pct", False),
            "Market Cap (desc)": ("market_cap", False),
        }
        s1, s2, s3 = st.columns([2, 1, 1])
        sort_label = s1.selectbox("Sortuj wg", list(sort_options.keys()), key="sp_scr_sort")
        sort_col, ascending = sort_options[sort_label]
        top_n_label = s2.selectbox("Top N", ["5", "10", "15", "25", "Wszystkie"], index=2, key="sp_scr_topn")
        s3.markdown(f"**Wynikow:** {len(df_filtered)}/{len(df_full)}")

        df_sorted = df_filtered.sort_values(sort_col, ascending=ascending, na_position="last")
        if top_n_label != "Wszystkie":
            df_sorted = df_sorted.head(int(top_n_label))

        # 5. Summary cards
        _render_screener_summary(df_sorted, total=len(df_full))
        st.markdown("---")

        # 6. Tabela
        df_display = _format_screener_df(df_sorted, currency_sym="$")
        sel = st.dataframe(
            df_display, height=500, use_container_width=True,
            on_select="rerun", selection_mode="single-row",
        )
        if sel and hasattr(sel, "selection") and sel.selection.rows:
            clicked = df_display.index[sel.selection.rows[0]]
            st.session_state["sp_finanse_ticker"] = clicked
            st.info(f"✓ Wybrano **{clicked}** — przelacz na tab 💰 Finanse aby zobaczyc szczegoly")

        # 7. CSV export
        export_df = df_sorted.copy()
        export_df.index.name = "ticker"
        csv = export_df.to_csv()
        st.download_button("📥 Eksport CSV", csv, "sp500_screener.csv", "text/csv", key="sp_scr_csv")

        st.caption(
            "💡 Spolki z brakujacym wskaznikiem sa odfiltrowane gdy filtr aktywny "
            "(np. spolka bez P/E nie pojawi sie gdy P/E max < 100)."
        )

    _screener_fragment()


# ========================== TAB 7: FINANSE ==========================
with tab7:
    @st.fragment
    def _finanse_fragment():
        st.markdown("### Wskazniki finansowe + konsensus analitykow")
        st.caption(
            "Dane z yfinance (Ticker.info / .earnings_estimate / .earnings_history). "
            "Cache 24h. Niektore wskazniki moga byc niedostepne dla mniejszych spolek."
        )

        # Pre-fill z top rankingu (jesli user wczesniej otworzyl tab Ranking) lub fallback.
        # WAZNE: NIE uzywaj index= z key= jednoczesnie (powoduje cofanie do default
        # przy re-run fragmentu). Init w session_state TYLKO przy pierwszym renderze.
        ticker_options = sorted(SP500_NAMES.keys())
        if "sp_finanse_ticker" not in st.session_state:
            default_ticker = st.session_state.get("sp_finanse_default") or ticker_options[0]
            if default_ticker in ticker_options:
                st.session_state["sp_finanse_ticker"] = default_ticker

        ticker = st.selectbox(
            "Spolka",
            ticker_options,
            format_func=lambda t: f"{t} — {SP500_NAMES.get(t, t)}",
            key="sp_finanse_ticker",
        )
        st.caption(f"Wskazniki dla: **{ticker}** — {SP500_NAMES.get(ticker, '')}")

        with st.spinner(f"Pobieram dane finansowe dla {ticker}..."):
            snap = get_ratios_snapshot(ticker)
            cons = get_forward_consensus(ticker)
            hist = get_earnings_history(ticker)
            recos = get_analyst_recos(ticker)

        col1, col2 = st.columns(2)
        with col1:
            ratios_card(snap, is_bank=False)
        with col2:
            forward_consensus_card(cons)

        col3, col4 = st.columns(2)
        with col3:
            earnings_history_card(hist)
        with col4:
            analyst_recos_card(recos)

    _finanse_fragment()


# ========================== TAB 8: SPRAWOZDANIA Q ==========================
with tab8:
    @st.fragment
    def _sprawozdania_fragment():
        st.markdown("### 📈 Sprawozdania finansowe — kwartalne + beat/miss vs consensus")

        # Pending view request — consume z session_state (pop = read+delete)
        # Streamlit zabrania settowania session_state widget keys; uzywamy
        # osobnej zmiennej i `index=` parametru.
        pending = st.session_state.pop("sp500_pending_view", None)
        default_index = 1 if pending == "deep_dive" else 0

        view = st.radio(
            "Widok",
            options=["🔍 Screener", "🏢 Deep dive"],
            horizontal=True,
            index=default_index,
            key="sp500_sprawozdania_view_radio",
        )

        universe = ALL_SP500_TICKERS

        if view == "🔍 Screener":
            selected = render_sprawozdania_screener(universe, market="SP500")
            if selected:
                # Zapisz wybor + pending request na deep dive view, rerun
                st.session_state["sp500_deep_dive_ticker"] = selected
                st.session_state["sp500_pending_view"] = "deep_dive"
                st.rerun()
        else:
            ticker = st.session_state.get("sp500_deep_dive_ticker", "")
            if not ticker:
                ticker = st.selectbox(
                    "Ticker",
                    options=[""] + universe,
                    key="sp500_deep_dive_manual",
                )
            render_sprawozdania_deep_dive(ticker, market="SP500")

    _sprawozdania_fragment()


render_footer()
