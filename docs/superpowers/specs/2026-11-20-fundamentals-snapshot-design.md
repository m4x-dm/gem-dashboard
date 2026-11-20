# Dzienny zrzut danych fundamentalnych (GitHub Actions → plik → aplikacja)

Data: 2026-11-20 · Status: zaakceptowany przez użytkownika · Gałąź: `fundamentals-snapshot`

## Problem (zdiagnozowany 20.11)
Na Streamlit Cloud Yahoo odrzuca WSZYSTKIE zapytania `quoteSummary` (wyniki, analitycy, insiderzy, `info`), a ceny (`yf.download`) działają. Lokalnie wszystko działa, także na najnowszych yfinance 1.8.0 / curl_cffi 0.17.0. GitHub Actions te dane dostaje (Top Picks 1.11: strategie earnings i quality policzone). Skutek: pusty panel „Co się dzieje” i puste zakładki Wyniki/insiderzy na Karcie spółki na produkcji.

## Rozwiązanie
1. **Zbieranie** — `scripts/update_fundamentals.py` + `.github/workflows/fundamentals.yml` (cron `30 5 * * *` + `workflow_dispatch`).
   - Universe: S&P 500 (`get_sp500_universe`) + GPW (`get_gpw_universe`) + `data/fundamentals_extra.py` (~30 popularnych spółek spoza indeksów, m.in. ASML.AS, SPCX).
   - Na spółkę: `get_earnings_history(t, 8)`; z `Ticker.info`: `earningsTimestamp` (ostatni raport) i `earningsTimestampStart` (następny, jeśli w przyszłości); poza GPW: `fetch_upgrades_downgrades` (90 dni) i `fetch_insider_transactions`. Te same funkcje co aplikacja, z wyłączonym odczytem zrzutu (`GEM_FUNDAMENTALS_SNAPSHOT=0`).
   - Próg: wyniki dla < 50% S&P 500 → exit 1, poprzedni zrzut zostaje.
   - Zapis `fundamentals.json.gz` na gałęzi `data-snapshots` (orphan, jeden commit, `push -f`) — `main` bez codziennych commitów, aplikacja bez restartów.
2. **Odczyt** — `data/fundamentals_snapshot.py`:
   - URL `https://raw.githubusercontent.com/m4x-dm/gem-dashboard/data-snapshots/fundamentals.json.gz` (nadpisywalny `GEM_FUNDAMENTALS_URL`); wyłączenie `GEM_FUNDAMENTALS_SNAPSHOT=0`.
   - Cache w pamięci procesu: sukces 1 h, porażka 5 min (bez wielokrotnych timeoutów).
   - Zrzut starszy niż 3 dni = brak zrzutu.
   - API: `snapshot()` → obiekt albo None; `lookup(kind, ticker, ...)` → `(trafienie, wartość)`. Spółka obecna w zrzucie = trafienie, także gdy pole puste (np. GPW bez insiderów) — wtedy NIE pytamy Yahoo.
3. **Integracja** — `_cache_success(snapshot=...)`: wrapper najpierw pyta zrzut, dopiero przy braku trafienia idzie do Yahoo (z cache 24 h bez zapamiętywania None). Dotyczy: `get_earnings_history`, `fetch_insider_transactions`, `fetch_upgrades_downgrades`; `fetch_last_report_date` i `fetch_earnings_dates` (data następnego raportu, bez wywołania `Ticker.calendar`) sprawdzają zrzut bezpośrednio. Przyszły raport ze zrzutu nie ma prognozy EPS (NaN).
4. **UI** — panel portfela: podpis „Dane fundamentalne z dziennego zrzutu z dd.mm hh:mm UTC”, gdy zrzut jest aktywny.

## Format pliku
```json
{"version": 1, "generated_at": "2026-11-21T05:41:00Z",
 "tickers": {"META": {"eh": {split DataFrame}, "rd": "2026-10-21", "nd": "2027-01-27",
                      "ud": {split}, "ins": {split}}}}
```
`split` = `{"index": [ISO dat], "columns": [...], "data": [[...]]}`; NaN → null. Brak klucza = brak danych dla tej spółki (trafienie z wartością None).

## Poza zakresem
`Ticker.info` dla reszty Karty spółki (wskaźniki, profil, rekomendacje), instytucje, główni akcjonariusze — następny krok tym samym mechanizmem.

## Testy
`tests/conftest.py` wyłącza zrzut domyślnie. Nowe: serializacja ↔ deserializacja (typy, daty, NaN), trafienie / brak / pusty / stary zrzut, porażka pobrania (cache 5 min), wrapper: zrzut przed Yahoo, spółka spoza zrzutu → Yahoo, `fetch_earnings_dates` ze zrzutu bez `calendar`, próg pokrycia w skrypcie (sieć zamockowana). Na koniec ręczny run workflow i sprawdzenie produkcji.
