# Mój portfel — moduł 2: alerty fundamentalne

Data: 2026-11-20 · Status: zaakceptowany przez użytkownika · Gałąź: `portfel-alerty`

## Cel
Panel „Co się dzieje” (Premium, prawa kolumna `views/portfel/moj_portfel.py`) pokazuje zdarzenia fundamentalne spółek z portfela z ostatnich 30 dni: wyniki kwartalne beat/miss, zmiany rekomendacji analityków, transakcje insiderów, a także (jak dotąd) najbliższe raporty w ciągu 14 dni.

## Pokrycie danych (zmierzone 20.11 na tickerach użytkownika)
- USA (META, TSLA, NOW, SPCX): wyniki ✅, `upgrades_downgrades` ✅ (15–23 wpisów / 30 dni, głównie `main`/`reit` = zmiana samej ceny docelowej), insiderzy ✅ (głównie sprzedaże).
- Europa (ASML.AS): wyniki ✅, reszta ❌. GPW: wyniki rzadko (XTB.WA 2 kwartały, SNT/DIG/ASB brak), analitycy i insiderzy ❌ (Yahoo 404).
→ Dla `.WA` nie odpytujemy analityków ani insiderów. Spółki bez żadnych danych trafiają do linii „brak danych Yahoo”.

## Reguły (stałe w `data/portfolio/alerts.py`)
| Rodzaj | Warunek | Wydźwięk |
|---|---|---|
| `earnings` | raport (nie przyszły) z datą w ostatnich 30 dniach i znanym `eps_surprise_pct` (w procentach) | ≥ +2 → pos, ≤ −2 → neg, inaczej neutral |
| `upcoming` | przyszły raport w ciągu 14 dni | neutral |
| `rating` | `Action` ∈ up / down / init w ostatnich 30 dniach; tekst „Firm: From → To” (init: „Firm rozpoczyna: To”) | up pos, down neg, init neutral |
| `targets` | 1 linia / spółka: liczba `priceTargetAction` Raises / Lowers w 30 dniach (pomijana, gdy oba 0) | pos gdy ↑>↓, neg gdy ↓>↑ |
| `insider_buy` | każda transakcja `Type == "Buy"` w 30 dniach | pos |
| `insider_sell` | `Type == "Sell"` i `Value` ≥ 1 000 000 USD | neg |
| `insider_sells` | 1 linia / spółka: pozostałe sprzedaże (liczba + suma USD) | neg |
| `no_data` | 1 linia: tickery bez żadnych danych | neutral |
Inne typy transakcji insiderów (nadania, darowizny, opcje) są pomijane.

Kolejność w panelu: zdarzenia z datą (malejąco), potem `targets` i `insider_sells`, potem `upcoming` (rosnąco), na końcu `no_data`.

## Architektura
- `data/portfolio/alerts.py` — czyste funkcje: `earnings_alerts(ticker, df, today)`, `analyst_alerts(ticker, df, today)`, `insider_alerts(ticker, df, today)`, `sort_alerts(list)`; dataclass `Alert(date, ticker, kind, tone, text, params)`; `text` to polski szablon pod `tr(text, **params)`, liczby formatowane przy renderze.
- `data/financials.py` — `fetch_upgrades_downgrades(ticker)` (`st.cache_data` 24 h, przez `_try_insider_endpoint(ticker, "upgrades_downgrades")`), indeks = data (naive), kolumny `Firm, ToGrade, FromGrade, Action, priceTargetAction, currentPriceTarget`; brak → None.
- `alerts.collect(tickers, today, fetchers)` — równolegle (ThreadPoolExecutor, max 6), błąd pojedynczej spółki → `no_data`. Na stronie owinięte `st.cache_data` 6 h.
- Spółki: wszystkie pozycje z `category == "STOCK"` mające ticker Yahoo (także spoza S&P 500/GPW, np. ASML.AS).
- Render: wiersz `ikona · TICKER · tekst · data` (jak dotychczasowe raporty), kolor wg wydźwięku. Free → `premium_teaser` bez zmian.

## Poza zakresem
Powiadomienia e-mail/push, oznaczenie „nowe od ostatniej wizyty”, klikanie alertu → Karta spółki, ESPI z GPW (moduł 4).

## Testy
Offline `tests/test_portfolio_alerts.py`: beat / miss / w linii / raport >30 dni / przyszły ≤14 dni; up / down / init / zliczanie cen docelowych; zakup, duża i mała sprzedaż, nadanie (pomijane); `collect` z wyjątkiem i GPW bez danych; sortowanie. Strona: stub fetcherów, Premium PL i EN (brak polskich resztek). Na koniec sprawdzenie na żywo dla tickerów użytkownika.
