"""Strona 8: Kryptowaluty — top 200, ranking momentum, Alt/BTC, wykresy, backtest."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from components.sidebar import setup_sidebar, get_risk_free, render_footer
from data.crypto_universe import (
    ALL_CRYPTO_TICKERS, CRYPTO_NAMES, CRYPTO_CATEGORY_MAP, CRYPTO_CATEGORIES,
    CRYPTO_BY_MCAP,
)
from data.downloader import download_prices, download_single
from data.momentum import (
    latest_returns, build_ranking, backtest_rotation, calc_stats,
    correlation_matrix, relative_strength,
    calc_ema, calc_macd, calc_rsi, calc_bollinger,
)
from components.formatting import (
    fmt_pct, fmt_number, color_for_value,
    GOLD, GREEN, RED, MUTED, BG_CARD, BORDER,
)
from components.charts import (
    price_chart, momentum_chart, drawdown_chart,
    ranking_bar_chart, correlation_heatmap, equity_chart, COLORS,
    _base_layout, ta_overview_chart, macd_chart, rsi_chart, rs_chart,
)
from components.cards import stats_table, comparison_card, final_value_card, ta_signal_card
from components.auth import require_premium

st.set_page_config(page_title="Kryptowaluty", page_icon="₿", layout="wide")
setup_sidebar()
if not require_premium(9): st.stop()

st.markdown("# ₿ Kryptowaluty — Top 200")

# ---------------------------------------------------------------------------
# Wspolne: wybor kategorii
# ---------------------------------------------------------------------------
CATEGORY_OPTIONS = ["Wszystkie"] + list(CRYPTO_CATEGORIES.keys())

TOP_N_OPTIONS = ["Top 10", "Top 20", "Top 50", "Top 100", "Top 200"]
ALTBTC_CATEGORY_OPTIONS = TOP_N_OPTIONS + ["Wszystkie"] + list(CRYPTO_CATEGORIES.keys())


def _tickers_for_category(cat: str) -> list[str]:
    """Zwraca liste tickerow dla wybranej kategorii."""
    if cat == "Wszystkie":
        return ALL_CRYPTO_TICKERS
    return list(CRYPTO_CATEGORIES.get(cat, {}).keys())


def _tickers_for_filter(label: str) -> list[str]:
    """Zwraca liste tickerow dla Top N lub kategorii."""
    if label.startswith("Top "):
        n = int(label.split()[1])
        return CRYPTO_BY_MCAP[:n]
    return _tickers_for_category(label)


def _flexible_score(ret_row: pd.Series) -> float:
    """Wynik kompozytowy z dostepnych okresow (renormalizuje wagi).

    Standardowo: 12M*50% + 6M*25% + 3M*15% + 1M*10%.
    Jesli brakuje niektorych okresow, renormalizuje wagi z dostepnych.
    Wymaga co najmniej 1M i 3M.
    """
    weights = {"12M": 0.50, "6M": 0.25, "3M": 0.15, "1M": 0.10}
    available = {}
    for period, w in weights.items():
        val = ret_row.get(period, np.nan)
        if pd.notna(val):
            available[period] = (val, w)

    # Wymog minimum: 1M i 3M
    if "1M" not in available or "3M" not in available:
        return np.nan

    if not available:
        return np.nan

    total_weight = sum(w for _, w in available.values())
    score = sum(val * (w / total_weight) for val, w in available.values())
    return score


# ---------------------------------------------------------------------------
# TABY
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Ranking momentum",
    "₿ Alt/BTC — sila vs Bitcoin",
    "📉 Wykresy",
    "⚖️ Porownanie",
    "🧪 Backtest momentum",
    "🔔 Sygnaly TA",
    "💪 Relative Strength",
])

# ========================== TAB 1: RANKING ==========================
with tab1:
    st.markdown("### Ranking momentum — kryptowaluty")

    col1, col2 = st.columns(2)
    with col1:
        cat_filter = st.selectbox("Kategoria", CATEGORY_OPTIONS, key="cr_rank_cat")
    with col2:
        mom_filter = st.selectbox("Momentum absolutny", ["Wszystkie", "TAK", "NIE"], key="cr_rank_mom")

    tickers = _tickers_for_category(cat_filter)
    if not tickers:
        st.warning("Brak tickerow dla wybranej kategorii.")
    else:
        if cat_filter == "Wszystkie":
            st.info("Pobieranie danych dla ~200 kryptowalut moze potrwac dluzej. Mozesz wybrac konkretna kategorie.")

        with st.spinner("Pobieram dane kryptowalut..."):
            prices = download_prices(tickers, period="2y")

        if prices.empty:
            st.error("Nie udalo sie pobrac danych.")
        else:
            rf = get_risk_free()
            ranking = build_ranking(prices, rf)

            # Dodaj nazwy i kategorie
            ranking["Nazwa"] = ranking.index.map(lambda t: CRYPTO_NAMES.get(t, t))
            ranking["Kategoria"] = ranking.index.map(lambda t: CRYPTO_CATEGORY_MAP.get(t, "—"))

            # Filtr
            filtered = ranking.copy()
            if cat_filter != "Wszystkie":
                filtered = filtered[filtered["Kategoria"] == cat_filter]
            if mom_filter != "Wszystkie":
                filtered = filtered[filtered["Momentum_abs"] == mom_filter]

            st.markdown(f"**{len(filtered)}** kryptowalut | Stopa wolna: **{rf:.2f}%**")

            display_df = filtered[["Nazwa", "Kategoria", "1M", "3M", "6M", "12M", "Wynik", "Momentum_abs"]].copy()
            display_df.index.name = "Ticker"
            for col in ["1M", "3M", "6M", "12M", "Wynik"]:
                display_df[col] = display_df[col].apply(lambda x: fmt_pct(x) if pd.notna(x) else "—")
            display_df = display_df.rename(columns={"Momentum_abs": "Mom. abs."})

            st.dataframe(display_df, use_container_width=True, height=min(700, 40 + len(display_df) * 35))

            # Eksport CSV
            csv = filtered[["Nazwa", "Kategoria", "1M", "3M", "6M", "12M", "Wynik", "Momentum_abs"]].copy()
            csv.index.name = "Ticker"
            st.download_button("📥 Eksportuj CSV", csv.to_csv(), "crypto_ranking.csv", "text/csv")

            st.divider()

            # Wykres slupkowy top 15
            valid = filtered.dropna(subset=["Wynik"])
            if not valid.empty:
                fig = ranking_bar_chart(valid, top_n=min(15, len(valid)), title="Top 15 — wynik momentum kryptowalut")
                st.plotly_chart(fig, use_container_width=True)

# ========================== TAB 2: ALT/BTC ==========================
with tab2:
    st.markdown("### Alt/BTC — sila altcoinow wzgledem Bitcoina")
    st.caption("Ktore altcoiny najlepiej performuja w relacji do BTC? Ratio alt/BTC rosnie = altcoin bije Bitcoina.")

    col1, col2 = st.columns(2)
    with col1:
        altbtc_cat = st.selectbox("Filtr", ALTBTC_CATEGORY_OPTIONS, index=1, key="altbtc_cat")
    with col2:
        altbtc_display_map = {
            "Strategia 12-1": 273,
            "1 miesiac": 21, "2 miesiace": 42, "3 miesiace": 63,
            "6 miesiecy": 126, "9 miesiecy": 189, "1 rok": 252, "2 lata": 504,
        }
        altbtc_display_label = st.selectbox("Okres wykresu", list(altbtc_display_map.keys()), index=0, key="altbtc_period")
        altbtc_display_days = altbtc_display_map[altbtc_display_label]
        altbtc_is_strategy = altbtc_display_label == "Strategia 12-1"

    # Pobierz altcoiny + BTC — ZAWSZE 2y dla poprawnego obliczenia momentum
    alt_tickers = _tickers_for_filter(altbtc_cat)
    # Usun BTC z listy altow (BTC/BTC = 1 zawsze)
    alt_tickers_clean = [t for t in alt_tickers if t != "BTC-USD"]

    _altbtc_ok = True
    if not alt_tickers_clean:
        st.warning("Brak altcoinow do analizy (wybrana kategoria zawiera tylko BTC).")
        _altbtc_ok = False

    if _altbtc_ok:
        all_needed = list(set(alt_tickers_clean + ["BTC-USD"]))

        if altbtc_cat == "Wszystkie" or altbtc_cat in ("Top 100", "Top 200"):
            st.info(f"Pobieranie danych dla {len(all_needed)} kryptowalut moze potrwac dluzej. Wybierz mniejszy filtr, aby przyspieszyc.")

        with st.spinner("Pobieram dane kryptowalut i BTC..."):
            altbtc_prices = download_prices(all_needed, period="2y")

        if altbtc_prices.empty or "BTC-USD" not in altbtc_prices.columns:
            st.error("Nie udalo sie pobrac danych BTC.")
            _altbtc_ok = False

    if _altbtc_ok:
        btc_prices = altbtc_prices["BTC-USD"]
        available_alts = [t for t in alt_tickers_clean if t in altbtc_prices.columns]

        if not available_alts:
            st.error("Brak danych altcoinow.")
            _altbtc_ok = False

    if _altbtc_ok:
        # Oblicz ratio alt/BTC
        ratio_df = pd.DataFrame(index=altbtc_prices.index)
        for alt in available_alts:
            ratio = altbtc_prices[alt] / btc_prices
            ratio_df[alt] = ratio

        ratio_df = ratio_df.dropna(how="all")
        # Usun kolumny z samymi NaN
        ratio_df = ratio_df.dropna(axis=1, how="all")

        if ratio_df.empty or len(ratio_df) < 22:
            st.error("Za malo danych do obliczenia ratio alt/BTC.")
            _altbtc_ok = False

    if _altbtc_ok:
        # Oblicz momentum ratio z elastycznym wynikiem
        ratio_rets = latest_returns(ratio_df)
        ratio_rets["Wynik"] = ratio_rets.apply(_flexible_score, axis=1)
        ratio_rets = ratio_rets.dropna(subset=["Wynik"])
        ratio_rets = ratio_rets.sort_values("Wynik", ascending=False)

        # Dodaj nazwy i kategorie
        ratio_rets["Nazwa"] = ratio_rets.index.map(lambda t: CRYPTO_NAMES.get(t, t))
        ratio_rets["Kategoria"] = ratio_rets.index.map(lambda t: CRYPTO_CATEGORY_MAP.get(t, "—"))

        if ratio_rets.empty:
            st.warning("Brak wystarczajacych danych do obliczenia ratio. Sprobuj inna kategorie.")
        else:
            # Top 20 tabela
            top20 = ratio_rets.head(20)
            st.markdown(f"#### Top 20 altcoinow vs BTC (ratio momentum) — {len(ratio_rets)} altcoinow z danymi")

            display_cols = ["Nazwa", "Kategoria"]
            for p in ["1M", "3M", "6M", "12M"]:
                if p in top20.columns:
                    display_cols.append(p)
            display_cols.append("Wynik")

            display_ratio = top20[display_cols].copy()
            display_ratio.index.name = "Ticker"
            for col in [c for c in display_cols if c not in ("Nazwa", "Kategoria")]:
                display_ratio[col] = display_ratio[col].apply(lambda x: fmt_pct(x) if pd.notna(x) else "—")

            st.dataframe(display_ratio, use_container_width=True)

            st.divider()

            # Wykres slupkowy zmian ratio top 20
            st.markdown("#### Wynik kompozytowy ratio alt/BTC — top 20")
            bar_data_valid = top20.dropna(subset=["Wynik"])
            if not bar_data_valid.empty:
                bar_sorted = bar_data_valid.head(20).sort_values("Wynik", ascending=True)
                bar_colors = [(GREEN if v > 0 else RED) for v in bar_sorted["Wynik"]]
                fig_bar = go.Figure(go.Bar(
                    x=bar_sorted["Wynik"] * 100,
                    y=[f"{t.replace('-USD','')} ({CRYPTO_NAMES.get(t, '')})" for t in bar_sorted.index],
                    orientation="h",
                    marker_color=bar_colors,
                    text=[f"{v*100:.1f}%" for v in bar_sorted["Wynik"]],
                    textposition="outside",
                    textfont=dict(size=10),
                ))
                fig_bar.update_layout(**_base_layout("Ratio alt/BTC — wynik kompozytowy (%)", height=max(400, len(bar_sorted) * 30)))
                fig_bar.update_xaxes(title_text="Zmiana ratio (%)")
                st.plotly_chart(fig_bar, use_container_width=True)

            st.divider()

            # Wykres liniowy ratio alt/BTC dla top 5 (znormalizowany do bazy 100)
            st.markdown("#### Ratio alt/BTC — top 5 (baza = 100)")
            top5_tickers = [t for t in ratio_rets.head(5).index.tolist() if t in ratio_df.columns]
            if top5_tickers:
                top5_ratio = ratio_df[top5_tickers].dropna(how="all")
                # Ogranicz do wybranego okresu wyswietlania
                if altbtc_is_strategy and len(top5_ratio) > 273:
                    top5_ratio = top5_ratio.iloc[-273:-21]
                elif len(top5_ratio) > altbtc_display_days:
                    top5_ratio = top5_ratio.iloc[-altbtc_display_days:]

                if not top5_ratio.empty and len(top5_ratio) > 1:
                    renamed = top5_ratio.rename(columns={t: f"{t.replace('-USD','')} / BTC" for t in top5_tickers})
                    fig_ratio = price_chart(renamed, title=f"Ratio alt/BTC (baza = 100) — {altbtc_display_label}", normalize=True)
                    st.plotly_chart(fig_ratio, use_container_width=True)

# ========================== TAB 3: WYKRESY ==========================
with tab3:
    st.markdown("### Wykresy — kryptowaluty")

    options_map = {t: f"{t.replace('-USD','')} — {CRYPTO_NAMES.get(t, t)}" for t in ALL_CRYPTO_TICKERS}

    selected_charts = st.multiselect(
        "Wybierz kryptowaluty (maks. 5)",
        options=list(options_map.keys()),
        default=["BTC-USD", "ETH-USD", "SOL-USD"],
        format_func=lambda x: options_map[x],
        max_selections=5,
        key="cr_chart_sel",
    )

    period_map = {
        "1 miesiac": "1mo", "3 miesiace": "3mo", "6 miesiecy": "6mo",
        "1 rok": "1y", "2 lata": "2y", "5 lat": "5y", "Maksymalny": "max",
    }
    period_label = st.selectbox("Okres", list(period_map.keys()), index=4, key="cr_chart_period")
    period = period_map[period_label]

    if not selected_charts:
        st.info("Wybierz co najmniej 1 kryptowalute.")
    else:
        with st.spinner("Pobieram dane..."):
            chart_prices = download_prices(selected_charts, period=period)

        if chart_prices.empty:
            st.error("Nie udalo sie pobrac danych.")
        else:
            sub1, sub2, sub3 = st.tabs(["📈 Cena", "🚀 Momentum", "📉 Drawdown"])

            with sub1:
                normalize = st.checkbox("Normalizuj (baza = 100)", value=True, key="cr_norm")
                title = "Cena znormalizowana (baza = 100)" if normalize else "Cena (USD)"
                fig = price_chart(chart_prices, title=title, normalize=normalize)
                st.plotly_chart(fig, use_container_width=True)

            with sub2:
                window = st.slider("Okno momentum (dni)", 21, 504, 252, step=21, key="cr_mom_win")
                fig = momentum_chart(chart_prices, window=window, title=f"Momentum {window}D (rolling)")
                st.plotly_chart(fig, use_container_width=True)

            with sub3:
                fig = drawdown_chart(chart_prices)
                st.plotly_chart(fig, use_container_width=True)

# ========================== TAB 4: POROWNANIE ==========================
with tab4:
    st.markdown("### Porownanie kryptowalut")

    options_cmp = {t: f"{t.replace('-USD','')} — {CRYPTO_NAMES.get(t, t)}" for t in ALL_CRYPTO_TICKERS}

    col_sel, col_period = st.columns([3, 1])
    with col_sel:
        selected_cmp = st.multiselect(
            "Wybierz 2-4 kryptowaluty do porownania",
            options=list(options_cmp.keys()),
            default=["BTC-USD", "ETH-USD"],
            format_func=lambda x: options_cmp[x],
            max_selections=4,
            key="cr_cmp_sel",
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
        cmp_period_label = st.selectbox("Okres", list(cmp_period_map.keys()), index=0, key="cr_cmp_period")
        cmp_period = cmp_period_map[cmp_period_label]
        cmp_is_strategy = cmp_period_label == "Strategia 12-1"

    if len(selected_cmp) < 2:
        st.info("Wybierz co najmniej 2 kryptowaluty.")
    else:
        with st.spinner("Pobieram dane..."):
            cmp_prices = download_prices(selected_cmp, period=cmp_period)

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
                        ticker, CRYPTO_NAMES.get(ticker, ticker),
                        CRYPTO_CATEGORY_MAP.get(ticker, ""), r, i,
                        ticker_display=ticker.replace("-USD", ""),
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
                    cmp_stats[t] = calc_stats(cmp_prices[t].dropna(), 365, rf_decimal)
            if cmp_stats:
                stats_table(cmp_stats)

            st.divider()

            # Macierz korelacji
            st.markdown("#### Macierz korelacji (252 dni)")
            corr = correlation_matrix(cmp_prices, period=252)
            fig = correlation_heatmap(corr)
            st.plotly_chart(fig, use_container_width=True)

# ========================== TAB 5: BACKTEST ==========================
with tab5:
    st.markdown("### Backtest rotacji momentum — kryptowaluty")
    st.caption("Co miesiac kupuj top N krypto wg wyniku kompozytowego. Porownanie z BTC buy & hold i equal-weight B&H.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        bt_cat = st.selectbox("Kategoria", CATEGORY_OPTIONS, key="cr_bt_cat")
    with col2:
        top_n = st.selectbox("Top N kryptowalut", [1, 3, 5, 10], index=1, key="cr_bt_topn")
    with col3:
        bt_period_map = {"1 rok": "1y", "2 lata": "2y", "5 lat": "5y"}
        bt_period_label = st.selectbox("Okres", list(bt_period_map.keys()), index=1, key="cr_bt_period")
        bt_period = bt_period_map[bt_period_label]
    with col4:
        start_capital = st.number_input("Kapital (USD)", value=10000, step=1000, min_value=100, key="cr_bt_cap")

    bt_tickers = _tickers_for_category(bt_cat)
    # Zawsze dodaj BTC do porownania
    if "BTC-USD" not in bt_tickers:
        bt_tickers = bt_tickers + ["BTC-USD"]

    _bt_ok = True
    if len(bt_tickers) < top_n + 1:
        st.warning(f"Za malo kryptowalut ({len(bt_tickers)}) dla top {top_n}.")
        _bt_ok = False

    if _bt_ok:
        with st.spinner("Pobieram dane i licze backtest..."):
            bt_prices = download_prices(bt_tickers, period=bt_period)

        if bt_prices.empty or len(bt_prices) < 91:
            st.error("Za malo danych do backtestu. Sprobuj dluzszy okres.")
            _bt_ok = False

    if _bt_ok:
        # --- Backtest: momentum rotation ---
        # Krypto: krotszy lookback niz akcje (90 dni ~ 3M)
        lookback = min(273, len(bt_prices) - 30)
        if lookback < 63:
            st.error("Za malo danych do backtestu (potrzeba min. 63 dni historii).")
            _bt_ok = False

    if _bt_ok:
        available_cols = [c for c in bt_prices.columns if bt_prices[c].dropna().shape[0] > lookback]
        if len(available_cols) < top_n:
            st.error(f"Tylko {len(available_cols)} kryptowalut ma wystarczajaco dlugie dane. Potrzeba min. {top_n}.")
            _bt_ok = False

    if _bt_ok:
        has_btc = "BTC-USD" in available_cols
        bm = {"Equal-Weight B&H": available_cols}
        if has_btc:
            bm["BTC Buy&Hold"] = "BTC-USD"

        result = backtest_rotation(
            bt_prices[available_cols].dropna(how="all"), top_n=top_n,
            lookback=lookback, start_capital=start_capital,
            trading_days=365, benchmarks=bm,
            score_func=_flexible_score,
        )

        if result is None:
            st.error("Za malo danych do backtestu.")
        else:
            # Krzywa kapitalu
            st.markdown("#### Krzywa kapitalu")
            fig = equity_chart(result["equity_curves"])
            st.plotly_chart(fig, use_container_width=True)

            # Statystyki z rf
            rf = get_risk_free()
            rf_decimal = rf / 100.0
            bt_stats = {}
            for name, eq in result["equity_curves"].items():
                bt_stats[name] = calc_stats(eq, 365, rf_decimal)

            st.markdown("#### Statystyki")
            stats_table(bt_stats)

            # Wartosci koncowe
            st.divider()
            strategies = list(result["equity_curves"].items())
            cols = st.columns(len(strategies))
            for i, (name, eq) in enumerate(strategies):
                with cols[i]:
                    final_value_card(name, eq.iloc[-1], start_capital, "USD")

# ========================== TAB 6: SYGNALY TA ==========================
with tab6:
    st.markdown("### Sygnaly analizy technicznej")
    st.caption("Trend-following: 5 wskaznikow z filtrem trendu EMA 200. Sygnaly generowane tylko w kierunku trendu.")

    col_ta1, col_ta2 = st.columns(2)
    with col_ta1:
        ta_options = {t: f"{t.replace('-USD','')} — {CRYPTO_NAMES.get(t, t)}" for t in ALL_CRYPTO_TICKERS}
        ta_ticker = st.selectbox("Kryptowaluta", options=list(ta_options.keys()),
                                  format_func=lambda x: ta_options[x], key="ta_ticker")
    with col_ta2:
        ta_period_map = {"3 miesiace": "3mo", "6 miesiecy": "6mo",
                         "1 rok": "1y", "2 lata": "2y"}
        ta_period_label = st.selectbox("Okres", list(ta_period_map.keys()), index=1, key="ta_period")
        ta_period = ta_period_map[ta_period_label]

    with st.expander("Parametry wskaznikow"):
        pc1, pc2, pc3, pc4 = st.columns(4)
        with pc1:
            ema_short = st.number_input("EMA krotka", value=20, min_value=5, max_value=100, key="ta_ema_s")
            ema_long = st.number_input("EMA dluga", value=50, min_value=10, max_value=300, key="ta_ema_l")
        with pc2:
            rsi_period = st.number_input("RSI okres", value=14, min_value=5, max_value=50, key="ta_rsi")
        with pc3:
            macd_fast = st.number_input("MACD fast", value=12, min_value=5, max_value=50, key="ta_macd_f")
            macd_slow = st.number_input("MACD slow", value=26, min_value=10, max_value=100, key="ta_macd_s")
            macd_signal = st.number_input("MACD signal", value=9, min_value=3, max_value=30, key="ta_macd_sig")
        with pc4:
            bb_period = st.number_input("BB okres", value=20, min_value=5, max_value=100, key="ta_bb_p")
            bb_std = st.number_input("BB odch. std.", value=2.0, min_value=0.5, max_value=4.0, step=0.5, key="ta_bb_std")

    _ta_ok = True
    with st.spinner("Pobieram dane..."):
        _ta_series = download_single(ta_ticker, period=ta_period)

    if _ta_series is None or len(_ta_series) == 0:
        st.error("Nie udalo sie pobrac danych.")
        _ta_ok = False

    if _ta_ok:
        ta_close = _ta_series.dropna()
        if len(ta_close) < 50:
            st.error("Za malo danych do analizy technicznej (min. 50 sesji).")
            _ta_ok = False

    if _ta_ok:
        # Oblicz wskazniki — zawsze z EMA 200 (jesli dane pozwalaja)
        has_ema200 = len(ta_close) >= 200
        ema_spans = [ema_short, ema_long]
        if has_ema200:
            ema_spans.append(200)
        ema_df = calc_ema(ta_close, spans=ema_spans)
        macd_df = calc_macd(ta_close, fast=macd_fast, slow=macd_slow, signal=macd_signal)
        rsi_series = calc_rsi(ta_close, period=rsi_period)
        bb_df = calc_bollinger(ta_close, period=bb_period, std_dev=bb_std)

        last_price = ta_close.iloc[-1]
        ema_short_col = f"EMA_{ema_short}"
        ema_long_col = f"EMA_{ema_long}"

        # --- 1. TREND: cena vs EMA(200) ---
        if has_ema200:
            ema200_val = ema_df["EMA_200"].iloc[-1]
            trend_val = 1 if last_price > ema200_val else -1
            trend_detail = f"({last_price:,.0f} vs {ema200_val:,.0f})"
        else:
            trend_val = 0
            trend_detail = "(brak danych EMA200)"

        # --- 2. EMA CROSSOVER: EMA krotka vs dluga ---
        ema_s_now = ema_df[ema_short_col].iloc[-1]
        ema_l_now = ema_df[ema_long_col].iloc[-1]
        ema_signal_val = 1 if ema_s_now > ema_l_now else -1
        ema_detail = f"({ema_s_now:,.0f} vs {ema_l_now:,.0f})"

        # --- 3. MACD: crossover + kierunek histogramu ---
        last_macd = macd_df.iloc[-1]
        prev_hist = macd_df["Histogram"].iloc[-2] if len(macd_df) > 1 else 0
        curr_hist = last_macd["Histogram"]
        hist_growing = curr_hist > prev_hist

        if last_macd["MACD"] > last_macd["Signal"] and hist_growing:
            macd_signal_val = 1
            macd_detail = "(cross+ hist rosnacy)"
        elif last_macd["MACD"] < last_macd["Signal"] and not hist_growing:
            macd_signal_val = -1
            macd_detail = "(cross- hist malejacy)"
        else:
            macd_signal_val = 0
            macd_detail = "(brak potwierdzenia)"

        # --- 4. RSI: > 50 z momentum = bull, < 50 z momentum = bear ---
        last_rsi = rsi_series.iloc[-1]
        rsi_5d_ago = rsi_series.iloc[-6] if len(rsi_series) > 5 else rsi_series.iloc[0]
        rsi_rising = last_rsi > rsi_5d_ago

        if last_rsi > 50 and rsi_rising:
            rsi_signal_val = 1
            rsi_detail = f"({last_rsi:.0f}, rosnacy)"
        elif last_rsi < 50 and not rsi_rising:
            rsi_signal_val = -1
            rsi_detail = f"({last_rsi:.0f}, malejacy)"
        else:
            rsi_signal_val = 0
            rsi_detail = f"({last_rsi:.0f}, brak potw.)"

        # --- 5. BOLLINGER %B: pozycja w wstedze ---
        last_bb = bb_df.iloc[-1]
        bb_width = last_bb["Upper"] - last_bb["Lower"]
        if bb_width > 0:
            pct_b = (last_price - last_bb["Lower"]) / bb_width
        else:
            pct_b = 0.5

        if pct_b > 0.5:
            bb_signal_val = 1
            bb_detail = f"(%B={pct_b:.2f}, powyzej)"
        elif pct_b < 0.5:
            bb_signal_val = -1
            bb_detail = f"(%B={pct_b:.2f}, ponizej)"
        else:
            bb_signal_val = 0
            bb_detail = f"(%B={pct_b:.2f})"

        # --- AGREGAT ---
        n_indicators = 5 if has_ema200 else 4
        aggregate = trend_val + ema_signal_val + macd_signal_val + rsi_signal_val + bb_signal_val

        signals_dict = {
            "trend": trend_val, "trend_detail": trend_detail,
            "ema": ema_signal_val, "ema_detail": ema_detail,
            "macd": macd_signal_val, "macd_detail": macd_detail,
            "rsi": rsi_signal_val, "rsi_detail": rsi_detail,
            "bollinger": bb_signal_val, "bb_detail": bb_detail,
            "aggregate": aggregate,
            "n_indicators": n_indicators,
        }

        # Karta sygnalu
        ta_signal_card(ta_ticker, CRYPTO_NAMES.get(ta_ticker, ta_ticker), signals_dict)

        # --- Dzienny agregat do generowania markerow na wykresie ---
        ema_cross_d = (ema_df[ema_short_col] > ema_df[ema_long_col]).astype(int) * 2 - 1
        # MACD: crossover + histogram direction
        macd_above = (macd_df["MACD"] > macd_df["Signal"]).astype(int)
        hist_dir = (macd_df["Histogram"].diff() > 0).astype(int)
        macd_d = pd.Series(0, index=macd_df.index)
        macd_d[(macd_above == 1) & (hist_dir == 1)] = 1
        macd_d[(macd_above == 0) & (hist_dir == 0)] = -1
        # RSI: > 50 rosnacy = +1, < 50 malejacy = -1
        rsi_above50 = (rsi_series > 50).astype(int)
        rsi_dir = (rsi_series.diff(5) > 0).astype(int)
        rsi_d = pd.Series(0, index=rsi_series.index)
        rsi_d[(rsi_above50 == 1) & (rsi_dir == 1)] = 1
        rsi_d[(rsi_above50 == 0) & (rsi_dir == 0)] = -1
        # Bollinger %B
        bb_pctb = (ta_close - bb_df["Lower"]) / (bb_df["Upper"] - bb_df["Lower"])
        bb_d = pd.Series(0, index=ta_close.index)
        bb_d[bb_pctb > 0.5] = 1
        bb_d[bb_pctb < 0.5] = -1
        # Trend (EMA 200)
        if has_ema200:
            trend_d = (ta_close > ema_df["EMA_200"]).astype(int) * 2 - 1
        else:
            trend_d = pd.Series(0, index=ta_close.index)

        agg_daily = (trend_d + ema_cross_d + macd_d + rsi_d + bb_d).dropna()
        threshold = 3 if has_ema200 else 2

        signal_records = []
        prev_label = "NEUTRALNY"
        for dt, val in agg_daily.items():
            if val >= threshold and prev_label != "BUY":
                signal_records.append({"date": dt, "type": "BUY", "price": ta_close.loc[dt], "aggregate": int(val)})
                prev_label = "BUY"
            elif val <= -threshold and prev_label != "SELL":
                signal_records.append({"date": dt, "type": "SELL", "price": ta_close.loc[dt], "aggregate": int(val)})
                prev_label = "SELL"
            elif -threshold < val < threshold:
                prev_label = "NEUTRALNY"

        signals_df = pd.DataFrame(signal_records) if signal_records else pd.DataFrame()

        # Wykresy
        st.markdown("#### Wykres cenowy + wskazniki")
        fig_main = ta_overview_chart(ta_close, ema_df, bb_df, signals_df,
                                      title=f"{ta_ticker.replace('-USD','')} — analiza techniczna ({ta_period_label})")
        st.plotly_chart(fig_main, use_container_width=True)

        col_m, col_r = st.columns(2)
        with col_m:
            fig_macd = macd_chart(macd_df, title="MACD")
            st.plotly_chart(fig_macd, use_container_width=True)
        with col_r:
            fig_rsi = rsi_chart(rsi_series, title=f"RSI ({rsi_period})")
            st.plotly_chart(fig_rsi, use_container_width=True)

        # Tabela ostatnich sygnalow
        if not signals_df.empty:
            st.divider()
            st.markdown("#### Historia sygnalow")
            display_signals = signals_df.copy()
            display_signals["date"] = pd.to_datetime(display_signals["date"]).dt.strftime("%Y-%m-%d")
            display_signals["price"] = display_signals["price"].apply(lambda x: f"${x:,.2f}")
            display_signals = display_signals.rename(columns={
                "date": "Data", "type": "Sygnal", "price": "Cena", "aggregate": "Agregat"
            })
            display_signals = display_signals.iloc[::-1].head(20).reset_index(drop=True)
            display_signals.index = display_signals.index + 1
            st.dataframe(display_signals, use_container_width=True)
        else:
            st.info("Brak sygnalow kupna/sprzedazy w wybranym okresie — rynek neutralny wg wybranych parametrow.")

        # Info o wskaznikach
        with st.expander("Jak interpretowac sygnaly?"):
            st.markdown(f"""
**5 wskaznikow trend-following (kazdy -1 / 0 / +1):**

1. **Trend (EMA 200):** Cena > EMA(200) = bullish, ponizej = bearish. Glowny filtr kierunku — nie kupuj w downtrend.
2. **EMA crossover:** EMA({ema_short}) > EMA({ema_long}) = bullish momentum, ponizej = bearish.
3. **MACD + histogram:** Crossover MACD/Signal potwierdzony kierunkiem histogramu. Wymaga zgodnosci obu — eliminuje falszywe crossovery.
4. **RSI momentum:** RSI > 50 i rosnacy = byki kontroluja, RSI < 50 i malejacy = niedzwiedzie. Nie uzywamy ekstremalnych poziomow 30/70 (lapanie spadajacych nozy).
5. **Bollinger %B:** Pozycja ceny w wstedze. %B > 0.5 (powyzej srodka) = trend up, < 0.5 = trend down.

**Agregat:** Suma {n_indicators} sygnalow. >= {threshold} = **KUP**, <= -{threshold} = **SPRZEDAJ**, reszta = **NEUTRALNY**

**Roznice vs prosta analiza:**
- Filtr trendu EMA(200) zapobiega kupowaniu w downtrend
- MACD wymaga potwierdzenia histogramem (mniej falszywych sygnalow)
- RSI oparty o momentum, nie o extreme levels (unikamy lapania spadajacych nozy)
- Bollinger mierzy pozycje w wstedze, nie dotkniecia band

*Sygnaly TA maja charakter informacyjny i nie stanowia rekomendacji inwestycyjnej.*
""")

# ========================== TAB 7: RELATIVE STRENGTH ==========================
with tab7:
    st.markdown("### Relative Strength vs BTC")
    st.caption("RS > 100 = kryptowaluta outperformuje Bitcoin")

    rs_options_cr = {t: f"{t.replace('-USD','')} — {CRYPTO_NAMES.get(t, t)}" for t in CRYPTO_BY_MCAP[:50]}
    rs_selected_cr = st.multiselect(
        "Wybierz krypto (maks. 5)",
        options=list(rs_options_cr.keys()),
        default=["ETH-USD", "SOL-USD"],
        format_func=lambda x: rs_options_cr[x],
        max_selections=5,
        key="cr_rs_sel",
    )

    rs_period_map = {
        "6 miesiecy": "6mo", "1 rok": "1y", "2 lata": "2y", "Maksymalny": "max",
    }
    rs_period_label = st.selectbox("Okres", list(rs_period_map.keys()), index=1, key="cr_rs_period")
    rs_period = rs_period_map[rs_period_label]

    if rs_selected_cr:
        rs_tickers_cr = list(set(rs_selected_cr + ["BTC-USD"]))
        with st.spinner("Pobieram dane..."):
            rs_prices_cr = download_prices(rs_tickers_cr, period=rs_period)

        if "BTC-USD" in rs_prices_cr.columns:
            for t in rs_selected_cr:
                if t in rs_prices_cr.columns and t != "BTC-USD":
                    rs_data = relative_strength(rs_prices_cr[t].dropna(), rs_prices_cr["BTC-USD"].dropna())
                    if not rs_data.empty:
                        fig = rs_chart(rs_data, t.replace("-USD", ""), "BTC")
                        st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nie udalo sie pobrac danych BTC.")
    else:
        st.info("Wybierz co najmniej 1 kryptowalute.")

render_footer()
