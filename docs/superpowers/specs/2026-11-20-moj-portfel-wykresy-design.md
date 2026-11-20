# Mój portfel — wykresy w czasie (wartość vs wpłaty, porównanie z indeksami)

Data: 2026-11-20 · Status: zaakceptowany przez użytkownika · Gałąź: `portfel-wykresy`

## Cel
Na stronie `views/portfel/moj_portfel.py` oprócz donuta struktury pokazać:
1. **Wartość vs wpłacony kapitał** (darmowe) — jak rósł portfel na tle wpłat netto, zysk/strata w czasie.
2. **Porównanie z indeksami** (Premium, teaser dla free) — „co gdyby” każda wpłata trafiła tego samego dnia do WIG20 / mWIG40 / S&P 500 / Nasdaq 100.

## Dane wejściowe
Wyłącznie to, co parser już zapisuje: `XtbAccount.cash_ops` (`type, ticker, time, amount_pln, comment`) i `lots` (do kontroli). Bez zmian w formacie localStorage.

Komentarze transakcji (zweryfikowane na prawdziwym eksporcie):
- `Stock purchase`: `OPEN BUY SNT.PL 3 @ 123.45`
- `Stock sell`: `CLOSE BUY NVDA.US 1.5/3 @ 180.20` (pierwsza liczba = sprzedana ilość)

Regex: `^(OPEN|CLOSE) BUY (\S+) ([\d.]+)(?:/[\d.]+)? @ ([\d.]+)`. Komentarz niepasujący → operacja liczy się tylko do gotówki (bez zmiany sztuk) + licznik `unparsed`.

## Model
Moduł `data/portfolio/history.py` (czysta logika + jedno pobieranie):

- `parse_trades(cash_ops) -> DataFrame[time, xtb_ticker, qty(+/-), price, amount_pln]`
- `is_flow(type)`: typ zawiera `deposit`, `withdraw` lub `transfer` (bez względu na wielkość liter). Przepływy liczone **per konto**, więc przelew zwykłe→IKE znosi się w widoku „Wszystkie”, a w widoku IKE jest wpłatą.
- `history_tickers(accounts) -> set[str]`: tickery Yahoo wszystkich papierów z historii + kursy walut + benchmarki.
- `fetch_history(tickers, start) -> DataFrame` dziennych close (jedno `yf.download(..., start=..., auto_adjust=True, timeout=30)`; błąd → pusty DF). Na stronie owinięte `st.cache_data(ttl=6h)`.
- `reconstruct(accounts, prices, account_type=None) -> (DataFrame[value, deposits], dict checks)` na dziennym indeksie dni roboczych od pierwszej operacji do dziś:
  - gotówka(d) = skumulowana suma `amount_pln` wszystkich operacji do końca dnia d;
  - sztuki(d) per ticker = skumulowana suma `qty`;
  - kurs(d) = close Yahoo / dzielnik (UK=100) × FX(d), ffill. Ticker bez danych Yahoo **lub** z kursem różnym o >50% od ceny transakcji (ETF-y LSE notowane przez XTB w USD) → kurs zastępczy: wartość jednostkowa PLN z ostatniej transakcji (`|amount_pln| / qty`), ffill;
  - wartość(d) = gotówka(d) + Σ sztuki × kurs; deposits(d) = skumulowane przepływy.
  - `checks`: `volume_mismatch` — lista tickerów, dla których sztuki na koniec ≠ suma `volume` w `lots` (tolerancja 1e-6); `unparsed` — liczba niesparsowanych transakcji.
- `whatif(flows, bench_close_pln) -> Series`: każdy przepływ kupuje (wpłata) / sprzedaje (wypłata, max do zera) jednostki benchmarku po close dnia (ffill/bfill do najbliższej sesji); wartość = jednostki × close.

Benchmarki (total return, w PLN): WIG20 `ETFBW20TR.WA`, mWIG40 `ETFBM40TR.WA`, S&P 500 `SPY`×`USDPLN=X`, Nasdaq 100 `QQQ`×`USDPLN=X`. Benchmark bez danych → pomijany (podpis „brak danych”).

## UI
Nowa sekcja w lewej kolumnie pod pozycjami, przed „Struktura”, działa z przełącznikiem kont:
- **„Wartość i wpłaty”** — `portfolio_value_chart(df)` w `components/charts.py`: linia wartości (złota), przerywana linia wpłat, wypełnienie między nimi (zielone/czerwone wg znaku zysku na końcu okresu — jedno wypełnienie, bez podziału na segmenty), hover: data, wartość, wpłaty, zysk zł i % wpłat.
- **„Porównanie z indeksami”** — Premium: `benchmark_whatif_chart(df)` (portfel + 4 indeksy + wpłaty przerywane) i tabelka: wartość dziś, różnica vs portfel (zł). Free: `premium_teaser`.
- Ostrzeżenie ⚠ nad wykresami, gdy `volume_mismatch` niepuste: „Eksport nie obejmuje całej historii konta — w XTB wybierz zakres od początku konta”. Wykres i tak się rysuje.
- Brak sieci / pusty `prices` → `st.info` „Nie udało się pobrać historii kursów”.
- Wszystkie teksty przez `tr()` + tłumaczenia w `components/locales/en_portfel.py`.

## Poza zakresem
Otwarte CFD (wynik tylko w gotówce przy zamknięciu), stopa zwrotu w % (TWR), dywidendy benchmarków poza tym, co dają fundusze TR / auto_adjust.

## Testy
Offline (`tests/test_portfolio_history.py`) na syntetycznych operacjach: parsowanie komentarzy (w tym `x/y`), kupno + częściowa sprzedaż, przelew zwykłe→IKE (widok Wszystkie vs IKE), wypłata, papier bez kursu Yahoo (kurs z transakcji), sanity >50%, `volume_mismatch`, `whatif` (wpłata, wypłata, dni bez sesji). Smoke strony w `tests/test_moj_portfel_offline.py` ze stubem `fetch_history`. Weryfikacja na prawdziwym pliku: tylko „zgodne/niezgodne” (sztuki na koniec vs Open Positions; wartość ostatniego dnia vs wycena strony ±5%).
