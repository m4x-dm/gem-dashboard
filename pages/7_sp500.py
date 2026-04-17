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
from components.cards import stats_table, comparison_card, final_value_card
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


# ---------------------------------------------------------------------------
# TABY
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Ranking momentum",
    "📉 Wykresy",
    "⚖️ Porownanie",
    "🧪 Backtest momentum",
    "💪 Relative Strength",
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

        with st.expander("⚙️ Metoda scoringu", expanded=False):
            rank_based = st.checkbox(
                "Rank-based score (percentyle + anty-1M)",
                value=False,
                key="sp_bt_rank",
                help="Zamiast wazonej sumy surowych zwrotow, rankuje tickery per okres "
                     "(0-1). 1M flipowany jako anti-signal (short-term reversal). "
                     "Odporny na outliery i skew miedzy aktywami.",
            )

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

render_footer()
