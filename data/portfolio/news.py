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


def parse_bankier(page: str, ticker: str) -> list[NewsItem]:
    """Lista komunikatow ESPI ze strony spolki na Bankierze."""
    if "m-quotes-announcements" not in (page or ""):
        raise NewsParseError("brak listy komunikatów w HTML")
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


def fetch_google(name: str) -> str:
    import requests
    url = (f"https://news.google.com/rss/search?q={quote(chr(34) + name + chr(34))}+when:{WINDOW_DAYS}d"
           "&hl=pl&gl=PL&ceid=PL:pl")
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
            fetch_bankier: Callable = fetch_bankier, max_workers: int = 6
            ) -> tuple[list[NewsItem], dict]:
    """rows = [(ticker Yahoo, nazwa spolki)] -> (newsy z 14 dni malejaco, status zrodel per spolka)."""

    def one(row):
        ticker, name = row
        items, st_ = [], {}

        def run(key, fn):
            try:
                got = fn()
            except Exception:
                st_[key] = "error"
                return []
            st_[key] = "ok" if got else "empty"
            return got

        if _is_gpw(ticker):
            items += run("google", lambda: parse_google_rss(fetch_google(name), name, ticker))
            items += run("espi", lambda: parse_bankier(fetch_bankier(base_symbol(ticker)), ticker))
        else:
            sym = base_symbol(ticker)

            def yahoo():
                got = parse_yahoo(fetch_yahoo(sym), sym)
                if len(got) < MIN_YAHOO_HITS and name and name.upper() != sym.upper():
                    got += parse_yahoo(fetch_yahoo(name), sym)
                return [NewsItem(i.date, ticker, i.title, i.link, i.source, i.kind) for i in got]

            items += run("yahoo", yahoo)
        return ticker, items, st_

    status: dict = {}
    out: list[NewsItem] = []
    if rows:
        with ThreadPoolExecutor(max_workers=min(max_workers, len(rows))) as ex:
            for ticker, items, st_ in ex.map(one, rows):
                status[ticker] = st_
                out += items
    lo = today.normalize() - pd.Timedelta(days=WINDOW_DAYS)
    out = [i for i in out if i.date >= lo]
    out.sort(key=lambda i: i.date, reverse=True)
    return dedupe(out), status
