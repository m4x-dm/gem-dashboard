"""Karta spolki — jedna spolka (S&P 500 / GPW), ticker w adresie ?t=TICKER."""
import streamlit as st

from components.auth import is_premium, premium_teaser
from components.company import header
from components.sidebar import render_footer
from data.financials import _detect_market
from data.gpw_universe import GPW_NAMES
from data.sp500_universe import SP500_NAMES

TABS = ["Przegląd", "Finanse", "Wyniki", "Akcjonariat", "Dywidendy", "Konkurencja"]
TEASERS = {
    "Finanse": "Wskaźniki, konsensus EPS, historia wyników i rekomendacje analityków.",
    "Wyniki": "Wyniki kwartalne vs prognozy, rachunek zysków i strat, bilans, przepływy.",
    "Akcjonariat": "Główni akcjonariusze, fundusze, transakcje insiderów.",
    "Dywidendy": "Historia wypłat, stopa, wzrost dywidendy i kalkulator dochodu po podatku.",
    "Konkurencja": "Porównanie wskaźników z 5 najbliższymi spółkami z sektora.",
}
SLUGS = {"Przegląd": "przeglad", "Finanse": "finanse", "Wyniki": "wyniki",
         "Akcjonariat": "akcjonariat", "Dywidendy": "dywidendy", "Konkurencja": "konkurencja"}
BY_SLUG = {v: k for k, v in SLUGS.items()}
NAMES = {**SP500_NAMES, **GPW_NAMES}


def _on_pick():
    t = st.session_state.get("karta_search")
    if t:
        st.query_params["t"] = t


def _search(current: str | None) -> None:
    options = [""] + sorted(NAMES, key=lambda t: NAMES[t])
    if st.session_state.get("karta_search") != (current or ""):
        st.session_state["karta_search"] = current if current in options else ""
    st.selectbox("Szukaj spółki (S&P 500 i GPW)", options,
                 key="karta_search", on_change=_on_pick,
                 format_func=lambda t: "Wpisz nazwę lub ticker…" if not t else f"{t} — {NAMES[t]}")


def _on_tab():
    sel = st.session_state.get("karta_tab") or "Przegląd"
    if sel == "Przegląd":
        st.query_params.pop("tab", None)
    else:
        st.query_params["tab"] = SLUGS[sel]


def _section() -> str:
    """Wybor sekcji — renderujemy tylko ja (st.tabs wykonywal wszystkie 6 naraz).
    Zrodlem prawdy jest ?tab= w adresie; stan widgetu ustawiamy PRZED jego utworzeniem."""
    want = BY_SLUG.get((st.query_params.get("tab") or "").lower().strip(), "Przegląd")
    if st.session_state.get("karta_tab") != want:
        st.session_state["karta_tab"] = want
    sel = st.segmented_control("Sekcja", TABS, key="karta_tab", on_change=_on_tab,
                               label_visibility="collapsed")
    return sel or "Przegląd"


def _render_tab(name: str, ticker: str, market: str) -> None:
    from components.company import overview, finance, results, ownership, dividends, peers
    mod = {"Przegląd": overview, "Finanse": finance, "Wyniki": results,
           "Akcjonariat": ownership, "Dywidendy": dividends, "Konkurencja": peers}[name]
    try:
        mod.render(ticker, market)
    except Exception:
        st.caption(f"{name}: dane chwilowo niedostępne")


ticker = (st.query_params.get("t") or "").upper().strip() or None
if ticker and ticker not in NAMES and f"{ticker}.WA" in NAMES:
    ticker = f"{ticker}.WA"
st.markdown("# Karta spółki")
_search(ticker)

if ticker is None:
    st.caption("Wybierz spółkę, aby zobaczyć jej kartę.")
elif ticker not in NAMES:
    st.warning(f"Nie znaleziono spółki {ticker} w S&P 500 ani na GPW.")
else:
    market = _detect_market(ticker)
    header.render(ticker, market)
    name = _section()
    if name == "Przegląd" or is_premium():
        _render_tab(name, ticker, market)
    else:
        premium_teaser(name, TEASERS[name])

render_footer()
