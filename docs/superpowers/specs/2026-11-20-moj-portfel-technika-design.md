# Mój portfel — moduł 3: analiza techniczna

Data: 2026-11-20 · Status: zaakceptowany przez użytkownika · Gałąź: `portfel-technika`

## Cel
Dla pozycji z portfela: (1) zdarzenia techniczne z ostatnich 10 sesji jako alerty w panelu „Co się dzieje”, (2) sekcja „Technika” z tabelą poziomów. Oba Premium (Free: `premium_teaser`).

## Dane
Jedno `yf.download(tickers, period="2y", auto_adjust=True, timeout=30)` dla wszystkich pozycji z tickerem Yahoo (akcje i ETF-y) — kolumny High/Low/Close. Na stronie `st.cache_data` 6 h. Ceny (`yf.download`) działają na Streamlit Cloud (w przeciwieństwie do `quoteSummary`).

## Logika — `data/portfolio/technicals.py` (czyste funkcje)
Stałe: `LEVEL_WINDOW=126`, `PIVOT_K=5`, `CLUSTER_PCT=0.015`, `MIN_TOUCHES=2`, `BREAK_PCT=0.01`, `EVENT_SESSIONS=10`, `RSI_HI=70`, `RSI_LO=30`.
- `levels(high, low, k, window)` → lista `(cena, liczba testów)`: pivot high = `High[i]` = max z `High[i-k..i+k]`, pivot low analogicznie; punkty sortowane, łączone gdy następny ≤ 1,5% od średniej grupy; poziom = średnia grupy; tylko grupy z ≥ 2 punktami.
- `snapshot_row(ohlc)` → słownik do tabeli: `price`, `res` (najbliższy poziom > cena), `sup` (najbliższy < cena), `sma50`, `sma200`, `rsi` (`calc_rsi` z `data/momentum.py`), `from_high52` (cena / max zamknięcia z 252 sesji − 1). Za mało danych → `None`/NaN w danym polu.
- `events(ticker, ohlc)` → lista `Alert` (z `data/portfolio/alerts.py`) z ostatnich 10 sesji, po jednym (najnowszym) na rodzaj:
  - `tech_level`: poziomy liczone z danych KOŃCZĄCYCH SIĘ przed oknem 10 sesji; zamknięcie przechodzi przez poziom (poprzednie po drugiej stronie) i jest dalej niż 1% → opór przebity (pos) / wsparcie przebite (neg).
  - `tech_cross`: SMA50 przecina SMA200 (złoty krzyż pos / śmiertelny neg).
  - `tech_sma200`: zamknięcie przecina SMA200 (pos/neg).
  - `tech_52w`: zamknięcie = max (pos) / min (neg) zamknięć z 252 sesji (wymaga ≥ 252 sesji).
  - `tech_rsi`: RSI przechodzi > 70 (wykupienie) / < 30 (wyprzedanie) — neutral.
- Rodzaje `tech_*` dołączają do `DATED_KINDS` (sortowanie razem z wynikami i insiderami).

## UI
- Panel: alerty techniczne doklejone do listy alertów fundamentalnych przed sortowaniem; ikony 📈/📉 (poziom, 52 tyg.), ✨/⚠ (krzyże), 〰 (SMA200), 🌡 (RSI). Teksty z kwotą w walucie notowań.
- Sekcja „Technika” (lewa kolumna, po „Wartość i wpłaty”): tabela HTML w kontenerze z poziomym przewijaniem; kolumny: Spółka · Kurs · Opór (+%) · Wsparcie (−%) · SMA50 · SMA200 (nad/pod) · RSI · Od 52-tyg. max. RSI ≥ 70 / ≤ 30 wyróżnione. Brak danych → „—”.
- Teksty przez `tr()` + EN w `components/locales/en_portfel.py`.

## Poza zakresem
Wykresy z poziomami, MACD/Bollinger, powiadomienia e-mail.

## Testy
`tests/test_portfolio_technicals.py` (syntetyczne kursy): pivoty i łączenie, min. 2 testy, przebicie bez lookahead (poziom z danych sprzed okna), krzyże SMA, kurs vs SMA200, 52 tyg., RSI wejście w strefę, krótka historia. Strona: stub pobierania cen, Premium PL/EN, Free teaser. Na koniec sprawdzenie na żywo na tickerach użytkownika + zrzut.

## Zmiana 2026-11-20 (po feedbacku użytkownika)
Sekcja przemianowana na **„Analiza techniczna”** („Technical analysis”). Pod tabelą: przełącznik spółki (etykiety XTB) i okresu 6M/1R oraz wykres `technical_chart`: świece dzienne (`fetch_ohlc` pobiera też Open), SMA50/SMA200 liczone z pełnej historii (`chart_frame`), wszystkie wyznaczone poziomy (opory czerwone powyżej kursu, wsparcia zielone poniżej, etykieta z ceną i liczbą testów), trójkąty zdarzeń z ostatnich 10 sesji z opisem w podpowiedzi, RSI(14) z liniami 70/30 w dolnym panelu, bez przerw weekendowych.
