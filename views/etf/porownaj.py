"""Porownaj — wykresy, head-to-head z korelacjami i side-by-side.

Scalone 2026-11-15 z pages/3_wykresy.py, 4_porownanie.py, 21_side_by_side.py.
Kazda zakladka ma wlasne kontrolki (klucze widgetow z prefiksem wyk_/h2h_/sbs_).
"""
import streamlit as st
import pandas as pd
from components.sidebar import get_risk_free, render_footer
from data.etf_universe import ALL_TICKERS, ETF_NAMES, ETF_CATEGORY_MAP
from data.sp500_universe import ALL_SP500_TICKERS, SP500_NAMES, SP500_SECTOR_MAP
from data.gpw_universe import ALL_GPW_TICKERS, GPW_NAMES, GPW_CATEGORY_MAP
from data.crypto_universe import CRYPTO_BY_MCAP, CRYPTO_NAMES, CRYPTO_CATEGORY_MAP
from data.downloader import (benchmark_status, download_single, download_stooq,
                             STOOQ_TICKERS)
from data.momentum import (latest_returns, correlation_matrix, calc_stats,
                           relative_strength)
from components.charts import (price_chart, momentum_chart, drawdown_chart,
                               correlation_heatmap, rs_chart)
from components.cards import comparison_card, stats_table
from components.i18n import tr
from components.h2h_compare import render_h2h


def render_charts_tab() -> None:
    """Tresc dawnej 3_wykresy.py."""
    st.caption(tr("Wykresy — cena, momentum i drawdown wybranych ETF-ow"))
    # Wybor ETF-ow
    available = ALL_TICKERS + st.session_state.get("custom_tickers", [])
    options = {t: f"{t} — {ETF_NAMES.get(t, t)}" for t in available}

    selected = st.multiselect(
        tr("Wybierz ETF-y (maks. 5)"),
        options=list(options.keys()),
        default=["QQQ", "VEA", "AGG"],
        format_func=lambda x: options[x],
        max_selections=5,
        key="wyk_sel",
    )

    # Okres
    period_map = {
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
    period_label = st.selectbox(tr("Okres"), list(period_map.keys()), index=4, key="wyk_period", format_func=tr)
    period = period_map[period_label]
    is_strategy_view = period_label == "Strategia 12-1"

    _ok = True
    if not selected:
        st.info(tr("Wybierz co najmniej 1 ETF."))
        _ok = False

    if _ok:
        # Pobierz dane — download_single per ticker (pelny fallback chain)
        dl_period = "5y" if is_strategy_view else period
        import pandas as pd
        _parts = {}
        for _t in selected:
            _s = download_single(_t, period=dl_period)
            if _s is not None and len(_s) > 0:
                _parts[_t] = _s
        prices_full = pd.DataFrame(_parts) if _parts else pd.DataFrame()

        # Strategia 12-1: przytnij do okna 13M-1M wstecz dla ceny/drawdown
        if is_strategy_view and len(prices_full) > 273:
            prices = prices_full.iloc[-273:-21]
        elif is_strategy_view:
            st.warning(tr("Za malo danych dla widoku Strategia 12-1. Wyswietlam dostepne dane."))
            prices = prices_full
        else:
            prices = prices_full

        if prices.empty:
            st.error(tr("Nie udalo sie pobrac danych."))
            _ok = False

    if _ok:
        # Zakladki
        tab1, tab2, tab3 = st.tabs([tr("📈 Cena"), tr("🚀 Momentum"), tr("📉 Drawdown")])

        with tab1:
            normalize = st.checkbox(tr("Normalizuj (baza = 100)"), value=True, key="wyk_norm")
            title = "Cena znormalizowana (baza = 100)" if normalize else "Cena (USD)"
            fig = price_chart(prices, title=title, normalize=normalize)
            st.plotly_chart(fig, width="stretch", key="wyk_price")

        with tab2:
            # Momentum uzywa pelnych danych (nie przycinanych), zeby rolling mial wystarczajaco historii
            mom_data = prices_full if is_strategy_view else prices
            max_window = min(504, len(mom_data) - 1) if len(mom_data) > 21 else 21
            default_window = min(252, max_window)
            window = st.slider(tr("Okno momentum (dni)"), 21, max_window, default_window, step=21, key="wyk_window")
            fig = momentum_chart(mom_data, window=window, title=tr('Momentum {window}D (rolling)', window=window))
            st.plotly_chart(fig, width="stretch", key="wyk_mom")

        with tab3:
            fig = drawdown_chart(prices)
            st.plotly_chart(fig, width="stretch", key="wyk_dd")


def render_h2h_tab() -> None:
    """Zakladka Head-to-head — logika w components/h2h_compare.py."""
    render_h2h()


def render_side_by_side_tab() -> None:
    """Tresc dawnej 21_side_by_side.py."""
    st.caption(tr("Porownaj dwa aktywa obok siebie — cena, drawdown, statystyki i Relative Strength"))
    # --- Polaczony universe ---
    all_names = {**ETF_NAMES, **SP500_NAMES, **GPW_NAMES, **CRYPTO_NAMES}
    all_categories = {**ETF_CATEGORY_MAP, **SP500_SECTOR_MAP, **GPW_CATEGORY_MAP, **CRYPTO_CATEGORY_MAP}

    # Top aktywa (zredukowana lista dla szybkosci)
    top_tickers = (
        ALL_TICKERS
        + ALL_SP500_TICKERS[:50]
        + ALL_GPW_TICKERS[:30]
        + CRYPTO_BY_MCAP[:30]
        + st.session_state.get("custom_tickers", [])
    )
    # Usun duplikaty zachowujac kolejnosc
    seen = set()
    unique_tickers = []
    for t in top_tickers:
        if t not in seen:
            seen.add(t)
            unique_tickers.append(t)

    options_map = {t: f"{t} — {all_names.get(t, t)}" for t in unique_tickers}

    # --- Selektory ---
    col_a, col_b, col_period = st.columns([2, 2, 1])
    with col_a:
        ticker_a = st.selectbox(tr("Aktywo A"), unique_tickers, index=0,
                                format_func=lambda x: options_map[x], key="sbs_a")
    with col_b:
        default_b = min(1, len(unique_tickers) - 1)
        ticker_b = st.selectbox(tr("Aktywo B"), unique_tickers, index=default_b,
                                format_func=lambda x: options_map[x], key="sbs_b")
    with col_period:
        period_map = {
            "6 miesiecy": "6mo", "1 rok": "1y", "2 lata": "2y",
            "5 lat": "5y", "10 lat": "10y", "Maksymalny": "max",
        }
        period_label = st.selectbox(tr("Okres"), list(period_map.keys()), index=2, key="sbs_period", format_func=tr)
        period = period_map[period_label]

    if ticker_a == ticker_b:
        st.warning(tr("Wybierz dwa rozne aktywa."))
        return

    # --- Pobierz dane ---
    with st.spinner(tr("Pobieram dane...")):
        _parts = {}
        for _t in [ticker_a, ticker_b]:
            _s = download_single(_t, period=period)
            if _s is not None and len(_s) > 0:
                _parts[_t] = _s
        prices = pd.DataFrame(_parts) if _parts else pd.DataFrame()

    if prices.empty or ticker_a not in prices.columns or ticker_b not in prices.columns:
        st.error(tr("Nie udalo sie pobrac danych dla wybranych aktywow."))
        return

    rf = get_risk_free()
    rf_decimal = rf / 100.0
    rets = latest_returns(prices)

    # --- Karty porownawcze ---
    col_left, col_right = st.columns(2)
    for col, ticker in [(col_left, ticker_a), (col_right, ticker_b)]:
        with col:
            r = rets.loc[ticker] if ticker in rets.index else pd.Series()
            comparison_card(
                ticker, all_names.get(ticker, ticker),
                all_categories.get(ticker, ""), r, 0 if ticker == ticker_a else 1,
            )

    st.divider()

    # --- Side-by-side: Cena + Drawdown ---
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown(f"#### {ticker_a}")
        fig = price_chart(prices[[ticker_a]], title=tr('Cena — {ticker_a}', ticker_a=ticker_a), normalize=True)
        st.plotly_chart(fig, width="stretch", key="sbs_price_a")
        fig = drawdown_chart(prices[[ticker_a]], title=tr('Drawdown — {ticker_a}', ticker_a=ticker_a))
        st.plotly_chart(fig, width="stretch", key="sbs_dd_a")

        s_a = calc_stats(prices[ticker_a].dropna(), 252, rf_decimal)
        stats_table({ticker_a: s_a})

    with col_right:
        st.markdown(f"#### {ticker_b}")
        fig = price_chart(prices[[ticker_b]], title=tr('Cena — {ticker_b}', ticker_b=ticker_b), normalize=True)
        st.plotly_chart(fig, width="stretch", key="sbs_price_b")
        fig = drawdown_chart(prices[[ticker_b]], title=tr('Drawdown — {ticker_b}', ticker_b=ticker_b))
        st.plotly_chart(fig, width="stretch", key="sbs_dd_b")

        s_b = calc_stats(prices[ticker_b].dropna(), 252, rf_decimal)
        stats_table({ticker_b: s_b})

    st.divider()

    # --- Wspolna sekcja: Korelacja + Relative Strength ---
    st.markdown(tr("### Porownanie wspolne"))

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(tr("#### Korelacja"))
        corr = correlation_matrix(prices, period=252)
        fig = correlation_heatmap(corr, title=tr("Macierz korelacji"))
        st.plotly_chart(fig, width="stretch", key="sbs_corr")

    with col2:
        st.markdown(tr("#### Relative Strength"))
        rs_data = relative_strength(prices[ticker_a].dropna(), prices[ticker_b].dropna())
        if not rs_data.empty:
            fig = rs_chart(rs_data, ticker_a, ticker_b)
            st.plotly_chart(fig, width="stretch", key="sbs_rs")
        else:
            st.info(tr("Za malo wspolnych danych do RS."))


st.markdown(tr("# Porównaj"))
tab_charts, tab_h2h, tab_sbs = st.tabs([tr("📈 Wykresy"), tr("⚖️ Head-to-head"), tr("🔀 Side-by-side")])
with tab_charts:
    render_charts_tab()
with tab_h2h:
    render_h2h_tab()
with tab_sbs:
    render_side_by_side_tab()

render_footer()
