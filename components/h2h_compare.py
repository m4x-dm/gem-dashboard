"""Porownanie head-to-head 2-4 instrumentow — wspolny komponent.

Wydzielone 2026-11-22 z views/etf/porownaj.py, zeby to samo porownanie
pokazac na stronie Sygnal GEM (koszyk QQQ/VEA/EEM/AGG).
"""
import streamlit as st
import pandas as pd
from components.sidebar import get_risk_free
from data.etf_universe import ALL_TICKERS, ETF_NAMES, ETF_CATEGORY_MAP
from data.downloader import (benchmark_status, download_single, download_stooq,
                             STOOQ_TICKERS)
from data.momentum import (latest_returns, correlation_matrix, calc_stats,
                           relative_strength)
from components.charts import price_chart, correlation_heatmap, rs_chart
from components.cards import comparison_card, stats_table
from components.i18n import tr


def render_h2h(default: list[str] | None = None, key: str = "h2h",
               caption: str | None = "Porownanie head-to-head 2-4 ETF-ow") -> None:
    """Porownanie head-to-head 2-4 instrumentow (dawna 4_porownanie.py).

    Wspolne dla ETF → Porownaj (default QQQ/VEA, key "h2h") i Sygnal GEM
    (koszyk GEM, wlasny prefiks kluczy, zeby widgety sie nie gryzly).
    """
    if default is None:
        default = ["QQQ", "VEA"]
    if caption:
        st.caption(tr(caption))
    # Indeksy GPW (dane ze stooq.com)
    GPW_INDEX_NAMES = {"WIG20": "WIG20 (GPW)", "mWIG40": "mWIG40 (GPW)", "sWIG80": "sWIG80 (GPW)"}
    GPW_INDEX_CAT = {t: "Indeksy GPW" for t in GPW_INDEX_NAMES}

    all_names = {**ETF_NAMES, **GPW_INDEX_NAMES}
    all_categories = {**ETF_CATEGORY_MAP, **GPW_INDEX_CAT}
    for t in st.session_state.get("custom_tickers", []):
        all_names.setdefault(t, t)
        all_categories.setdefault(t, "Wlasne")

    available = ALL_TICKERS + list(GPW_INDEX_NAMES.keys()) + st.session_state.get("custom_tickers", [])
    options = {t: f"{t} — {all_names.get(t, t)}" for t in available}

    col_sel, col_period = st.columns([3, 1])
    with col_sel:
        selected = st.multiselect(
            tr("Wybierz 2-4 instrumenty do porownania"),
            options=list(options.keys()),
            default=[t for t in default if t in options],
            format_func=lambda x: options[x],
            max_selections=4,
            key=f"{key}_sel",
        )
    with col_period:
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
        period_label = st.selectbox(tr("Okres"), list(period_map.keys()), index=4, key=f"{key}_period", format_func=tr)
        period = period_map[period_label]
        is_strategy_view = period_label == "Strategia 12-1"

    if len(selected) < 2:
        st.info(tr("Wybierz co najmniej 2 ETF-y."))
        return

    # Dane — rozdziel tickery yfinance vs stooq
    yf_tickers = [t for t in selected if t not in STOOQ_TICKERS]
    stooq_tickers = [t for t in selected if t in STOOQ_TICKERS]

    prices = pd.DataFrame()
    for _t in yf_tickers:
        _s = download_single(_t, period=period)
        if _s is not None and len(_s) > 0:
            prices[_t] = _s

    _stale_idx = []
    for t in stooq_tickers:
        s = download_stooq(t, period=period)
        if s is not None:
            prices[t] = s
            _state = benchmark_status(s)
            if _state["stale"]:
                _stale_idx.append(f"{t} (ostatnie notowanie {_state['last_date']})")

    # Indeksy GPW ida z ETF-ow Beta przez yfinance. Gdy to zrodlo padnie, zostaje
    # zamrozony cache - ma to byc widoczne, a nie udawac aktualnych danych.
    if _stale_idx:
        st.warning(tr("Nieaktualne dane indeksow: {v}. Porownanie moze wprowadzac w blad.",
                      v=", ".join(_stale_idx)))

    prices = prices.dropna(how="all")

    # Strategia 12-1: pokaz okres od 13 mies. wstecz do 1 mies. wstecz
    if is_strategy_view and len(prices) > 273:
        prices = prices.iloc[-273:-21]
    elif is_strategy_view:
        st.warning(tr("Za malo danych dla widoku Strategia 12-1. Wyswietlam dostepne dane."))
    if prices.empty:
        st.error(tr("Brak danych."))
        return

    # Metryki
    st.markdown(tr("### Stopy zwrotu"))
    rets = latest_returns(prices, skip_month=False)

    cols = st.columns(len(selected))
    for i, ticker in enumerate(selected):
        with cols[i]:
            r = rets.loc[ticker] if ticker in rets.index else pd.Series()
            comparison_card(
                ticker, all_names.get(ticker, ticker),
                all_categories.get(ticker, "Wlasne"), r, i,
            )

    st.divider()

    # Overlay cenowy
    st.markdown(tr("### Cena znormalizowana (baza = 100)"))
    fig = price_chart(prices, title=tr('Porownanie cenowe — {period_label}', period_label=tr(period_label)))
    st.plotly_chart(fig, width="stretch", key=f"{key}_price")

    st.divider()

    # Statystyki
    st.markdown(tr("### Statystyki"))
    rf = get_risk_free()
    rf_decimal = rf / 100.0
    cmp_stats = {}
    for t in selected:
        if t in prices.columns:
            cmp_stats[t] = calc_stats(prices[t].dropna(), 252, rf_decimal)
    if cmp_stats:
        stats_table(cmp_stats)

    st.divider()

    # Macierz korelacji
    st.markdown(tr("### Macierz korelacji (252 dni)"))
    corr = correlation_matrix(prices, period=252)
    fig = correlation_heatmap(corr)
    st.plotly_chart(fig, width="stretch", key=f"{key}_corr")

    # Interpretacja
    with st.expander(tr("Jak czytac korelacje?")):
        st.markdown(tr("""
        - **1.0** = doskonala korelacja dodatnia (ruchy w tym samym kierunku)
        - **0.0** = brak korelacji (niezalezne ruchy)
        - **-1.0** = doskonala korelacja ujemna (ruchy w przeciwnym kierunku)

        Dobrze zdywersyfikowany portfel powinien zawierac aktywa o **niskiej lub ujemnej korelacji**.
        """))

    st.divider()

    # =====================================================================
    # Relative Strength
    # =====================================================================
    st.markdown(tr("### Relative Strength"))

    rs_benchmark = st.selectbox(
        tr("Benchmark RS"), [t for t in selected], index=0, key=f"{key}_rs_bench",
    )
    rs_assets = [t for t in selected if t != rs_benchmark]

    if rs_assets and rs_benchmark in prices.columns:
        for asset_t in rs_assets:
            if asset_t in prices.columns:
                rs_data = relative_strength(prices[asset_t].dropna(), prices[rs_benchmark].dropna())
                if not rs_data.empty:
                    fig = rs_chart(rs_data, asset_t, rs_benchmark)
                    st.plotly_chart(fig, width="stretch", key=f"{key}_rs_{asset_t}")
    else:
        st.info(tr("Wybierz co najmniej 2 instrumenty."))
