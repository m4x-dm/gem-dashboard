# Mój portfel — moduł 4: newsy o spółkach z portfela

Data: 2026-11-20 · Status: zaakceptowany przez użytkownika · Gałąź: `portfel-newsy`

## Pomiar źródeł (20.11, lokalnie)
- `yf.Ticker(t).news` — zepsute („YAHOO! FINANCE IS CURRENTLY DOWN”). `yf.Search(symbol, news_count=20)` działa: META 18, TSLA 19, SPCX 17, ASML 20 newsów z 7 dni; NOW: tylko 1/19 z `relatedTickers` zawierającym NOW (słowo „now”) → szukanie po nazwie „ServiceNow”. Europa: symbol bez giełdy (ASML.AS → ASML). GPW: 0.
- Google News RSS (`news.google.com/rss/search?q="<nazwa>"+when:14d&hl=pl&gl=PL&ceid=PL:pl`): Synektik 24, Asbis 15, Digital Network 10, XTB 90 (szum: strony reklamowe „… - XTB.com”).
- Bankier: `/gielda/notowania/akcje/<SYMBOL>/komunikaty` — lista ESPI (`m-quotes-announcements-item__date` + `__anchor`). robots.txt: dozwolone dla zwykłych klientów (pełny zakaz tylko GPTBot/CCbot/Bard/Google-Extended). RSS ESPI Bankiera ma tylko 10 ostatnich komunikatów z całej giełdy — za mało.
- Nieznane: dostępność Yahoo Search / Google News / Bankier z IP Streamlit Cloud → diagnostyka ✅/❌, ew. przeniesienie do zrzutu GH Actions.

## Logika — `data/portfolio/news.py`
- `NewsItem(date, ticker, title, link, source, kind)` — `kind` = "news" | "espi"; `date` naive UTC.
- Parsery (czyste, testowane offline): `parse_yahoo(items, symbol)` (tylko `symbol in relatedTickers`), `parse_google_rss(xml, name, ticker)` (tytuł bez sufiksu „ - Źródło”, nazwa spółki musi być w tytule, odrzucane źródła z `BLOCKED_SOURCES` = {"xtb.com"}), `parse_bankier(html, ticker)` (brak znacznika listy w HTML → `NewsParseError`).
- Pobieranie: Yahoo przez `yf.Search` z sesją curl_cffi (`financials._get_yf_session`); Google i Bankier przez `requests` z przeglądarkowym User-Agent, timeout 15 s.
- `collect(rows, today)` — `rows` = [(ticker Yahoo, nazwa z pliku XTB)]; równolegle (max 6). GPW (`.WA`): Google + Bankier (symbol = ticker bez `.WA`); reszta: Yahoo po symbolu bazowym, a gdy < 3 trafień — drugi raz po nazwie. Okno 14 dni, duplikaty (znormalizowany tytuł) usuwane, sortowanie malejąco po dacie. Zwraca `(items, status)`, status `{ticker: {"yahoo"|"google"|"espi": "ok"|"empty"|"error"}}`.

## UI
Sekcja „Newsy” (Premium; Free: `premium_teaser`) w lewej kolumnie pod „Analizą techniczną”: filtr spółek (`st.segmented_control`, etykiety XTB, „Wszystkie”), 20 pozycji + „Pokaż więcej”, wiersz: data · spółka · [ESPI] · tytuł-link (`target="_blank" rel="noopener"`) · źródło; expander „Źródła newsów” ✅/❌. Cache strony 30 min. EN przez `tr()`.

## Poza zakresem
Ocena AI (sentyment/streszczenie), newsy w panelu „Co się dzieje”.

## Testy
Offline: parsery na syntetycznych próbkach (Yahoo dict, RSS XML, HTML Bankiera, zmieniony HTML → błąd), drugie wyszukiwanie po nazwie, okno 14 dni, duplikaty, statusy, GPW vs reszta. Strona: Premium PL/EN, filtr, Free teaser. Na koniec pomiar na żywo + zrzut.
