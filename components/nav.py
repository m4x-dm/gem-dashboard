"""Rejestr stron GEM Dashboard — jedyne zrodlo prawdy o nawigacji.

Nowa strona = plik w views/<sekcja>/ + jeden wpis w PAGES.
Adres URL = nazwa pliku (bez url_path) — wymagane przez AppTest.switch_page,
ktory liczy hash strony z nazwy pliku. Dlatego nazwy plikow musza byc unikalne.
Router (app.py) buduje z tego st.navigation i bramke Premium.
"""
from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class PageDef:
    key: str
    path: str
    title: str
    icon: str
    section: str          # "" = link bezposredni w gornym menu
    free: bool
    description: str
    default: bool = False


# Kolejnosc sekcji w gornym menu. "" = linki bezposrednie (tylko Pulpit) —
# st.navigation zawsze stawia je na poczatku. Krypto ma wlasna sekcje,
# zeby byc na koncu menu (decyzja uzytkownika 2026-11-15).
SECTION_ORDER = ["", "Strategia GEM", "ETF", "Spółki", "Portfel", "Rynek", "Krypto"]

PAGES: list[PageDef] = [
    # --- Start ---
    PageDef("pulpit", "views/start/pulpit.py", "Pulpit", ":material/dashboard:", "", True,
            "Centrum dowodzenia: sygnal GEM, regime, rynek, watchlista, wyniki tygodnia", default=True),
    # --- Strategia GEM ---
    PageDef("sygnal", "views/strategia/sygnal.py", "Sygnał GEM", ":material/track_changes:", "Strategia GEM", True,
            "Aktualny sygnal GEM, top 5 ETF oraz pelna historia zmian sygnalu"),
    PageDef("backtest", "views/strategia/backtest.py", "Backtest", ":material/science:", "Strategia GEM", False,
            "GEM vs Buy&Hold — krzywa kapitalu, Sharpe, MDD i wiecej"),
    PageDef("gem-extended", "views/strategia/gem_extended.py", "GEM Extended", ":material/rocket_launch:", "Strategia GEM", False,
            "Backtest GEM z dowolnym universe (do 10 ETF + krypto), top N equal-weight"),
    PageDef("gem-zloto", "views/strategia/gem_zloto.py", "GEM Gold Momentum", ":material/workspace_premium:", "Strategia GEM", False,
            "Momentum ze zlotem w wersji GEM: Nasdaq-100 / zloto / obligacje, backtest od 2005 vs GEM klasyczny"),
    PageDef("o-strategii", "views/strategia/o_strategii.py", "O strategii", ":material/menu_book:", "Strategia GEM", True,
            "Opis strategii GEM Gary'ego Antonacciego"),
    # --- ETF ---
    PageDef("ranking-etf", "views/etf/ranking.py", "Ranking momentum", ":material/leaderboard:", "ETF", True,
            "Tabela rankingowa 30+ ETF-ow z wynikiem momentum"),
    PageDef("porownaj", "views/etf/porownaj.py", "Porównaj", ":material/compare_arrows:", "ETF", False,
            "Wykresy, head-to-head 2–4 ETF-ow z korelacjami oraz side-by-side dwoch aktywow"),
    PageDef("stopy-zwrotu", "views/etf/stopy_zwrotu.py", "Stopy zwrotu", ":material/percent:", "ETF", False,
            "Stopy zwrotu ETF-ow do 30 lat: okresy, lata, okna kroczace, PLN i proxy"),
    PageDef("drawdowny", "views/etf/drawdowny.py", "Drawdowny", ":material/trending_down:", "ETF", False,
            "Analiza spadkow od szczytu — glebokosc, czas trwania, odbudowa"),
    # --- Spolki ---
    PageDef("karta", "views/spolki/karta.py", "Karta spółki", ":material/badge:", "Spółki", True,
            "Jedna spolka: przeglad, finanse, wyniki, akcjonariat, dywidendy, konkurencja"),
    PageDef("sp500", "views/spolki/sp500.py", "S&P 500", ":material/flag:", "Spółki", False,
            "Ranking, wykresy, sprawozdania (screener) i backtest ~500 spolek z indeksu S&P 500"),
    PageDef("gpw", "views/spolki/gpw.py", "GPW", ":material/flag:", "Spółki", False,
            "140 spolek z WIG20, mWIG40 i sWIG80 — momentum, sprawozdania (screener) i backtest"),
    PageDef("top-picks", "views/spolki/top_picks.py", "Top Picks", ":material/star:", "Spółki", False,
            "Trzy miesieczne piatki spolek: momentum cenowe, jakosc wynikow kwartalnych i jakosc biznesu"),
    PageDef("screener", "views/spolki/screener.py", "Screener", ":material/filter_alt:", "Spółki", False,
            "Cross-asset ranking momentum ze wszystkich klas aktywow"),
    PageDef("kalendarz-wynikow", "views/spolki/kalendarz_wynikow.py", "Kalendarz wyników", ":material/event:", "Spółki", False,
            "Kalendarz nadchodzacych i niedawnych raportow SP500 + GPW (±28 dni) z watchlista"),
    PageDef("insiderzy", "views/spolki/insiderzy.py", "Insiderzy", ":material/groups:", "Spółki", False,
            "Bulk insider activity SP500 — top kupujacy/sprzedajacy, sektory"),
    # --- Portfel ---
    PageDef("portfolio-builder", "views/portfel/portfolio_builder.py", "Portfolio Builder", ":material/pie_chart:", "Portfel", False,
            "Zbuduj portfel, ustaw wagi, backtest i analiza korelacji"),
    PageDef("monte-carlo", "views/portfel/monte_carlo.py", "Monte Carlo", ":material/casino:", "Portfel", False,
            "Symulacja przyszlych zwrotow — ile mozesz miec za N lat?"),
    # --- Rynek ---
    PageDef("makro", "views/rynek/makro.py", "Makro", ":material/public:", "Rynek", False,
            "VIX, yield curve, DXY, S&P+200MA, zloto, ropa"),
    PageDef("sektory", "views/rynek/sektory.py", "Rotacja sektorowa", ":material/donut_large:", "Rynek", False,
            "Ktory sektor GICS prowadzi? Heatmapa momentum sektorow"),
    PageDef("intermarket", "views/rynek/intermarket.py", "Intermarket", ":material/hub:", "Rynek", False,
            "Relacje miedzy klasami aktywow: akcje, obligacje, zloto, dolar"),
    PageDef("sezonowosc", "views/rynek/sezonowosc.py", "Sezonowość", ":material/calendar_month:", "Rynek", False,
            "Heatmapa miesiecznych zwrotow i wzorce sezonowe"),
    PageDef("waluta", "views/rynek/waluta.py", "Waluta PLN/USD", ":material/currency_exchange:", "Rynek", False,
            "Wplyw kursu USD/PLN na zwroty ETF-ow w zlotowkach"),
    # --- Krypto (ostatnia sekcja w menu) ---
    PageDef("krypto", "views/krypto/kryptowaluty.py", "Kryptowaluty", ":material/currency_bitcoin:", "Krypto", False,
            "Top 200 kryptowalut — ranking, alt/BTC ratio, backtest"),
]

_BY_KEY = {p.key: p for p in PAGES}
_BY_PATH = {p.path: p for p in PAGES}
_BY_TITLE = {p.title: p for p in PAGES}


def get(key: str) -> PageDef:
    return _BY_KEY[key]


def by_path(path: str) -> PageDef | None:
    return _BY_PATH.get(path.replace("\\", "/"))


def by_title(title: str) -> PageDef | None:
    """Router identyfikuje biezaca strone po tytule (st.Page nie udostepnia sciezki)."""
    return _BY_TITLE.get(title)


def access_info(title: str) -> tuple[bool, str, str, str]:
    """(free, icon, title, description). Nieznana strona = zamknieta (fail closed)."""
    page = _BY_TITLE.get(title)
    if page is None:
        return False, ":material/lock:", title, "Ta strona wymaga dostępu Premium."
    return page.free, page.icon, page.title, page.description


def build_navigation() -> dict[str, list]:
    """Sekcje dla st.navigation — kolejnosc wg SECTION_ORDER, strony wg PAGES."""
    sections: dict[str, list] = {name: [] for name in SECTION_ORDER}
    for p in PAGES:
        sections[p.section].append(
            st.Page(p.path, title=p.title, icon=p.icon, default=p.default)
        )
    return {name: pages for name, pages in sections.items() if pages}


def go(key: str) -> None:
    """Przejscie na strone po kluczu (zamiast twardej sciezki w st.switch_page)."""
    st.switch_page(get(key).path)


def link(key: str, label: str | None = None, **kwargs) -> None:
    p = get(key)
    st.page_link(p.path, label=label or p.title, icon=p.icon, **kwargs)


def go_company(ticker: str) -> None:
    """Otwiera Karte spolki dla tickera (ticker w adresie: ?t=...)."""
    st.switch_page(get("karta").path, query_params={"t": ticker})


def company_link(ticker: str, label: str | None = None, **kwargs) -> None:
    p = get("karta")
    st.page_link(p.path, label=label or ticker, query_params={"t": ticker}, **kwargs)
