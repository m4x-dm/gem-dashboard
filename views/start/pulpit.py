"""Pulpit — centrum dowodzenia (domyslna strona).

Darmowe: wyszukiwarka, pasek stanu (sygnal GEM, regime, wskazniki rynku), Top 5 ETF, ulubione z sidebara, wyniki strategii 5 lat.
Cala strona jest darmowa (od 2026-11-18): watchlista (localStorage), wyniki tygodnia, wygrani/przegrani, eksport PDF.
Kazda karta renderuje sie niezaleznie — blad w jednej nie psuje reszty.
"""
import math
import unicodedata

import pandas as pd
import streamlit as st
from streamlit_local_storage import LocalStorage

from components import nav
from components.auth import is_premium
from components.cards import (card_html, metric_row, top_etf_cards, stats_table,
                              data_status_card, alert_banner, _sparkline_svg)
from components.charts import sparkline_chart
from components.constants import GREEN, RED, AMBER, GOLD, GOLD_SOFT, TEXT, BORDER, BG_HOVER, SHADOW
from components.formatting import color_for_value, MUTED, BG_CARD
from components.i18n import tr, is_pl
from components.sidebar import get_risk_free, render_footer
from components.watchlist import get_watchlist
from data import market_status as ms
from data.downloader import download_prices, download_single
from data.etf_universe import ALL_TICKERS, ETF_NAMES, ETF_CATEGORY_MAP
from data.financials import _status_badge, bulk_fetch_earnings_calendar
from data.gpw_universe import ALL_GPW_TICKERS, GPW_NAMES
from data.momentum import gem_classic_signal, build_ranking, backtest_gem
from data.sp500_universe import ALL_SP500_TICKERS, SP500_NAMES

REGIME_COLORS = {"Risk-On": GREEN, "Risk-Off": RED, "Neutralny": AMBER}
SIGNAL_COLORS = {"QQQ": GREEN, "VEA": "#60A5FA", "EEM": "#A78BFA", "ACWI": "#22D3EE", "AGG": AMBER}
SIGNAL_SHORT = {"QQQ": "Akcje USA", "VEA": "Rynki rozwinięte", "EEM": "Rynki wschodzące",
                "ACWI": "Akcje globalne", "AGG": "Obligacje"}
_DAYS_PL = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]
_MONTHS_PL = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia",
              "września", "października", "listopada", "grudnia"]
_DAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December"]
STATUS_CARD_HEIGHT = "132px"
PREMIUM = is_premium()


def unavailable(title: str) -> None:
    st.caption(f"{title}: " + tr("dane chwilowo niedostępne"))


def _ascii(text) -> str:
    """Bez polskich znakow diakrytycznych — PDF na Linuksie uzywa Helvetica."""
    t = str(text).translate(str.maketrans({"ł": "l", "Ł": "L"}))
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")


def _finite(x) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def date_pl(ts: pd.Timestamp, weekday: bool = False) -> str:
    """'15 listopada' lub 'niedziela, 15 listopada' (EN: 'Sunday, November 15')."""
    if not is_pl():
        txt = f"{_MONTHS_EN[ts.month - 1]} {ts.day}"
        return f"{_DAYS_EN[ts.weekday()]}, {txt}" if weekday else txt
    txt = f"{ts.day} {_MONTHS_PL[ts.month - 1]}"
    return f"{_DAYS_PL[ts.weekday()]}, {txt}" if weekday else txt


def greeting(now: pd.Timestamp) -> str:
    return tr("Dobry wieczór") if now.hour >= 18 else tr("Dzień dobry")


def status_card(label: str, value: str, caption: str, color: str = TEXT, pill: str = "") -> None:
    """Karta paska stanu — ta sama wysokosc dla Sygnalu i Regime (rowne karty)."""
    pill_html = (f'<span style="display:inline-block;background:{GOLD_SOFT};color:{GOLD};font-size:12px;'
                 f'padding:3px 10px;border-radius:999px;margin-left:8px;vertical-align:middle">{pill}</span>'
                 if pill else "")
    st.html(card_html(
        f'<div style="font-size:12px;color:{MUTED};margin-bottom:6px">{label}{pill_html}</div>'
        f'<div style="font-size:26px;font-weight:650;color:{color};line-height:1.2;'
        f'font-variant-numeric:tabular-nums">{value}</div>'
        f'<div style="font-size:12px;color:{MUTED};margin-top:8px;line-height:1.4">{caption}</div>',
        pad="16px 18px", extra=f"height:{STATUS_CARD_HEIGHT};box-sizing:border-box;overflow:hidden;",
    ))


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
    """Callback: zapamietaj wybor i wyczysc pole (w callbacku wolno zmienic stan widgetu).

    Samo przejscie na Karte spolki robi render_search() w glownym przebiegu
    skryptu — st.switch_page w callbacku nie dziala.
    """
    choice = st.session_state.get("pulpit_search")
    if not choice:
        return
    st.session_state["pulpit_search"] = ""
    st.session_state["_pulpit_go"] = choice


def render_search() -> None:
    names = {**SP500_NAMES, **GPW_NAMES}
    options = [""] + sorted(names, key=lambda t: names[t])
    st.selectbox(
        tr("Szukaj spółki (S&P 500 i GPW)"), options, key="pulpit_search", on_change=_on_search,
        format_func=lambda t: tr("Wpisz nazwę lub ticker…") if not t else f"{t} — {names[t]}",
    )
    if not PREMIUM:
        st.caption(tr("Przegląd spółki za darmo, pozostałe zakładki w Premium."))
    target = st.session_state.pop("_pulpit_go", None)
    if target:
        nav.go_company(target)


# --- 3. Pasek stanu ----------------------------------------------------------
def render_status_bar(prices: pd.DataFrame, rf: float):
    """Sygnal GEM + metryki 12M, regime rynku. Zwraca (gem_data, regime) dla eksportu PDF."""
    gem_data, regime = None, None
    c_sig, c_reg = st.columns(2)
    with c_sig:
        try:
            gem_data = gem_classic_signal(prices, rf)
            sig = gem_data["signal"]
            pill = ""
            try:
                hist = backtest_gem(download_prices(["QQQ", "VEA", "EEM", "ACWI", "AGG"], period="max"), rf)
                since = ms.signal_since(hist["signals"]) if hist else None
                if since:
                    days = (pd.Timestamp.now().normalize() - pd.Timestamp(since[0]).normalize()).days
                    pill = tr("od {n} dni", n=max(days, 0))
            except Exception:
                pass
            nxt = ms.next_rebalance_date(pd.Timestamp.now())
            value = (f"{tr(SIGNAL_SHORT[sig])} · {sig}" if sig in SIGNAL_SHORT else tr(gem_data["signal_label"]))
            status_card(tr("Sygnał GEM"), value, tr("Następne przeliczenie: {date}", date=date_pl(nxt)),
                        color=SIGNAL_COLORS.get(sig, MUTED), pill=pill)
        except Exception:
            gem_data = None
            unavailable(tr("Sygnał GEM"))
    with c_reg:
        try:
            data = {t: download_single(t, period="1y") for t in ms.REGIME_TICKERS}
            regime = ms.compute_regime({t: s for t, s in data.items() if s is not None})
            status_card(tr("Regime rynku"), tr(regime["label"]), f'{regime["score"]:.0f}/100 · {tr(regime["desc"])}',
                        color=REGIME_COLORS[regime["label"]])
        except Exception:
            regime = None
            unavailable(tr("Regime rynku"))
    if gem_data is not None:
        try:
            metric_row(gem_data["qqq_12m"], gem_data["vea_12m"], gem_data["eem_12m"],
                       gem_data["acwi_12m"], gem_data["agg_12m"], rf)
        except Exception:
            unavailable(tr("Metryki 12M"))
    return gem_data, regime


def _vix_label(v: float) -> str:
    if v < 15:
        return tr("Niski strach")
    if v < 25:
        return tr("Umiarkowany")
    return tr("Wysoki strach")


def _tile_html(label: str, last: float, c1d: float, chg_1m: float, spark: pd.Series, extra: str) -> str:
    sub = f'<span style="color:{color_for_value(c1d)}">{c1d*100:+.2f}%</span>'
    if _finite(chg_1m):
        sub += (f' <span style="color:{MUTED};font-size:11px">· 1M '
                f'<span style="color:{color_for_value(chg_1m)}">{chg_1m*100:+.1f}%</span></span>')
    if extra:
        sub += f' <span style="color:{MUTED};font-size:11px">· {extra}</span>'
    line_color = GREEN if (_finite(chg_1m) and chg_1m >= 0) else RED
    svg = _sparkline_svg(spark.tail(126), line_color, width=100, height=28, fill=False)
    return (
        f'<div style="background:{BG_CARD};border-radius:12px;padding:12px 14px;min-width:0">'
        f'<div style="font-size:12px;color:{MUTED}">{label}</div>'
        f'<div style="font-size:17px;font-weight:650;color:{TEXT};margin:3px 0;'
        f'font-variant-numeric:tabular-nums">{last:,.2f}</div>'
        f'<div style="font-size:12px;font-variant-numeric:tabular-nums">{sub}</div>'
        f'<div style="margin-top:6px">{svg}</div></div>'
    )


def render_market_tiles() -> list:
    """Wskazniki rynku (VIX, indeksy, FX, zloto, BTC...). Zwraca liste sparklines dla PDF."""
    st.markdown("### " + tr("Wskaźniki rynku"))
    sparks, tiles = [], []
    for ticker, label in ms.MARKET_TILES:
        label = tr(label)
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
            if _finite(chg_1m):
                sparks.append((ticker, label, last, chg_1m))
            extra = _vix_label(last) if ticker == "^VIX" else ""
            tiles.append(_tile_html(label, last, c1d, chg_1m, s, extra))
        except Exception:
            unavailable(label)
    if tiles:
        st.html(f'<div class="gem-tiles">{"".join(tiles)}</div>')
    return sparks


# --- 4. Trzy kolumny (darmowe) ------------------------------------------------
_MONTHS_SHORT_PL = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"]


def short_month_pl(ts) -> str:
    """Skrot miesiaca: 'lis', 'paź' (EN: 'Nov')."""
    m = pd.Timestamp(ts).month
    return _MONTHS_EN[m - 1][:3] if not is_pl() else _MONTHS_SHORT_PL[m - 1]


def days_label(n: int) -> str:
    """Etykieta odleglosci: 'dziś', 'jutro', 'za 3 dni'."""
    if n <= 0:
        return tr("dziś")
    if n == 1:
        return tr("jutro")
    return tr("za {n} dni", n=n)


def _ticker_name(t: str) -> str:
    etf = ETF_NAMES.get(t)
    return SP500_NAMES.get(t) or GPW_NAMES.get(t) or (tr(etf) if etf else "")


def _pill(chg: float) -> str:
    up = chg >= 0
    bg, fg = ("rgba(52,211,153,.12)", GREEN) if up else ("rgba(248,113,113,.12)", RED)
    return (f'<span style="background:{bg};color:{fg};font-size:12px;padding:2px 8px;border-radius:999px;'
            f'font-variant-numeric:tabular-nums;white-space:nowrap">{chg*100:+.2f}%</span>')


def _ticker_block(t: str, dot: str = "") -> str:
    name = _ticker_name(t)
    sub = (f'<div style="font-size:12px;color:{MUTED};white-space:nowrap;overflow:hidden;'
           f'text-overflow:ellipsis">{name}</div>') if name else ""
    return (f'<div style="min-width:0;flex:1"><div style="font-size:14px;font-weight:600;color:{TEXT}">{t}{dot}</div>'
            f'{sub}</div>')


_ROW = f"display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid {BORDER};"

# Klikalne wiersze: karta = st.container(key="pulcard_*"), wiersz = st.container(key="pulrow_*")
# z HTML-em wiersza i przezroczystym st.buttonem rozciagnietym na caly wiersz. Nawigacja
# przez st.switch_page (bez przeladowania strony — sesja, Premium i Ulubione zostaja).
_CLICK_CSS = f"""<style>
[class*="st-key-pulcard_"] {{ background:{BG_CARD}; border-radius:14px; padding:4px 16px;
  box-shadow:{SHADOW}; gap:0; }}
[class*="st-key-pulcard_"] [data-testid="stHorizontalBlock"] {{ gap:16px; }}
.st-key-pulcard_mov {{ padding-top:12px; }}
[class*="st-key-pulcard_"] [data-testid="stColumn"] [data-testid="stVerticalBlock"] {{ gap:0; }}
[class*="st-key-pulrow_"] {{ position:relative; gap:0; }}
[class*="st-key-pulrow_"] .stElementContainer:has(.stButton) {{ position:absolute; inset:0; z-index:2; }}
[class*="st-key-pulrow_"] .stButton, [class*="st-key-pulrow_"] .stButton button {{
  width:100%; height:100%; min-height:0; }}
[class*="st-key-pulrow_"] .stButton button {{ background:transparent; border:none; color:transparent;
  border-radius:8px; padding:0; box-shadow:none; }}
[class*="st-key-pulrow_"] .stButton button:hover {{ background:rgba(255,255,255,.04); }}
[class*="st-key-pulrow_"] .stButton button:focus-visible {{ outline:1px solid {GOLD}; }}
[class*="st-key-pulrow_"] .stButton button p {{ color:transparent; }}
</style>"""


def _has_card(t: str) -> bool:
    """Karta spolki istnieje tylko dla S&P 500 i GPW (nie dla ETF-ow z Ulubionych)."""
    return t in SP500_NAMES or t in GPW_NAMES


def _click_rows(key: str, rows: list[tuple[str, str]]) -> None:
    """Wiersze (ticker, html); klik w wiersz spolki otwiera jej Karte spolki."""
    for i, (t, html) in enumerate(rows):
        with st.container(key=f"pulrow_{key}_{i}"):
            st.html(html)
            if _has_card(t) and st.button(tr("Otwórz kartę {ticker}", ticker=t), key=f"pulbtn_{key}_{i}_{t}",
                                          help=tr("Karta spółki {ticker}", ticker=t)):
                nav.go_company(t)


def render_watchlist(tickers, heading: str, empty_msg: str) -> None:
    """Karta z cena, zmiana dnia i sparkline 3M dla listy tickerow (Premium i Free)."""
    st.markdown(f"#### {heading}")
    tickers = sorted(tickers)
    if not tickers:
        st.caption(empty_msg)
        return
    rows = []
    for t in tickers[:10]:
        try:
            s = download_single(t, period="3mo")
            chg = ms.daily_change(s.to_frame(t)) if s is not None else pd.Series(dtype=float)
            if s is None or chg.empty:
                raise ValueError("no data")
            color = GREEN if s.iloc[-1] >= s.iloc[0] else RED
            spark = _sparkline_svg(s, color, height=24, fill=False)
            rows.append((t,
                f'<div style="{_ROW}">{_ticker_block(t)}'
                f'<div style="width:80px;flex:none">{spark}</div>'
                f'<div style="text-align:right;flex:none"><div style="font-size:14px;font-weight:600;color:{TEXT};'
                f'font-variant-numeric:tabular-nums">{s.iloc[-1]:,.2f}</div>'
                f'<div style="margin-top:2px">{_pill(float(chg.iloc[0]))}</div></div></div>'))
        except Exception:
            rows.append((t, f'<div style="{_ROW}"><div style="font-size:14px;font-weight:600;color:{TEXT}">{t}</div>'
                            f'<div style="font-size:12px;color:{MUTED}">{tr("brak danych")}</div></div>'))
    with st.container(key="pulcard_wl"):
        _click_rows("wl", rows)


def render_week_earnings(ls) -> None:
    st.markdown("#### " + tr("Wyniki w tym tygodniu"))
    wl = get_watchlist(ls)
    tickers = tuple(ms.pulpit_earnings_tickers(wl))
    df = bulk_fetch_earnings_calendar(tickers, window_days=7)
    if df is None or df.empty:
        st.caption(tr("Brak nadchodzących raportów w ciągu 7 dni dla watchlisty i największych spółek."))
        return
    df = df.assign(date=pd.to_datetime(df["date"]))
    today = pd.Timestamp.now().normalize()
    df = df[(df["date"] >= today) & (df["date"] <= today + pd.Timedelta(days=7))]
    if df.empty:
        st.caption(tr("Brak nadchodzących raportów w ciągu 7 dni dla watchlisty i największych spółek."))
        return
    # Najpierw spolki z watchlisty, w obu grupach chronologicznie
    df = (df.assign(_wl=~df["ticker"].isin(wl))
            .sort_values(["_wl", "date", "ticker"]).head(10))
    rows = []
    for _, r in df.iterrows():
        n = (r["date"].normalize() - today).days
        if n <= 0:
            status = (f'<span style="background:{GOLD_SOFT};color:{GOLD};font-size:12px;padding:2px 8px;'
                      f'border-radius:999px">{tr("dziś")}</span>')
        else:
            status = f'<span style="color:{MUTED};font-size:12px;white-space:nowrap">{days_label(n)}</span>'
        dot = (f'<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:{GOLD};'
               f'margin-left:6px;vertical-align:middle"></span>') if r["ticker"] in wl else ""
        rows.append((r["ticker"],
            f'<div style="{_ROW}">'
            f'<div style="width:40px;flex:none;text-align:center;background:{BG_HOVER};border-radius:8px;padding:4px 0">'
            f'<div style="font-size:16px;font-weight:600;color:{TEXT};line-height:1.2">{r["date"].day}</div>'
            f'<div style="font-size:11px;color:{MUTED}">{short_month_pl(r["date"])}</div></div>'
            f'{_ticker_block(r["ticker"], dot)}'
            f'<div style="flex:none">{status}</div></div>'))
    with st.container(key="pulcard_earn"):
        _click_rows("earn", rows)


def _movers_col(key: str, title: str, color: str, series: pd.Series) -> None:
    st.html(f'<div style="font-size:12px;font-weight:600;color:{color};padding:6px 0 2px">{title}</div>')
    _click_rows(key, [
        (t, f'<div style="display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid {BORDER}">'
            f'{_ticker_block(t)}{_pill(float(v))}</div>')
        for t, v in series.items()])


@st.fragment
def render_movers() -> None:
    # Sam naglowek (jedna linia jak w sasiednich kolumnach); przelacznik rynku jest
    # wewnatrz karty, wiec wszystkie trzy karty startuja na tej samej wysokosci.
    st.markdown("#### " + tr("Wygrani / przegrani"))
    card = st.container(key="pulcard_mov")
    with card:
        try:
            market = st.segmented_control("Rynek", ["S&P 500", "GPW"], default="S&P 500",
                                          key="mov_market", label_visibility="collapsed")
        except Exception:
            market = st.radio("Rynek", ["S&P 500", "GPW"], horizontal=True, key="mov_market_r",
                              label_visibility="collapsed")
    market = market or "S&P 500"
    universe = ALL_SP500_TICKERS if market == "S&P 500" else ALL_GPW_TICKERS
    with st.spinner(tr("Liczę zmiany {market}…", market=market)):
        try:
            gainers, losers = ms.top_movers(ms.market_movers(tuple(universe)), n=5)
        except Exception:
            unavailable(market)
            return
    if gainers.empty:
        unavailable(market)
        return
    with card:
        c_up, c_down = st.columns(2)
        with c_up:
            _movers_col("up", tr("Wzrosty"), GREEN, gainers)
        with c_down:
            _movers_col("down", tr("Spadki"), RED, losers)


# --- 5. Top 5 ETF + wyniki 5 lat ------------------------------------------------
def render_top_etf(prices: pd.DataFrame, rf: float):
    st.markdown("### " + tr("Top 5 ETF wg momentum"))
    names, cats = dict(ETF_NAMES), dict(ETF_CATEGORY_MAP)
    for t in st.session_state.get("custom_tickers", []):
        names.setdefault(t, t)
        cats.setdefault(t, "Wlasne")
    try:
        ranking = build_ranking(prices, rf, skip_month=False).dropna(subset=["Wynik"])
        if ranking.empty:
            unavailable(tr("Ranking ETF"))
        else:
            top_etf_cards(ranking, names, cats, n=5)
    except Exception:
        ranking = pd.DataFrame()
        unavailable(tr("Ranking ETF"))
    return ranking, names


def render_strategy_5y(rf: float):
    st.markdown("### " + tr("Wyniki strategii (5 lat)"))
    try:
        bt = backtest_gem(download_prices(["QQQ", "VEA", "EEM", "ACWI", "AGG"], period="7y"), rf)
    except Exception:
        unavailable(tr("Wyniki strategii"))
        return None
    if bt is None:
        st.info(tr("Za malo danych do backtestu GEM (wymagane 252+ sesji)."))
        return None
    show = {k: bt["stats"][k] for k in ("GEM", "QQQ B&H", "ACWI B&H", "AGG B&H") if k in bt["stats"]}
    if show:
        stats_table(show)
    return show


def render_pdf_export(gem_data, regime, sparks, ranking, names, show_stats) -> None:
    with st.expander(tr("Eksport raportu PDF"), icon=":material/picture_as_pdf:"):
        st.caption(tr("Wybierz sekcje do wlaczenia w raport"))
        pdf_gem = st.checkbox(tr("Sygnal GEM"), value=True, key="pdf_gem")
        pdf_regime = st.checkbox(tr("Regime rynkowy"), value=True, key="pdf_regime")
        pdf_top5 = st.checkbox(tr("Top 5 ETF-ow"), value=True, key="pdf_top5")
        pdf_sparks = st.checkbox(tr("Kluczowe aktywa"), value=True, key="pdf_sparks")
        pdf_bt = st.checkbox(tr("Statystyki strategii"), value=True, key="pdf_bt")
        pdf_rank = st.checkbox(tr("Ranking ETF top 10"), value=True, key="pdf_rank")
        if not st.button(tr("Generuj raport PDF"), key="pdf_gen_btn"):
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
            st.download_button(tr("Pobierz PDF"), data=generate_report(sections),
                               file_name=f"gem_raport_{pd.Timestamp.now():%Y%m%d}.pdf",
                               mime="application/pdf")
        else:
            st.warning(tr("Wybierz co najmniej jedna sekcje."))


# =============================================================================
_now = pd.Timestamp.now()
st.markdown(f"# {greeting(_now)}")
st.caption(f"{date_pl(_now, weekday=True)} · " + tr("dane z zamknięcia ostatniej sesji"))
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

st.markdown(_CLICK_CSS, unsafe_allow_html=True)
_favs = set(st.session_state.get("favorites", set()))
# Caly Pulpit jest darmowy (decyzja 2026-11-18): watchlista, wyniki tygodnia,
# wygrani/przegrani i eksport PDF bez kodu Premium.
ls = LocalStorage()
try:
    _wl = get_watchlist(ls) | _favs
except Exception:
    _wl = _favs
# Pusta watchlista idzie na koniec wiersza; z co najmniej jedna spolka — na poczatek.
if _wl:
    col_wl, col_earn, col_mov = st.columns(3)
else:
    col_earn, col_mov, col_wl = st.columns(3)
with col_wl:
    try:
        render_watchlist(
            _wl,
            tr("Moja watchlista"),
            tr("Pusta. Dodaj spółki gwiazdką ⭐ w S&P 500 / GPW albo w sidebarze (Ulubione)."))
    except Exception:
        unavailable(tr("Watchlista"))
with col_earn:
    try:
        render_week_earnings(ls)
    except Exception:
        unavailable(tr("Wyniki w tym tygodniu"))
mov_slot = col_mov.container()

st.divider()
ranking, names = render_top_etf(prices, rf)

show_stats = render_strategy_5y(rf)
render_pdf_export(gem_data, regime, sparks, ranking, names, show_stats)

# Ciezkie pobieranie ~600 spolek na koncu — nie blokuje reszty strony
with mov_slot:
    render_movers()

with st.expander(tr("Status danych")):
    try:
        data_status_card()
    except Exception:
        unavailable(tr("Status danych"))

render_footer()
