# GEM Dashboard — Karta spółki (podprojekt 2)

**Data:** 2026-11-15
**Status:** zaakceptowany projekt, przed planem wdrożenia
**Gałąź:** `company-card` (od `main` po merge `cb0c3aa`)
**Poprzedni etap:** `2026-11-15-gem-nav-restructure-design.md` (router, rejestr `components/nav.py`, strony w `views/`, motyw B)

## Cel

Jedna strona dla jednej spółki (S&P 500 i GPW), w stylu Stoxly: nagłówek + 6 zakładek. Dziś dane o pojedynczej spółce są rozrzucone po zakładkach stron rynków („💰 Finanse”, deep dive w „📈 Sprawozdania Q”) i każda ma własną wyszukiwarkę. Karta je zbiera, dodaje Przegląd, Dywidendy i Konkurencję oraz momentum GEM (przewaga nad Stoxly).

## Decyzje

| Decyzja | Wybór |
|---|---|
| Zakres v1 | Przegląd (nowy), Finanse, Wyniki, Akcjonariat (przeniesione), Dywidendy (nowe), Konkurencja (nowe). DCF — osobny etap |
| Istniejące zakładki per-spółka w S&P 500 / GPW | Przeniesione do Karty; na stronach rynków zostają funkcje całego rynku |
| Układ Przeglądu | „A”: duży wykres + panel kluczowych danych, pod spodem momentum / analitycy / kalendarz, opis |
| Konkurencja | 5 spółek z sektora o najbliższej kapitalizacji, lista edytowalna (maks. 8) |
| Architektura | Jedna strona `views/spolki/karta.py` + moduły zakładek w `components/company/` + logika danych w `data/company.py` |
| Darmowe | Nagłówek + Przegląd; pozostałe zakładki Premium (`premium_teaser`) |

## Architektura

### Strona i adres

- `views/spolki/karta.py`; wpis w `components/nav.py`: `PageDef("karta", "views/spolki/karta.py", "Karta spółki", ":material/badge:", "Spółki", True, "<opis>")` — **pierwsza** pozycja w sekcji Spółki. `free=True` (router wpuszcza); zakładki Premium gatingowane w stronie (`is_premium()` + `premium_teaser()`).
- Ticker w adresie: `?t=AAPL` / `?t=CDR.WA` (czytany z `st.query_params.get("t")`, normalizowany `upper().strip()`). Zmiana spółki w wyszukiwarce na karcie ustawia `st.query_params["t"]`.
- Bez `t`: wyszukiwarka (SP500 + GPW, format „TICKER — Nazwa”) + podpowiedzi (watchlista + 6 największych spółek) jako `nav.link` do kart.
- Ticker spoza universe SP500/GPW: komunikat „Nie znaleziono spółki {t} w S&P 500 ani na GPW” + wyszukiwarka; bez wyjątku.
- Rynek: `data.financials._detect_market(ticker)` → `"SP500"` / `"GPW"`.

### Nawigacja do karty

- Nowa funkcja w `components/nav.py`: `go_company(ticker: str) -> None` = `st.switch_page(get("karta").path, query_params={"t": ticker})`; oraz `company_link(ticker, label=None)` = `st.page_link(..., query_params={"t": ticker})`.
- Zastępuje mechanizm `{sp500|gpw}_deep_dive_ticker` + `{sp500|gpw}_pending_view` oraz `sp_finanse_ticker` / `gpw_finanse_ticker` / `sp_finanse_default` / `gpw_finanse_default` — usuwane z całego kodu razem z obsługującą je logiką.
- Wołają ją: wyszukiwarka Pulpitu (`_on_search` → flaga → `nav.go_company`), Kalendarz wyników, Insiderzy, screening F12 (przycisk „Pokaż w Finanse” → „Otwórz kartę spółki”), screener Sprawozdań Q (F13), ranking S&P 500 / GPW (selectbox + przycisk „Otwórz kartę” pod tabelą).

### Moduły

`components/company/` (pakiet z `__init__.py`); każdy moduł eksportuje `render(ticker: str, market: str) -> None` i nic nie wie o routingu:

| Plik | Zakładka | Dane |
|---|---|---|
| `header.py` | nagłówek | `download_single(ticker, "1y")`, nazwy (`SP500_NAMES`/`GPW_NAMES`), sektor (`SP500_SECTOR_MAP`/`GPW_SECTOR_MAP`), giełda; przycisk ☆ (watchlista, `components/watchlist.py`; tylko Premium — dla free nieaktywny z podpowiedzią) |
| `overview.py` | Przegląd (free) | `get_ratios_snapshot`, `get_analyst_recos`, `fetch_earnings_dates`, `data.company.momentum_profile`, `data.company.company_profile` (opis, beta, zakres 52 tyg. z `Ticker.info`) |
| `finance.py` | Finanse | karty F11 przeniesione 1:1 z zakładki „💰 Finanse” (`ratios_card`, `forward_consensus_card`, `earnings_history_card`, `analyst_recos_card`) |
| `results.py` | Wyniki | z `components/financials_ui.py`: beat/miss + rachunek / bilans / przepływy (kwartalne i roczne) — obecne pod-zakładki deep dive F13 |
| `ownership.py` | Akcjonariat | `components/financials_ui._render_insiders_tab` (F15) |
| `dividends.py` | Dywidendy | `data.company.dividend_history`, `dividend_summary`, `dividend_after_tax` |
| `peers.py` | Konkurencja | `data.company.sector_peers`, `peer_table` |

`components/financials_ui.render_sprawozdania_deep_dive` przestaje być wołane ze stron rynków; jego pod-zakładki są rozdzielone na `results.py` i `ownership.py` (funkcje `_render_*_tab` zostają w `financials_ui.py` i są importowane).

### `data/company.py` (logika bez UI)

Funkcje czyste przyjmują dane jako argumenty (testy offline); cienkie wrappery z `@st.cache_data` pobierają dane.

- `momentum_profile(ticker: str, prices: pd.DataFrame, rf: float, skip_month: bool = True) -> dict | None` — `{"rank": int, "of": int, "r1m","r3m","r6m","r12m": float}` z rankingu `build_ranking(prices, rf, skip_month=True)` (ta sama reguła co ranking akcji na stronach rynków: 12-1); `None`, gdy tickera nie ma w `prices` lub ma < 273 sesji. Wrapper w karcie używa `download_prices(universe, period="2y")` — **ten sam wywołanie co ranking na stronie rynku** (wspólny cache 1 h). Renderowane w `@st.fragment` na końcu Przeglądu.
- `company_profile(ticker) -> dict` (cache 24 h): `summary`, `beta`, `low52`, `high52`, `exchange`, `currency` z `Ticker.info` (brakujące → `None`).
- `dividend_history(ticker) -> pd.Series` (cache 24 h): `Ticker.dividends`, indeks tz-naive.
- `dividend_summary(divs: pd.Series, price: float | None, info: dict) -> dict`: `yield` (z `info["dividendYield"]`, fallback: suma 12 mies. / cena), `payout` (`info["payoutRatio"]`), `years_paid` (kolejne pełne lata kalendarzowe z wypłatą licząc od ostatniego pełnego roku), `cagr5` (wzrost sum rocznych: rok−1 vs rok−6; `None` gdy brak danych lub suma startowa 0), `annual` (`pd.Series` sum rocznych, ostatnie 10 pełnych lat), `last8` (ostatnie 8 wypłat). Brak dywidend → `{"pays": False}`.
- `dividend_after_tax(amount_pln_or_usd: float, yield_: float, market: str, account: str = "zwykle") -> dict`: `gross = amount * yield_`; podatek: GPW `zwykle` 19%, GPW `ike`/`ikze` 0%; SP500 `zwykle` 19% łącznie (15% u źródła z W-8BEN + 4% w PL), SP500 `ike`/`ikze` 15% (u źródła, niezwracane). Zwraca `{"gross","tax","net","note"}`.
- `sector_caps(market: str, sector: str) -> pd.Series` (cache 24 h): kapitalizacje (`Ticker.info["marketCap"]`) wszystkich spółek sektora z universe; ThreadPool 8 jak w `bulk_fetch_*`; brak → pominięty.
- `sector_peers(ticker: str, caps: pd.Series, n: int = 5) -> list[str]`: `n` spółek o najmniejszej różnicy `|log(cap) - log(cap_ticker)|`, bez samego tickera; gdy sektor ma mniej spółek — tyle, ile jest; gdy brak kapitalizacji tickera — `n` największych.
- `peer_table(rows: dict[str, dict]) -> pd.DataFrame`: kolumny `Kapitalizacja, P/E, Forward P/E, EV/EBITDA, ROE, Marża netto, Wzrost przychodów, Stopa dywidendy, Momentum 12M` + wiersz „Mediana grupy”; wejście = wyniki `get_ratios_snapshot` (+ momentum). Kolorowanie (lepsza od mediany = zielona; dla P/E, Forward P/E, EV/EBITDA niższa = lepsza) robi UI na podstawie `peer_table` i stałej `LOWER_IS_BETTER = {"P/E","Forward P/E","EV/EBITDA"}`.

## Zawartość zakładek

### Nagłówek
Ticker (26 px, 700), nazwa · sektor · giełda (MUTED), po prawej cena (26 px, 650, waluta) + pill zmiany dziennej; ☆ watchlista. Pod nagłówkiem `st.tabs(["Przegląd","Finanse","Wyniki","Akcjonariat","Dywidendy","Konkurencja"])` (bez emoji).

### Przegląd (free)
- Lewo (2/3): wykres ceny (`st.segmented_control` 1M/6M/1R/5L/Max, domyślnie 1R; linia zielona/czerwona wg zmiany w okresie; `_base_layout`).
- Prawo (1/3), karta „kluczowe dane”: kapitalizacja, P/E · Forward P/E, EV/EBITDA (**dla `GPW_BANKS` zamiast niej P/B**), stopa dywidendy, beta, zakres 52 tyg. z markerem ceny.
- Pod spodem 3 karty: **Momentum GEM** („#rank z N w S&P 500/GPW” + 1M/3M/6M/12M; fragment ładowany na końcu), **Analitycy** (liczba, średnia rekomendacja, cel średni + potencjał %, pasek min–cena–cel–max; brak → „Brak pokrycia analityków”), **Kalendarz** (następne wyniki, ostatni dzień ex-dywidendy, ostatni beat/miss).
- „O spółce”: opis (angielski, z Yahoo) skrócony do ~3 linii + `st.expander("Rozwiń")`.

### Finanse / Wyniki / Akcjonariat (Premium)
Logika przeniesiona bez zmian; wygląd motywu B (komponenty już przestylowane).

### Dywidendy (Premium)
Kafelki: stopa, wskaźnik wypłaty, lata z rzędu, CAGR 5 lat. Wykres słupkowy sum rocznych (≤10 lat). Tabela ostatnich 8 wypłat (data, kwota, waluta). Kalkulator: `st.number_input("Kwota inwestycji", value=10000)` + `st.segmented_control` konto (Zwykłe / IKE / IKZE) → brutto, podatek, netto + nota z `dividend_after_tax`. `pays=False` → „Spółka nie wypłaca dywidendy”.

### Konkurencja (Premium)
`st.multiselect` (domyślnie `sector_peers`, maks. 8, opcje = spółki z tego samego rynku). Tabela `peer_table` (spółka wyróżniona pogrubieniem/tłem, wiersz mediany), kolorowanie względem mediany, „—” dla braków. Spinner „Pobieram kapitalizacje sektora…” przy zimnym cache.

## Zmiany w istniejących stronach

- `views/spolki/sp500.py`, `views/spolki/gpw.py`: usunięta zakładka „💰 Finanse” (cały blok + klucze sesji `*_finanse_*`); w „📈 Sprawozdania Q” zostaje tylko screener (`render_sprawozdania_screener`), deep dive i jego obsługa `pending_view` usunięte; w rankingu i screeningu F12: selectbox spółki + przycisk „Otwórz kartę spółki” → `nav.go_company`. Liczba zakładek: 8 → 7.
- `components/financials_ui.py`: screener F13 — wybór spółki prowadzi do `nav.go_company` zamiast przełączać na deep dive.
- `views/spolki/kalendarz_wynikow.py`, `views/spolki/insiderzy.py`: `_navigate_to_deep_dive` → `nav.go_company`.
- `views/start/pulpit.py`: `_on_search` → `nav.go_company`; dopisek pod wyszukiwarką: „Przegląd spółki za darmo, pozostałe zakładki w Premium.”

## Obsługa błędów

Każda zakładka i karta renderowana w `try/except` → komunikat w miejscu (`unavailable`), reszta karty działa. Brak pokrycia analityków / dywidendy / konkurentów / ceny → czytelne komunikaty po polsku. NaN/inf nie trafiają do formatowania (`np.isfinite`). `st.stop()` zakazane w zakładkach (`return`).

## Testy

1. `tests/test_company_data.py` (offline): `momentum_profile` (rank, stopy, ticker spoza danych, za krótka historia), `dividend_summary` (yield z info i fallback, years_paid, cagr5, brak dywidend), `dividend_after_tax` (GPW 19%, GPW IKE 0%, SP500 19%, SP500 IKE 15%), `sector_peers` (najbliższe log-cap, sektor < n, brak cap tickera), `peer_table` (mediana, braki).
2. `tests/test_karta_offline.py` (AppTest przez `app.py`, stub `LocalStorage`, podstawione `download_single`/`download_prices`/funkcje `data.financials`/`data.company`): `?t=AAPL` free → Przegląd + 5 zaślepek; premium → 6 zakładek bez wyjątku; `?t=XXX` → „Nie znaleziono spółki”; bez `t` → wyszukiwarka.
3. `tests/test_nav.py`: `karta` pierwsza w sekcji „Spółki” i `free`; `go_company`/`company_link` istnieją; w `views/`, `components/` brak napisów `deep_dive_ticker`, `pending_view`, `_finanse_ticker`, `_finanse_default`.
4. `tests/test_pages_smoke.py`: dodatkowe przypadki Karty dla `AAPL` i `CDR.WA` (z Premium); S&P 500 i GPW przechodzą po usunięciu zakładek.

## Wdrożenie

Gałąź `company-card`; zadania przez subagentów z przeglądem; zrzuty ekranu Karty (free i Premium, desktop i telefon) do akceptacji użytkownika; pełna suita offline + smoke; merge do `main` i push dopiero po zgodzie użytkownika. Aktualizacja `CLAUDE.md` (sekcja struktury + Karta) i skilli GEM.

## Poza zakresem

DCF / własne projekcje (osobny etap), ceny real-time, transkrypcje konferencji wynikowych, AI (podprojekt 4), zmiany w logice rankingów i backtestów.
