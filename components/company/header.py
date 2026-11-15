"""Naglowek karty spolki: ticker, nazwa, sektor, gielda, cena + zmiana dnia, watchlista."""
import streamlit as st

from components.auth import is_premium
from components.constants import TEXT, MUTED, GREEN, RED
from data import company as co
from data import downloader
from data.gpw_universe import GPW_NAMES
from data.sp500_universe import SP500_NAMES

EXCHANGE = {"SP500": "NYSE / NASDAQ", "GPW": "GPW"}


def company_name(ticker: str, market: str) -> str:
    return (GPW_NAMES if market == "GPW" else SP500_NAMES).get(ticker, ticker)


def _watchlist_button(ticker: str) -> None:
    if not is_premium():
        st.caption("Watchlista w Premium")
        return
    from streamlit_local_storage import LocalStorage
    from components.watchlist import get_watchlist, toggle_ticker

    ls = LocalStorage()
    label = "Usuń z watchlisty" if ticker in get_watchlist(ls) else "Dodaj do watchlisty"
    if st.button(label, key="karta_wl"):
        toggle_ticker(ls, ticker)
        st.rerun()


def render(ticker: str, market: str) -> None:
    s = downloader.download_single(ticker, period="1y")
    price = chg = None
    if s is not None and len(s.dropna()) >= 2:
        s = s.dropna()
        price, chg = float(s.iloc[-1]), float(s.iloc[-1] / s.iloc[-2] - 1)
    ccy = "zł" if market == "GPW" else "$"
    sector = co.sector_of(ticker, market) or ""
    pill = ""
    if chg is not None:
        col, bg = (GREEN, "rgba(52,211,153,.12)") if chg >= 0 else (RED, "rgba(248,113,113,.12)")
        pill = (f'<span style="background:{bg};color:{col};padding:2px 9px;border-radius:999px;'
                f'font-size:12px">{chg*100:+.2f}% dziś</span>')
    price_txt = f"{price:,.2f} {ccy}".replace(",", " ").replace(".", ",") if price is not None else "—"
    meta = " · ".join(x for x in (company_name(ticker, market), sector, EXCHANGE[market]) if x)
    st.html(
        f'<div style="display:flex;align-items:flex-end;gap:16px;margin:4px 0 10px">'
        f'<div><div style="font-size:26px;font-weight:700;color:{TEXT}">{ticker}</div>'
        f'<div style="color:{MUTED};font-size:14px">{meta}</div></div>'
        f'<div style="margin-left:auto;text-align:right"><div style="font-size:26px;font-weight:650;'
        f'color:{TEXT};font-variant-numeric:tabular-nums">{price_txt}</div>{pill}</div></div>'
    )
    _watchlist_button(ticker)
