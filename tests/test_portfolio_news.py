"""Offline: newsy o spolkach z portfela (Yahoo Search, Google News RSS, ESPI z Bankiera)."""
import pandas as pd
import pytest

from data.portfolio import news

TODAY = pd.Timestamp("2026-11-20")


def _ts(s):
    return int(pd.Timestamp(s, tz="UTC").timestamp())


YAHOO = [
    {"title": "Meta rallies", "link": "https://y/1", "publisher": "Barrons.com",
     "providerPublishTime": _ts("2026-11-19 10:00"), "relatedTickers": ["META", "GOOGL"]},
    {"title": "Unrelated now story", "link": "https://y/2", "publisher": "Fortune",
     "providerPublishTime": _ts("2026-11-18 10:00"), "relatedTickers": ["AAPL"]},
]

RSS = """<?xml version="1.0"?><rss><channel>
<item><title>Synektik poniżej oczekiwań rynku - Bankier.pl</title><link>https://g/1</link>
<pubDate>Wed, 18 Nov 2026 08:00:00 GMT</pubDate><source url="https://bankier.pl">Bankier.pl</source></item>
<item><title>Inwestuj w akcje Synektik - XTB.com</title><link>https://g/2</link>
<pubDate>Tue, 17 Nov 2026 08:00:00 GMT</pubDate><source url="https://xtb.com">XTB.com</source></item>
<item><title>SNT (+3.21%) - Synektik SA - Stooq</title><link>https://g/5</link>
<pubDate>Wed, 18 Nov 2026 09:00:00 GMT</pubDate><source url="https://stooq.pl">Stooq</source></item>
<item><title>Rynek medyczny rośnie - Parkiet</title><link>https://g/3</link>
<pubDate>Tue, 17 Nov 2026 08:00:00 GMT</pubDate><source url="https://parkiet.com">Parkiet.com</source></item>
<item><title>Synektik &amp; partnerzy - Stary news</title><link>https://g/4</link>
<pubDate>Mon, 20 Oct 2026 08:00:00 GMT</pubDate><source url="https://x">StockWatch.pl</source></item>
</channel></rss>"""

BANKIER = """<ul class="m-quotes-announcements-list">
<li class="m-quotes-announcements-list__item"><div class="m-quotes-announcements-item">
<span class="m-quotes-announcements-item__date">18.11.2026 06:03</span>
<a class="m-quotes-announcements-item__anchor" href="https://www.bankier.pl/wiadomosc/SYNEKTIK-Wyniki-1.html"
 data-vr-contentbox="x">Wyniki finansowe QSr 4/2025</a></div></li>
<li class="m-quotes-announcements-list__item"><div class="m-quotes-announcements-item">
<span class="m-quotes-announcements-item__date">01.09.2026 18:00</span>
<a class="m-quotes-announcements-item__anchor" href="https://www.bankier.pl/wiadomosc/SYNEKTIK-Stary-2.html">Stary komunikat</a></div></li>
</ul>"""


def test_parse_yahoo_keeps_only_related():
    items = news.parse_yahoo(YAHOO, "META")
    assert [i.title for i in items] == ["Meta rallies"]
    assert items[0].source == "Barrons.com" and items[0].date == pd.Timestamp("2026-11-19 10:00")


def test_parse_google_rss_filters_name_and_broker_promos():
    items = news.parse_google_rss(RSS, "Synektik", "SNT.WA")
    titles = [i.title for i in items]
    assert "Synektik poniżej oczekiwań rynku" in titles             # sufiks " - Bankier.pl" usuniety
    assert not any("XTB.com" in i.source for i in items)             # reklama brokera
    assert not any("Rynek medyczny" in t for t in titles)            # brak nazwy w tytule
    assert "Synektik & partnerzy" in titles                          # encje HTML rozkodowane
    assert not any(t.startswith("SNT (") for t in titles)            # notowanie Stooq, nie news


def test_parse_bankier_espi_and_changed_markup():
    items = news.parse_bankier(BANKIER, "SNT.WA")
    assert [(i.title, i.kind) for i in items] == [("Wyniki finansowe QSr 4/2025", "espi"),
                                                 ("Stary komunikat", "espi")]
    assert items[0].date == pd.Timestamp("2026-11-18 06:03") and items[0].source == "ESPI"
    with pytest.raises(news.NewsParseError):
        news.parse_bankier("<html>nowy wyglad strony</html>", "SNT.WA")


def test_collect_routes_sources_window_dedupe_and_status():
    calls = []

    def yahoo(q):
        calls.append(("y", q))
        if q == "NOW":
            return [dict(YAHOO[1], relatedTickers=["AAPL"])]
        if q == "ServiceNow":
            return [dict(YAHOO[0], title="ServiceNow AI push", relatedTickers=["NOW"])]
        return YAHOO

    def google(name):
        calls.append(("g", name))
        return RSS

    def bankier(symbol):
        calls.append(("b", symbol))
        raise OSError("timeout")

    details = {}
    items, status = news.collect([("META", "Meta"), ("NOW", "ServiceNow"), ("SNT.WA", "Synektik")], TODAY,
                                 fetch_yahoo=yahoo, fetch_google=google, fetch_bankier=bankier, details=details)
    assert details["SNT.WA"]["espi"] == "OSError: timeout"
    assert ("y", "ServiceNow") in calls and ("y", "META") in calls       # NOW: drugie szukanie po nazwie
    assert ("g", "Synektik") in calls and ("b", "SNT") in calls
    assert not any(c[0] == "y" and c[1].startswith("SNT") for c in calls)
    assert status["SNT.WA"] == {"google": "ok", "espi": "error"}
    assert status["META"] == {"yahoo": "ok"}
    titles = [i.title for i in items]
    assert "ServiceNow AI push" in titles
    assert "Synektik & partnerzy" not in titles                          # starszy niz 14 dni
    assert [i.date for i in items] == sorted((i.date for i in items), reverse=True)


def test_dedupe_same_title_from_two_sources():
    a = news.NewsItem(pd.Timestamp("2026-11-18"), "SNT.WA", "Synektik: wyniki!", "l1", "Bankier.pl", "news")
    b = news.NewsItem(pd.Timestamp("2026-11-18"), "SNT.WA", "synektik wyniki", "l2", "Parkiet", "news")
    assert len(news.dedupe([a, b])) == 1



def test_merge_same_article_across_tickers():
    a = news.NewsItem(pd.Timestamp("2026-11-20"), "META", "Funds With Anthropic Exposure", "l", "Barrons.com")
    b = news.NewsItem(pd.Timestamp("2026-11-20"), "SPCX", "Funds with Anthropic exposure", "l", "Barrons.com")
    c = news.NewsItem(pd.Timestamp("2026-11-19"), "META", "Other", "l2", "X")
    merged = news.merge_across_tickers([a, b, c])
    assert [(m[0].title, m[1]) for m in merged] == [("Funds With Anthropic Exposure", ["META", "SPCX"]),
                                                    ("Other", ["META"])]



def test_bankier_parse_error_names_page_title():
    with pytest.raises(news.NewsParseError, match="Zanim przejdziesz"):
        news.parse_bankier("<html><title>Zanim przejdziesz do serwisu</title></html>", "SNT.WA")


def test_details_explain_empty_results():
    details = {}
    news.collect([("ASB.WA", "Asbis")], TODAY, fetch_google=lambda n: RSS, fetch_bankier=lambda s: BANKIER,
                 details=details)
    assert details["ASB.WA"]["google"].startswith("0 pasujących z 5")
