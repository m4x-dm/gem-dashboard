# Mój portfel: moduł 1, import z XTB (design)

Data: 2026-11-19 · Gałąź: `moj-portfel` · Status: zaakceptowany w brainstormingu

## Kontekst i roadmapa

„Mój portfel” to podprojekt 3 z roadmapy (po nawigacji i Karcie spółki). Został podzielony na 4 moduły, budowane po kolei, każdy z osobnym cyklem spec → plan → wdrożenie:

1. **Import z XTB + pozycje** (ten dokument)
2. Alerty fundamentalne: wynik kwartalny beat/miss, duże transakcje insiderów (dane już są w `data/financials.py`)
3. Analiza techniczna: przełamania wsparć i oporów, SMA50/200, maksima i minima 52 tyg., RSI
4. Newsy z mediów o spółkach z portfela (Yahoo News, RSS dla GPW, opcjonalnie ocena AI)

Moduły 2–4 korzystają z listy spółek, którą daje moduł 1, i zasilają panel „Co się dzieje”.

## Decyzje użytkownika

- Kolejność modułów: 1 → 2 → 3 → 4.
- Zapis portfela: **localStorage przeglądarki** (jak watchlista ⭐). Nic nie trafia na serwer na stałe.
- Układ strony: **B**, czyli dwie kolumny: tabela pozycji + struktura po lewej, panel „Co się dzieje” po prawej. Na telefonie panel ląduje pod tabelą.
- Dostęp: **import, kafelki, tabela i struktura są darmowe; panel „Co się dzieje” jest Premium** (Free widzi zajawkę).
- Źródło pozycji: **arkusz *Open Positions* + kursy na żywo** (bez odtwarzania portfela z historii transakcji). Operacje gotówkowe są zapisywane, żeby historię można było zbudować później.

## Format pliku XTB (zbadany na prawdziwym eksporcie z 08.11.2026)

- Plik **XLSX** (nie CSV), jeden na konto. Nazwa ma postać `<TYP>_<nr konta>_<od>_<do>.xlsx`, gdzie typ to `PLN`, `IKE` lub `IKZE`. XTB pakuje kilka kont do jednego ZIP-a.
- Arkusze: `Closed Positions`, `Cash Operations`, `Open Positions`. Daty są liczbami seryjnymi Excela w UTC.
- `Closed Positions` i `Cash Operations`: metadane w wierszach 1–4 (numer konta, zakres dat), nagłówek w **wierszu 5**.
- `Cash Operations`, kolumny: `Type, Instrument, Ticker, Category, Time, Amount, ID, Comment, Product, Position ID`. Typy, które nas interesują: `Deposit`, `IKE deposit`, `IKZE deposit` (kwota ujemna na koncie źródłowym oznacza przelew wychodzący), `Withdrawal`, `Dividend`, `Withholding tax`, `Stock purchase`, `Stock sale`, `SEC fee`, `Free funds interest`, `Free funds interest tax`. Pozostałe typy są zapisywane, ale nie wpływają na kafelki.
- `Open Positions`: wiersze 4–6 to podsumowanie (`Open position value`, `Open position profit`), nagłówek pozycji w **wierszu 9**. Kolumny: `Product, Instrument/Position, Ticker, Category, Type, Volume, Value, Current price, Open price, Open time (UTC), Stop Loss, Take Profit, Net Profit %, Net Profit, Gross Profit, Margin, Open Commission, Swap, Rollover`.
  - **Wiersz zbiorczy** spółki: `Instrument/Position` = nazwa, `Category` wypełnione, `Type` puste.
  - **Wiersz zakupu** (lot): `Instrument/Position` = ID pozycji, `Type` = `BUY`, `Category` puste. Należy do poprzedzającego wiersza zbiorczego.
  - `Value`, `Net Profit` i `Gross Profit` są w walucie konta (PLN). `Open price` i `Current price` są w walucie instrumentu.
- Kolumna `Product` = `IKE`, `IKZE` albo `My Trades` (konto zwykłe). Uwaga: numer konta w nagłówku `Open Positions` bywa numerem konta głównego, więc typ konta bierzemy z `Product`, a numer konta z arkusza `Cash Operations`.
- Konto zwykłe zawiera CFD (`Category` = `CFD`, np. OIL.WTI, GOLD). **CFD są pomijane**, a liczba pominiętych pozycji pokazywana jest w komunikacie.

## Architektura

### `data/portfolio/xtb_parser.py`

`parse_xtb_xlsx(data: bytes, filename: str | None = None) -> XtbAccount`, czysta funkcja bez Streamlita, oparta na `openpyxl` (read_only, data_only).

```python
@dataclass
class XtbAccount:
    account_id: str            # z Cash Operations (wiersz 1)
    account_type: str          # "IKE" | "IKZE" | "ZWYKLE"
    report_time: datetime      # "Data as of report generated" (UTC)
    lots: pd.DataFrame         # xtb_ticker, name, category, volume, open_price, open_time,
                               # value_pln, gross_profit_pln, cost_pln (= value_pln - gross_profit_pln), file_price
    cash_ops: pd.DataFrame     # type, ticker, time, amount_pln, comment
    skipped_cfd: int
```

- Kolumny wyszukiwane są **po nazwie nagłówka**, a nie po indeksie. Wiersz nagłówka jest wykrywany po pierwszej komórce (`Instrument`, `Type`, `Product`), a nie na sztywno numerem 5 lub 9.
- `file_price` to `Current price` z wiersza zakupu.
- Typ konta: z kolumny `Product` (`My Trades` → `ZWYKLE`). Gdy pozycji brak, typ ustala się z prefiksu nazwy pliku, a w ostateczności z `Product` w `Cash Operations`.
- Błędy: `XtbFormatError` z czytelnym komunikatem po polsku (brak arkusza X, brak kolumny Y, „to nie wygląda na eksport z XTB”).

### `data/portfolio/tickers.py`

`xtb_to_yahoo(xtb_ticker: str) -> str | None`:

| Przyrostek XTB | Yahoo | Waluta |
|---|---|---|
| `.US` | bez przyrostka (`META.US` → `META`) | USD |
| `.PL` | `.WA` | PLN |
| `.DE` | `.DE` | EUR |
| `.NL` | `.AS` | EUR |
| `.FR` | `.PA` | EUR |
| `.UK` | `.L` | GBP (kurs w pensach, dzielony przez 100) |

Nieznany przyrostek → `None`, a pozycja jest wyceniana kursem z pliku i oznaczona ⚠ „brak notowań”. Funkcja `currency_for(xtb_ticker)` zwraca walutę instrumentu.

### `data/portfolio/valuation.py`

- `fetch_live_prices(yahoo_tickers) -> pd.DataFrame` (ostatni i przedostatni close). Robi **jedno** `yf.download` z timeoutem, bez `download_prices` i bez fallbacku per ticker (lekcja z Pulpitu: fallback per ticker trwał >5 min przy throttlingu Yahoo). Cache `st.cache_data(ttl=900)` w warstwie widoku.
- Kursy walut: `USDPLN=X`, `EURPLN=X`, `GBPPLN=X` w tym samym wywołaniu.
- `value_portfolio(accounts, prices, fx) -> (positions_df, summary)`:
  - Zakupy agregowane są do pozycji per (konto, ticker): suma ilości, średnia cena = Σ(open_price × volume) / Σ volume (w walucie instrumentu), koszt PLN = Σ cost_pln.
  - Wartość PLN = ilość × kurs bieżący × kurs waluty. Gdy kursu na żywo brak: `value_pln` z pliku.
  - Zysk PLN = wartość − koszt; zysk % = zysk / koszt; udział = wartość / suma.
  - Zmiana z dziś = ilość × (close − poprzedni close) × kurs waluty (bez zmiany kursu waluty).
  - `summary`: wartość, koszt, zysk zł i %, zmiana z dziś zł i %, wpłaty netto, dywidendy netto (dywidendy + podatek u źródła), data najstarszego raportu.
- Wpłaty netto per konto: suma `Deposit` + `IKE deposit`/`IKZE deposit` (dodatnie na koncie docelowym) − `Withdrawal`. Przelewy z konta zwykłego na IKE/IKZE (kwota ujemna na koncie zwykłym) zmniejszają wpłaty konta zwykłego, więc w widoku „Wszystkie” nie są liczone podwójnie.
- Filtr konta (`Wszystkie`/`IKE`/`IKZE`/`Zwykłe`) działa przed agregacją.

### `components/portfolio_storage.py`

- Klucz `gem_dashboard_portfolio_v1`. JSON: `{"v": 1, "accounts": {"<account_id>": {...XtbAccount zserializowany...}}}`. Surowy plik nie jest zapisywany.
- `load_portfolio(ls) -> dict[str, XtbAccount]` (pusty słownik przy braku lub uszkodzonych danych), `save_account(ls, account)` (podmienia konto o tym samym `account_id`), `clear_portfolio(ls)`.
- Kontrola rozmiaru: gdy JSON przekracza 1,5 MB, operacje gotówkowe są przycinane do ostatnich 5 lat i pojawia się ostrzeżenie (localStorage ma ~5 MB na domenę).

### `views/portfel/moj_portfel.py` + rejestr

- `PageDef("moj-portfel", "views/portfel/moj_portfel.py", "Mój portfel", ":material/account_balance_wallet:", "Portfel", True, ...)`: **pierwsza** pozycja w sekcji Portfel, darmowa.
- Układ od góry:
  1. Pole wczytania `st.file_uploader` (xlsx, `accept_multiple_files=True`) + „ostatnio wczytany: <data raportu>” + przycisk „Usuń portfel” (z potwierdzeniem).
  2. Przełącznik kont `st.segmented_control` (tylko konta, które są w portfelu).
  3. Kafelki: Wartość · Zysk/strata · Dziś · Wpłaty netto · Dywidendy.
  4. Dwie kolumny (`st.columns([2, 1])`):
     - lewa: tabela pozycji (Spółka, Konto, Ilość, Śr. cena, Kurs, Wartość, Zysk %, Udział) z klikalnymi wierszami → `nav.go_company(yahoo_ticker)` (wzorzec klikalnego wiersza z Pulpitu); pod nią wykres struktury (donut wg spółek, przełącznik: spółki / konta / waluty);
     - prawa: panel „Co się dzieje”. W module 1: najbliższe raporty kwartalne spółek z portfela (`fetch_earnings_dates`, ±14 dni). Premium; Free widzi zajawkę z opisem przyszłych alertów i linkiem do Premium.
- Stan pusty (brak portfela): instrukcja „Jak pobrać eksport z XTB” (xStation → Historia konta → Eksport → XLSX; ZIP trzeba rozpakować), uploader i informacja o prywatności.
- Informacja o prywatności (zawsze widoczna, zwinięta): plik przetwarzany jest tylko w pamięci, nie jest zapisywany na serwerze, dane portfela zostają w tej przeglądarce.
- Język UI: polski z `tr()` (i18n EN jak na pozostałych stronach).

## Obsługa błędów

| Sytuacja | Zachowanie |
|---|---|
| Plik nie jest XLSX / brak arkuszy XTB | `st.error` z komunikatem `XtbFormatError`; pozostałe wczytane pliki przetwarzane dalej |
| Plik jest ZIP-em | komunikat „rozpakuj ZIP i wczytaj pliki .xlsx” |
| Konto bez otwartych pozycji | konto zapisane (wpłaty, dywidendy liczą się), w tabeli brak wierszy |
| CFD w pliku | pominięte, `st.info` „Pominięto N pozycji CFD” |
| Yahoo nie odpowiada / brak tickera | kurs z pliku, kolumna Kurs z ⚠ i podpowiedzią „kurs z dnia raportu” |
| Uszkodzony JSON w localStorage | traktowany jak brak portfela + `st.warning` |

## Testy

- Fikstura `tests/fixtures/xtb_ike_sample.xlsx` i `xtb_zwykle_sample.xlsx`, generowane skryptem `tests/fixtures/make_xtb_fixtures.py` (openpyxl). Fikcyjne kwoty i numery kont, struktura 1:1 z prawdziwym eksportem: wiersze metadanych, nagłówki w wierszach 5 i 9, wiersze zbiorcze + zakupy, akcje `.US`, `.PL`, ETF `.DE`, CFD, operacje gotówkowe wszystkich typów z listy. **Prawdziwy plik użytkownika nie trafia do repo.**
- `tests/test_xtb_parser.py`: typ konta, liczba zakupów, koszt PLN, pomijanie CFD, błędy formatu, wykrywanie nagłówka po nazwie.
- `tests/test_portfolio_tickers.py`: mapowanie przyrostków, nieznany przyrostek, waluty, pensy GBP.
- `tests/test_portfolio_valuation.py`: agregacja zakupów, średnia cena, fallback na kurs z pliku, zmiana z dziś, wpłaty netto bez podwójnego liczenia przelewów, filtr kont.
- `tests/test_portfolio_storage.py`: zapis i odczyt, podmiana konta, uszkodzony JSON (atrapa LocalStorage).
- Smoke `AppTest` strony `moj-portfel` w stanie pustym i z portfelem (LocalStorage stubowany, sieć wyłączona), plus istniejący smoke wszystkich stron.

## Zależności

- `openpyxl` do `requirements.txt`.

## Poza zakresem modułu 1

Inni brokerzy (mBank, Bossa, Trading 212; parser jest wymienny), ręczne dodawanie transakcji, historia wartości portfela w czasie, zrealizowane zyski, rozliczenie Belki / PIT-38, alerty z modułów 2–4.
