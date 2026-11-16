"""Karta spolki — zakladka Przeglad (free): wykres, kluczowe dane, analitycy, kalendarz, momentum GEM."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.cards import card_html
from components.charts import _base_layout
from components.constants import TEXT, MUTED, GOLD, GREEN, RED, BG_HOVER, BORDER
from components.sidebar import get_risk_free
from data import company as co
from data import downloader as dl
from data import financials as fin
from data.gpw_universe import GPW_BANKS, ALL_GPW_TICKERS
from data.sp500_universe import ALL_SP500_TICKERS

PERIODS = {"1M": "1mo", "6M": "6mo", "1R": "1y", "5L": "5y", "Max": "max"}
REC_PL = {"strong_buy": "Kupuj", "buy": "Kupuj", "hold": "Trzymaj", "sell": "Sprzedaj",
          "underperform": "Sprzedaj", "strong_sell": "Sprzedaj"}
NUM = "font-variant-numeric:tabular-nums;"


def _ok(x) -> bool:
    try:
        return x is not None and bool(np.isfinite(float(x)))
    except (TypeError, ValueError):
        return False


def _num(x, d=1) -> str:
    return f"{float(x):,.{d}f}".replace(",", " ").replace(".", ",") if _ok(x) else "—"


def _pct(x, d=1, sign=True) -> str:
    if not _ok(x):
        return "—"
    if sign:
        return f"{float(x):+.{d}f}%".replace(".", ",")
    return f"{float(x):.{d}f}%".replace(".", ",")


def _big(x, ccy) -> str:
    if not _ok(x):
        return "—"
    x = float(x)
    for lim, name in ((1e12, "bln"), (1e9, "mld"), (1e6, "mln")):
        if abs(x) >= lim:
            return f"{_num(x / lim, 1)} {name} {ccy}"
    return f"{_num(x, 0)} {ccy}"


def _lbl(t: str) -> str:
    return f'<div style="color:{MUTED};font-size:12px;margin-bottom:6px">{t}</div>'


def _kv(rows) -> str:
    out = ""
    for k, v in rows:
        out += (f'<div style="display:flex;justify-content:space-between;gap:10px;padding:4px 0">'
                f'<span style="color:{MUTED}">{k}</span><span style="color:{TEXT};{NUM}">{v}</span></div>')
    return out


def _marker(left, color, w=3, h=14, top=-4) -> str:
    left = min(max(left, 0), 100)
    return (f'<i style="position:absolute;left:{left:.0f}%;top:{top}px;width:{w}px;height:{h}px;'
            f'border-radius:2px;background:{color}"></i>')


def _bar(markers: str) -> str:
    return (f'<div style="height:6px;background:{BORDER};border-radius:99px;position:relative;'
            f'margin:10px 0 6px">{markers}</div>')


def _chart(ticker, ccy):
    rng = st.segmented_control("Okres", list(PERIODS), default="1R", key="kov_range",
                               label_visibility="collapsed") or "1R"
    s = dl.download_single(ticker, period=PERIODS[rng])
    if s is None:
        st.caption("Wykres: brak danych")
        return
    s = s.replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < 2:
        st.caption("Wykres: brak danych")
        return
    up = s.iloc[-1] >= s.iloc[0]
    col = GREEN if up else RED
    fig = go.Figure(go.Scatter(
        x=s.index, y=s, mode="lines", line=dict(color=col, width=1.8),
        hovertemplate="%{x|%d.%m.%Y}<br>%{y:,.2f} " + ccy + "<extra></extra>"))
    fig.update_layout(**_base_layout(height=320))
    fig.update_yaxes(range=[float(s.min()) * 0.97, float(s.max()) * 1.03])
    st.plotly_chart(fig, key="kov_price", width="stretch")


def _key_data(ticker, market, ccy):
    snap = fin.get_ratios_snapshot(ticker) or {}
    prof = co.company_profile(ticker) or {}
    rows = [("Kapitalizacja", _big(snap.get("market_cap"), ccy)),
            ("P/E · Forward P/E", f'{_num(snap.get("pe"))} · {_num(snap.get("fwd_pe"))}')]
    if market == "GPW" and ticker in GPW_BANKS:
        rows.append(("P/B", _num(snap.get("price_to_book"), 2)))
    else:
        rows.append(("EV/EBITDA", _num(snap.get("ev_ebitda"))))
    y = co._norm_yield(snap.get("dividend_yield"))
    rows.append(("Stopa dywidendy", _pct(y * 100, 2, sign=False) if _ok(y) else "—"))
    rows.append(("Beta", _num(prof.get("beta"), 2)))
    html = _kv(rows)
    lo, hi, px = prof.get("low52"), prof.get("high52"), snap.get("current_price")
    if _ok(lo) and _ok(hi) and float(lo) > 0 and float(hi) > float(lo):
        html += (f'<div style="color:{MUTED};margin-top:6px;{NUM}">Zakres 52 tyg.: '
                 f'{_num(lo, 0)} – {_num(hi, 0)} {ccy}</div>')
        if _ok(px):
            html += _bar(_marker((float(px) - float(lo)) / (float(hi) - float(lo)) * 100, TEXT))
    st.html(card_html(html, extra="font-size:13px;"))


def _analysts(ticker, ccy):
    r = fin.get_analyst_recos(ticker) or {}
    if not r:
        st.html(card_html(_lbl("Analitycy") + f'<span style="color:{MUTED}">Brak pokrycia analityków</span>',
                          extra="min-height:144px;"))
        return
    key = REC_PL.get((r.get("recommendation_key") or "").lower(), "—")
    col = GREEN if key == "Kupuj" else RED if key == "Sprzedaj" else MUTED
    n = r.get("num_analysts") or 0
    html = _lbl(f'Analitycy ({n}) · <span style="color:{col}">{key}</span>')
    tm, up = r.get("target_mean"), r.get("upside_pct")
    if _ok(tm):
        upc = GREEN if _ok(up) and up >= 0 else RED
        html += (f'<div style="color:{TEXT};{NUM}">Cel średni <b>{_num(tm, 0)} {ccy}</b> '
                 f'<span style="color:{upc}">{_pct(up)}</span></div>')
    lo, hi, px = r.get("target_low"), r.get("target_high"), r.get("current_price")
    if _ok(lo) and _ok(hi) and _ok(px) and float(hi) > float(lo):
        lo, hi, px = float(lo), float(hi), float(px)
        lo_b, hi_b = min(lo, px), max(hi, px)

        def pos(v):
            return (v - lo_b) / (hi_b - lo_b) * 100

        m = _marker(pos(lo), MUTED) + _marker(pos(px), TEXT) + _marker(pos(hi), MUTED)
        if _ok(tm):
            m += _marker(pos(float(tm)), GOLD)
        html += _bar(m) + (f'<div style="color:{MUTED};font-size:11px;{NUM}">min {_num(lo, 0)} · cena · '
                           f'cel · max {_num(hi, 0)}</div>')
    st.html(card_html(html, extra="min-height:144px;font-size:13px;"))


def _calendar(ticker):
    rows = []
    ed = fin.fetch_earnings_dates(ticker)
    nxt = None
    if ed is not None and len(ed) and "is_future" in ed.columns:
        fut = ed[ed["is_future"].astype(bool)]
        if len(fut):
            nxt = pd.Timestamp(fut.index.min())
    rows.append(("Następne wyniki", nxt.strftime("%d.%m.%Y") if nxt is not None else "—"))
    dv = co.dividend_history(ticker)
    if dv is not None and len(dv.dropna()):
        rows.append(("Dywidenda (ex)", pd.Timestamp(dv.dropna().index[-1]).strftime("%d.%m.%Y")))
    else:
        rows.append(("Dywidenda (ex)", "—"))
    bm = "—"
    try:
        eh = fin.get_earnings_history(ticker, n_quarters=1)
        if eh is not None and len(eh) and _ok(eh["surprise_pct"].iloc[-1]):
            sp = float(eh["surprise_pct"].iloc[-1])
            bm = f'<span style="color:{GREEN if sp >= 0 else RED}">{"Beat" if sp >= 0 else "Miss"} {_pct(sp)}</span>'
    except Exception:
        pass
    rows.append(("Ostatni beat/miss", bm))
    st.html(card_html(_lbl("Kalendarz") + _kv(rows), extra="min-height:144px;font-size:13px;"))


@st.fragment
def _momentum_fragment(ticker, market):
    try:
        universe = ALL_SP500_TICKERS if market == "SP500" else ALL_GPW_TICKERS
        label = "S&P 500" if market == "SP500" else "GPW"
        prices = co.universe_prices(tuple(universe), "2y")
        prof = co.momentum_profile(ticker, prices, get_risk_free())
        if not prof:
            html = _lbl("Momentum GEM") + f'<span style="color:{MUTED}">Za krótka historia notowań</span>'
        else:
            tiles = ""
            for k, name in (("r1m", "1M"), ("r3m", "3M"), ("r6m", "6M"), ("r12m", "12M")):
                v = prof.get(k)
                c = GREEN if _ok(v) and v >= 0 else RED
                val = _pct(v * 100) if _ok(v) else "—"
                tiles += (f'<div style="background:{BG_HOVER};border-radius:10px;padding:8px 4px;text-align:center">'
                          f'<div style="color:{MUTED};font-size:11px">{name}</div>'
                          f'<b style="color:{c};font-size:12px;{NUM}">{val}</b></div>')
            html = (_lbl(f'Momentum GEM · #{prof["rank"]} z {prof["of"]} w {label}') +
                    f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px">{tiles}</div>')
        st.html(card_html(html, extra="min-height:144px;font-size:13px;"))
    except Exception:
        st.caption("Momentum GEM: dane chwilowo niedostępne")


def _about(ticker):
    s = (co.company_profile(ticker) or {}).get("summary")
    if not s:
        return
    short = s if len(s) <= 300 else s[:300].rsplit(" ", 1)[0] + "…"
    st.html(card_html(_lbl("O spółce") + f'<span style="color:{MUTED};font-size:13px;line-height:1.5">{short}</span>'))
    if len(s) > 300:
        with st.expander("Rozwiń opis"):
            st.write(s)


def _safe(name, fn, *a):
    try:
        fn(*a)
    except Exception:
        st.caption(f"{name}: dane chwilowo niedostępne")


def render(ticker, market):
    ccy = "zł" if market == "GPW" else "$"
    c_chart, c_kv = st.columns([2, 1])
    with c_chart:
        _safe("Wykres", _chart, ticker, ccy)
    with c_kv:
        _safe("Kluczowe dane", _key_data, ticker, market, ccy)
    c1, c2, c3 = st.columns(3)
    mov_slot = c1.container()
    with c2:
        _safe("Analitycy", _analysts, ticker, ccy)
    with c3:
        _safe("Kalendarz", _calendar, ticker)
    _safe("O spółce", _about, ticker)
    with mov_slot:
        _momentum_fragment(ticker, market)
