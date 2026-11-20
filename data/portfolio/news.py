"""Newsy o spolkach z portfela: Yahoo Search (USA/Europa), Google News RSS i ESPI z Bankiera (GPW).

Spec: docs/superpowers/specs/2026-11-20-moj-portfel-newsy-design.md
Parsery sa czyste (testy offline na probkach); pobieranie jest cienkie i wstrzykiwane do collect().
`yf.Ticker(t).news` jest zepsute (2026-11-20: "YAHOO! FINANCE IS CURRENTLY DOWN") — uzywamy yf.Search.
"""
from __future__ import annotations

import html
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Callable
from urllib.parse import quote

import pandas as pd

WINDOW_DAYS = 14
MIN_YAHOO_HITS = 3                 # mniej -> drugie wyszukiwanie po nazwie spolki (np. NOW -> ServiceNow)
BLOCKED_SOURCES = ("xtb.com",)     # strony reklamowe brokera ("Inwestuj w akcje X - XTB.com")
# Notowania udajace newsy (Stooq: "SNT (+3.21%) - Synektik SA")
QUOTE_TITLE = re.compile(r"^[A-Z0-9.]{2,10} \([+\-]?[\d.,]+%\)")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"}


class NewsParseError(Exception):
    """Odpowiedz bez oczekiwanej struktury (np. zmieniony HTML strony Bankiera)."""


@dataclass
class NewsItem:
    date: pd.Timestamp
    ticker: str
    title: str
    link: str
    source: str
    kind: str = "news"             # "news" | "espi"


def _is_gpw(ticker: str) -> bool:
    return ticker.upper().endswith(".WA")


def base_symbol(ticker: str) -> str:
    """ASML.AS -> ASML, SNT.WA -> SNT, META -> META (klasy akcji z myslnikiem zostaja)."""
    return ticker.split(".")[0] if "." in ticker else ticker


# --------------------------------------------------------------------------- parsery

def parse_yahoo(items: list[dict] | None, symbol: str) -> list[NewsItem]:
    out = []
    for it in items or []:
        if symbol not in (it.get("relatedTickers") or []):
            continue
        ts = it.get("providerPublishTime")
        if not ts or not it.get("title") or not it.get("link"):
            continue
        out.append(NewsItem(pd.Timestamp(int(ts), unit="s"), symbol, str(it["title"]).strip(),
                            str(it["link"]), str(it.get("publisher") or "Yahoo Finance")))
    return out


_RSS_ITEM = re.compile(r"<item>(.*?)</item>", re.S)


def _tag(block: str, name: str) -> str:
    m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", block, re.S)
    if not m:
        return ""
    v = m.group(1).strip()
    if v.startswith("<![CDATA["):
        v = v[9:-3]
    return html.unescape(v).strip()


def parse_google_rss(xml: str, name: str, ticker: str) -> list[NewsItem]:
    """Google News RSS: nazwa spolki musi byc w tytule; odrzucone strony reklamowe brokera."""
    out = []
    want = name.lower()
    for block in _RSS_ITEM.findall(xml or ""):
        title, source = _tag(block, "title"), _tag(block, "source")
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3].rstrip()
        elif " - " in title:
            title = title.rsplit(" - ", 1)[0].rstrip()
        if want not in title.lower():
            continue
        if QUOTE_TITLE.match(title):
            continue
        if any(b in source.lower() or title.lower().endswith(b) for b in BLOCKED_SOURCES):
            continue
        try:
            dt = parsedate_to_datetime(_tag(block, "pubDate"))
            date = pd.Timestamp(dt).tz_convert("UTC").tz_localize(None)
        except (TypeError, ValueError):
            continue
        out.append(NewsItem(date, ticker, title, _tag(block, "link"), source or "Google News"))
    return out


_BANKIER_ITEM = re.compile(
    r'm-quotes-announcements-item__date">\s*([\d.]+\s+[\d:]+)\s*</span>\s*'
    r'<a[^>]*class="m-quotes-announcements-item__anchor"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)


def _page_title(page: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", page or "", re.S | re.I)
    return html.unescape(m.group(1)).strip()[:80] if m else ""


def parse_bankier(page: str, ticker: str) -> list[NewsItem]:
    """Lista komunikatow ESPI ze strony spolki na Bankierze."""
    if "m-quotes-announcements" not in (page or ""):
        # Tytul strony w bledzie: odroznia ekran zgody / blokade od zmiany ukladu (diagnostyka na Cloud)
        raise NewsParseError(f"brak listy komunikatów w HTML ({len(page or '')} zn., "
                             f"tytuł: {_page_title(page) or '—'})")
    out = []
    for date, link, title in _BANKIER_ITEM.findall(page):
        try:
            ts = pd.to_datetime(date.strip(), format="%d.%m.%Y %H:%M")
        except ValueError:
            continue
        out.append(NewsItem(ts, ticker, html.unescape(re.sub(r"<[^>]+>", "", title)).strip(), link, "ESPI", "espi"))
    return out


# --------------------------------------------------------------------------- pobieranie

def fetch_yahoo(query: str) -> list[dict]:
    import yfinance as yf
    from data.financials import _get_yf_session
    return yf.Search(query, news_count=20, session=_get_yf_session()).news or []


def fetch_google(name: str, lang: str = "pl") -> str:
    import requests
    region = "hl=pl&gl=PL&ceid=PL:pl" if lang == "pl" else "hl=en-US&gl=US&ceid=US:en"
    url = (f"https://news.google.com/rss/search?q={quote(chr(34) + name + chr(34))}+when:{WINDOW_DAYS}d"
           f"&{region}")
    r = requests.get(url, timeout=15, headers=UA)
    r.raise_for_status()
    return r.text


def fetch_bankier(symbol: str) -> str:
    import requests
    r = requests.get(f"https://www.bankier.pl/gielda/notowania/akcje/{quote(symbol)}/komunikaty",
                     timeout=15, headers=UA)
    r.raise_for_status()
    return r.text


# --------------------------------------------------------------------------- zbieranie

def _norm(title: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", title.lower()).split())


def dedupe(items: list[NewsItem]) -> list[NewsItem]:
    seen, out = set(), []
    for it in items:
        key = (it.ticker, _norm(it.title))
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def merge_across_tickers(items: list[NewsItem]) -> list[tuple[NewsItem, list[str]]]:
    """Ten sam artykul dla kilku spolek (np. META i SPCX) -> jeden wiersz z lista tickerow."""
    out: list[tuple[NewsItem, list[str]]] = []
    index: dict[str, int] = {}
    for it in items:
        key = _norm(it.title)
        if key in index:
            tickers = out[index[key]][1]
            if it.ticker not in tickers:
                tickers.append(it.ticker)
            continue
        index[key] = len(out)
        out.append((it, [it.ticker]))
    return out


def collect(rows: list[tuple[str, str]], today: pd.Timestamp,
            fetch_yahoo: Callable = fetch_yahoo, fetch_google: Callable = fetch_google,
            fetch_bankier: Callable = fetch_bankier, max_workers: int = 6,
            details: dict | None = None) -> tuple[list[NewsItem], dict]:
    """rows = [(ticker Yahoo, nazwa spolki)] -> (newsy z 14 dni malejaco, status zrodel per spolka).

    details (opcjonalny slownik do wypelnienia): {ticker: {zrodlo: opis}} — przy bledzie typ wyjatku
    i komunikat, przy pustym wyniku ile surowych wynikow odrzucil filtr (diagnostyka na Streamlit Cloud).
    """

    def one(row):
        ticker, name = row
        items, st_, det = [], {}, {}
        raw = {}                                     # ile surowych wynikow przed filtrem (diagnostyka)

        def run(key, fn):
            try:
                got = fn()
            except Exception as exc:
                st_[key] = "error"
                det[key] = f"{type(exc).__name__}: {str(exc)[:140]}"
                return []
            st_[key] = "ok" if got else "empty"
            if not got:
                det[key] = f"0 pasujących z {raw.get(key, 0)} wyników"
            return got

        def google():
            xml = fetch_google(name)
            raw["google"] = xml.count("<item>")
            return parse_google_rss(xml, name, ticker)

        def espi():
            # Bankier odpowiada 403 serwerom Streamlit Cloud -> najpierw dzienny zrzut z GitHub Actions.
            from data import fundamentals_snapshot as fs
            hit, df = fs.lookup("espi", ticker)
            if hit:
                got = [] if df is None else [NewsItem(d, ticker, str(r["title"]), str(r["link"]), "ESPI", "espi")
                                             for d, r in df.iterrows()]
            else:
                got = parse_bankier(fetch_bankier(base_symbol(ticker)), ticker)
            raw["espi"] = len(got)
            return got

        def google_en():
            xml = fetch_google(name, "en")
            raw["google"] = xml.count("<item>")
            return parse_google_rss(xml, name, ticker)

        if _is_gpw(ticker):
            items += run("google", google)
            items += run("espi", espi)
        else:
            sym = base_symbol(ticker)

            def yahoo():
                res = fetch_yahoo(sym)
                raw["yahoo"] = len(res or [])
                got = parse_yahoo(res, sym)
                if len(got) < MIN_YAHOO_HITS and name and name.upper() != sym.upper():
                    res2 = fetch_yahoo(name)
                    raw["yahoo"] += len(res2 or [])
                    got += parse_yahoo(res2, sym)
                return [NewsItem(i.date, ticker, i.title, i.link, i.source, i.kind) for i in got]

            got = run("yahoo", yahoo)
            items += got
            if not got and name:
                # Yahoo Search z IP Streamlit Cloud bywa pusty (ASML: 0 wynikow, 2026-11-20) -> Google News EN
                items += run("google", google_en)
        return ticker, items, st_, det

    status: dict = {}
    out: list[NewsItem] = []
    if rows:
        with ThreadPoolExecutor(max_workers=min(max_workers, len(rows))) as ex:
            for ticker, items, st_, det in ex.map(one, rows):
                status[ticker] = st_
                if details is not None and det:
                    details[ticker] = det
                out += items
    lo = today.normalize() - pd.Timedelta(days=WINDOW_DAYS)
    out = [i for i in out if i.date >= lo]
    out.sort(key=lambda i: i.date, reverse=True)
    return dedupe(out), status
