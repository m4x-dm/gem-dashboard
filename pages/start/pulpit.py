"""Pulpit — centrum dowodzenia (domyslna strona).

Darmowe: wyszukiwarka, pasek stanu (sygnal GEM, regime, wskazniki rynku), Top 5 ETF.
Premium: watchlista, wyniki tygodnia, wygrani/przegrani, wyniki strategii 5 lat, eksport PDF.
Kazda karta renderuje sie niezaleznie — blad w jednej nie psuje reszty.
"""
import math
import unicodedata

import pandas as pd
import streamlit as st
from streamlit_local_storage import LocalStorage

from components import nav
from components.auth import is_premium, premium_teaser
from components.cards import (signal_card, metric_row, top_etf_cards, stats_table,
                              data_status_card, alert_banner)
from components.charts import sparkline_chart
from components.constants import GREEN, RED
from components.formatting import color_for_value, MUTED, BG_CARD, BORDER
from components.sidebar import get_risk_free, render_footer
from components.watchlist import get_watchlist
from data import market_status as ms
from data.downloader import download_prices, download_single
from data.etf_universe import ALL_TICKERS, ETF_NAMES, ETF_CATEGORY_MAP
from data.financials import _detect_market, _status_badge, bulk_fetch_earnings_calendar
from data.gpw_universe import ALL_GPW_TICKERS, GPW_NAMES
from data.momentum import gem_classic_signal, build_ranking, backtest_gem
from data.sp500_universe import ALL_SP500_TICKERS, SP500_NAMES

REGIME_COLORS = {"Risk-On": GREEN, "Risk-Off": RED, "Neutralny": "#F59E0B"}
PREMIUM = is_premium()


def unavailable(title: str) -> None:
    st.caption(f"{title}: dane chwilowo niedostępne")


def _ascii(text) -> str:
    """Bez polskich znakow diakrytycznych — PDF na Linuksie uzywa Helvetica."""
    t = str(text).translate(str.maketrans({"ł": "l", "Ł": "L"}))
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")


def _finite(x) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def card(title: str, value: str, sub: str, border: str = BORDER) -> None:
    st.html(
        f'<div style="background:{BG_CARD};border:1px solid {border};border-radius:14px;padding:16px;height:100%">'
        f'<div style="font-size:0.7rem;color:{MUTED};text-transform:uppercase;letter-spacing:0.08em">{title}</div>'
        f'<div style="font-size:1.4rem;font-weight:800;color:#E5E7EB;margin:6px 0">{value}</div>'
        f'<div style="font-size:0.8rem;color:{MUTED}">{sub}</div></div>'
    )


# --- 1. Alerty cenowe (logika z dawnego Podsumowania, F1) --------------------
def render_alerts() -> None:
    periods = {"1D": 1, "1W": 5, "1M": 21}
    for a in st.session_state.get("alerts", []):
        s = download_single(a["ticker"], period="3mo")
        days = periods.get(a["period"], 1)
        if s is not None and len(s) > days:
            chg = s.iloc[-1] / s.iloc[-1 - days] - 1
            if _finite(chg):
                alert_banner(a["ticker"], a["condition"], a["threshold"], a["period"], chg)


# --- 2. Wyszukiwarka ---------------------------------------------------------
def _on_search() -> None:
    """Callback: ustaw deep-dive i wyczysc pole (w callbacku wolno zmienic stan widgetu)."""
    choice = st.session_state.get("pulpit_search")
    if not choice:
        return
    prefix = "sp500" if _detect_market(choice) == "SP500" else "gpw"
    st.session_state[f"{prefix}_deep_dive_ticker"] = choice
    st.session_state[f"{prefix}_pending_view"] = "deep_dive"
    st.session_state["pulpit_search"] = ""
    st.session_state["_pulpit_go"] = prefix


def render_search() -> None:
    names = {**SP500_NAMES, **GPW_NAMES}
    options = [""] + sorted(names, key=lambda t: names[t])
    st.selectbox(
        "🔎 Szukaj spółki (S&P 500 i GPW)", options, key="pulpit_search", on_change=_on_search,
        format_func=lambda t: "Wpisz nazwę lub ticker…" if not t else f"{t} — {names[t]}",
    )
    target = st.session_state.pop("_pulpit_go", None)
    if target:
        nav.go(target)


# --- 3. Pasek stanu ----------------------------------------------------------
def render_status_bar(prices: pd.DataFrame, rf: float):
    """Sygnal GEM + metryki 12M, regime rynku. Zwraca (gem_data, regime) dla eksportu PDF."""
    gem_data, regime = None, None
    c_sig, c_reg = st.columns([2, 1])
    with c_sig:
        try:
            gem_data = gem_classic_signal(prices, rf)
            signal_card(gem_data)
        except Exception:
            gem_data = None
            unavailable("Sygnał GEM")
        else:
            try:
                hist = backtest_gem(download_prices(["QQQ", "VEA", "EEM", "ACWI", "AGG"], period="max"), rf)
                since = ms.signal_since(hist["signals"]) if hist else None
                nxt = ms.next_rebalance_date(pd.Timestamp.now())
                if since:
                    st.caption(f"Pozycja od {since[0]:%d.%m.%Y} · następne przeliczenie: {nxt:%d.%m.%Y}")
            except Exception:
                pass
    with c_reg:
        try:
            data = {t: download_single(t, period="1y") for t in ms.REGIME_TICKERS}
            regime = ms.compute_regime({t: s for t, s in data.items() if s is not None})
            card("Regime rynku", regime["label"], f'{regime["desc"]} · Risk-On score: {regime["score"]:.0f}%',
                 border=REGIME_COLORS[regime["label"]])
        except Exception:
            regime = None
            unavailable("Regime rynku")
    if gem_data is not None:
        try:
            metric_row(gem_data["qqq_12m"], gem_data["vea_12m"], gem_data["eem_12m"],
                       gem_data["acwi_12m"], gem_data["agg_12m"], rf)
        except Exception:
            unavailable("Metryki 12M")
    return gem_data, regime


def _vix_label(v: float) -> str:
    if v < 15:
        return "Niski strach"
    if v < 25:
        return "Umiarkowany"
    return "Wysoki strach"


def render_market_tiles() -> list:
    """Wskazniki rynku (VIX, indeksy, FX, zloto, BTC...). Zwraca liste sparklines dla PDF."""
    st.markdown("### Wskaźniki rynku")
    sparks = []
    per_row = 4
    cols = st.columns(per_row)
    for i, (ticker, label) in enumerate(ms.MARKET_TILES):
        with cols[i % per_row]:
            try:
                s = download_single(ticker, period="6mo")
                if s is None or len(s) < 2:
                    unavailable(label)
                    continue
                last = float(s.iloc[-1])
                chg_d = ms.daily_change(s.to_frame(ticker))
                if not _finite(last) or chg_d.empty:
                    unavailable(label)
                    continue
                c1d = float(chg_d.iloc[0])
                chg_1m = float(s.iloc[-1] / s.iloc[-21] - 1) if len(s) > 21 else float("nan")
                sub = f'<span style="color:{color_for_value(c1d)}">{c1d*100:+.2f}% (1D)</span>'
                if _finite(chg_1m):
                    sub += f' · <span style="color:{color_for_value(chg_1m)}">{chg_1m*100:+.1f}% (1M)</span>'
                    sparks.append((ticker, label, last, chg_1m))
                extra = f' · {_vix_label(last)}' if ticker == "^VIX" else ""
                st.html(
                    f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;'
                    f'padding:8px;text-align:center;margin-bottom:2px">'
                    f'<div style="font-size:0.65rem;color:{MUTED};text-transform:uppercase">{label}</div>'
                    f'<div style="font-weight:700;color:#E5E7EB">{last:,.2f}</div>'
                    f'<div style="font-size:0.75rem">{sub}<span style="color:{MUTED}">{extra}</span></div></div>'
                )
                st.plotly_chart(sparkline_chart(s, height=60), width="stretch", key=f"tile_spark_{ticker}")
            except Exception:
                unavailable(label)
    return sparks


# --- 4. Trzy kolumny (Premium) ------------------------------------------------
def render_watchlist(ls) -> None:
    st.markdown("#### ⭐ Moja watchlista")
    tickers = sorted(get_watchlist(ls) | set(st.session_state.get("favorites", set())))
    if not tickers:
        st.caption("Pusta. Dodaj spółki gwiazdką ⭐ w S&P 500 / GPW albo w sidebarze (Ulubione).")
        return
    for t in tickers[:10]:
        try:
            s = download_single(t, period="3mo")
            chg = ms.daily_change(s.to_frame(t)) if s is not None else pd.Series(dtype=float)
            if s is None or chg.empty:
                st.caption(f"{t}: brak danych")
                continue
            c1, c2 = st.columns([1, 1])
            c1.markdown(f"**{t}** {s.iloc[-1]:,.2f}  \n"
                        f"<span style='color:{color_for_value(chg.iloc[0])}'>{chg.iloc[0]*100:+.2f}%</span>",
                        unsafe_allow_html=True)
            c2.plotly_chart(sparkline_chart(s, height=50), width="stretch", key=f"wl_spark_{t}")
        except Exception:
            st.caption(f"{t}: brak danych")


def render_week_earnings(ls) -> None:
    st.markdown("#### 📅 Wyniki w tym tygodniu")
    tickers = tuple(ms.pulpit_earnings_tickers(get_watchlist(ls)))
    df = bulk_fetch_earnings_calendar(tickers, window_days=7)
    if df is None or df.empty:
        st.caption("Brak nadchodzących raportów w ciągu 7 dni dla watchlisty i największych spółek.")
        return
    df = df.assign(date=pd.to_datetime(df["date"]))
    today = pd.Timestamp.now().normalize()
    df = df[(df["date"] >= today) & (df["date"] <= today + pd.Timedelta(days=7))]
    if df.empty:
        st.caption("Brak nadchodzących raportów w ciągu 7 dni dla watchlisty i największych spółek.")
        return
    order = {t: i for i, t in enumerate(tickers)}
    df = df.assign(_o=df["ticker"].map(order)).sort_values(["_o", "date"]).head(10)
    for _, r in df.iterrows():
        st.markdown(f"**{r['ticker']}** · {r['date']:%d.%m} · "
                    f"{_status_badge(r['date'], r.get('eps_actual'), r.get('eps_estimate'))}")


@st.fragment
def render_movers() -> None:
    st.markdown("#### 🔥 Wygrani / przegrani dnia")
    for label, universe in (("S&P 500", ALL_SP500_TICKERS), ("GPW", ALL_GPW_TICKERS)):
        with st.spinner(f"Liczę zmiany {label}…"):
            try:
                gainers, losers = ms.top_movers(ms.market_movers(tuple(universe)), n=5)
            except Exception:
                unavailable(label)
                continue
        if gainers.empty:
            unavailable(label)
            continue
        st.caption(label)
        g, l = st.columns(2)
        g.dataframe((gainers * 100).round(2).rename("% d/d"), width="stretch")
        l.dataframe((losers * 100).round(2).rename("% d/d"), width="stretch")


# --- 5. Top 5 ETF + wyniki 5 lat ------------------------------------------------
def render_top_etf(prices: pd.DataFrame, rf: float):
    st.markdown("### Top 5 ETF wg momentum")
    names, cats = dict(ETF_NAMES), dict(ETF_CATEGORY_MAP)
    for t in st.session_state.get("custom_tickers", []):
        names.setdefault(t, t)
        cats.setdefault(t, "Wlasne")
    try:
        ranking = build_ranking(prices, rf, skip_month=False).dropna(subset=["Wynik"])
        if ranking.empty:
            unavailable("Ranking ETF")
        else:
            top_etf_cards(ranking, names, cats, n=5)
    except Exception:
        ranking = pd.DataFrame()
        unavailable("Ranking ETF")
    return ranking, names


def render_strategy_5y(rf: float):
    st.markdown("### Wyniki strategii (5 lat)")
    try:
        bt = backtest_gem(download_prices(["QQQ", "VEA", "EEM", "ACWI", "AGG"], period="7y"), rf)
    except Exception:
        unavailable("Wyniki strategii")
        return None
    if bt is None:
        st.info("Za malo danych do backtestu GEM (wymagane 252+ sesji).")
        return None
    show = {k: bt["stats"][k] for k in ("GEM", "QQQ B&H", "ACWI B&H", "AGG B&H") if k in bt["stats"]}
    if show:
        stats_table(show)
    return show


def render_pdf_export(gem_data, regime, sparks, ranking, names, show_stats) -> None:
    with st.expander("📄 Eksport raportu PDF"):
        st.caption("Wybierz sekcje do wlaczenia w raport")
        pdf_gem = st.checkbox("Sygnal GEM", value=True, key="pdf_gem")
        pdf_regime = st.checkbox("Regime rynkowy", value=True, key="pdf_regime")
        pdf_top5 = st.checkbox("Top 5 ETF-ow", value=True, key="pdf_top5")
        pdf_sparks = st.checkbox("Kluczowe aktywa", value=True, key="pdf_sparks")
        pdf_bt = st.checkbox("Statystyki strategii", value=True, key="pdf_bt")
        pdf_rank = st.checkbox("Ranking ETF top 10", value=True, key="pdf_rank")
        if not st.button("Generuj raport PDF", key="pdf_gen_btn"):
            return
        from components.pdf_report import generate_report
        sections = {}
        if pdf_gem and gem_data is not None:
            sections["gem_signal"] = gem_data
        if pdf_regime and regime is not None:
            sections["regime"] = {"label": _ascii(regime["label"]), "score": regime["score"]}
        if pdf_top5 and not ranking.empty:
            sections["top_etfs"] = [(t, names.get(t, t), row.get("Wynik", 0))
                                    for t, row in ranking.head(5).iterrows()]
        if pdf_sparks and sparks:
            sections["sparklines"] = [(_ascii(t), _ascii(lbl), p, c) for t, lbl, p, c in sparks]
        if pdf_bt and show_stats:
            sections["backtest_stats"] = show_stats
        if pdf_rank and not ranking.empty:
            sections["ranking_top10"] = [(t, names.get(t, t), row.get("Wynik", 0),
                                          row.get("Momentum_abs", "—"))
                                         for t, row in ranking.head(10).iterrows()]
        if sections:
            st.download_button("📥 Pobierz PDF", data=generate_report(sections),
                               file_name=f"gem_raport_{pd.Timestamp.now():%Y%m%d}.pdf",
                               mime="application/pdf")
        else:
            st.warning("Wybierz co najmniej jedna sekcje.")


# =============================================================================
st.markdown("# 📈 Pulpit")
try:
    render_alerts()
except Exception:
    pass
render_search()

tickers = list(set(ALL_TICKERS + st.session_state.get("custom_tickers", [])))
prices = download_prices(tickers)
rf = get_risk_free()

gem_data, regime = render_status_bar(prices, rf)
sparks = render_market_tiles()
st.divider()

col_wl, col_earn, col_mov = st.columns(3)
if PREMIUM:
    ls = LocalStorage()
    with col_wl:
        try:
            render_watchlist(ls)
        except Exception:
            unavailable("Watchlista")
    with col_earn:
        try:
            render_week_earnings(ls)
        except Exception:
            unavailable("Wyniki w tym tygodniu")
    mov_slot = col_mov.container()
else:
    with col_wl:
        premium_teaser("⭐ Moja watchlista", "Twoje spółki z ceną, zmianą dnia i mini-wykresem.")
    with col_earn:
        premium_teaser("📅 Wyniki w tym tygodniu", "Kto raportuje w tym tygodniu — najpierw Twoje spółki.")
    with col_mov:
        premium_teaser("🔥 Wygrani i przegrani", "Największe zmiany dnia w S&P 500 i na GPW.")

st.divider()
ranking, names = render_top_etf(prices, rf)

if PREMIUM:
    show_stats = render_strategy_5y(rf)
    render_pdf_export(gem_data, regime, sparks, ranking, names, show_stats)
else:
    premium_teaser("Wyniki strategii (5 lat)", "GEM vs QQQ, ACWI i obligacje: CAGR, Sharpe, max drawdown.")

if PREMIUM:
    # Ciezkie pobieranie ~600 spolek na koncu — nie blokuje reszty strony
    with mov_slot:
        render_movers()

with st.expander("Status danych"):
    try:
        data_status_card()
    except Exception:
        unavailable("Status danych")

render_footer()
