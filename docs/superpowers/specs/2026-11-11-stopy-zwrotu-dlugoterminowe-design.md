# Stopy zwrotu długoterminowe — porównanie ETF-ów do 30 lat

**Data:** 2026-11-11
**Status:** Zatwierdzony projekt — czeka na review spisanej specyfikacji
**Cel:** Nowa strona premium, która porównuje ETF-y pod względem stóp zwrotu na horyzoncie do 30 lat: skumulowanych, średniorocznych (CAGR), rocznych, kroczących oraz wzrostu kapitału z miarami ryzyka. Opcjonalnie wydłuża historię młodszych ETF-ów o fundusze proxy i przelicza wyniki na PLN.

## Kontekst

Strona 4 (Porównanie) porównuje 2–4 instrumenty na okresach do „10 lat / Maksymalny” na danych dziennych i jest nastawiona na momentum. Nie odpowiada na pytanie „ile średniorocznie dał ten ETF przez 10, 20, 30 lat i jak bardzo to zależało od momentu wejścia”.

Ograniczenie danych: z 37 ETF-ów w `data/etf_universe.py` tylko SPY (od 1993) ma 30 lat historii. QQQ ma ok. 27 lat, sektory XL* 28, AGG/EEM/TLT ok. 22–24, GLD 22, VEA/ACWI ok. 18, VOO 16. Bez proxy 30-letnie porównanie istnieje tylko dla jednego ETF-u.

Sprawdzone 2026-11-11 (yfinance, `period="max"`, `auto_adjust=True`):

| Proxy | Start danych |
|---|---|
| VFINX (Vanguard 500 Index) | 1980-01-02 |
| NAESX (Vanguard Small-Cap Index) | 1980-01-02 |
| VTSMX (Total Stock Market) | 1992-04-27 |
| VBMFX (Total Bond Market) | 1986-12-11 |
| VUSTX (Long-Term Treasury) | 1986-05-19 |
| VFITX (Intermediate-Term Treasury) | 1991-10-28 |
| VBISX (Short-Term Bond Index) | 1994-02-28 |
| VGTSX (Total International Stock) | 1996-04-29 |
| VEIEX (Emerging Markets Index) | 1994-05-04 |
| VEURX (European Stock Index) | 1990-06-18 |
| VGSIX (REIT Index) | 1996-05-13 |

Kurs USD/PLN: yfinance (`USDPLN=X`) ma dane dopiero od 2003-12-01. FRED, seria `CCUSMA02PLM618N` (OECD, średni kurs miesięczny), ma dane od 1957, w nowych złotych (po denominacji), ostatni punkt 2026-09-01.

## Decyzje

1. **Nowa strona** `pages/6_stopy_zwrotu.py`, a nie zakładka strony 4. Logika obliczeń w osobnym module `data/long_returns.py` (czyste funkcje, testowalne).
2. **Pozycja w menu: po „O strategii”, przed „S&P 500”.** Streamlit sortuje strony po numerze z nazwy pliku. Prefiks `6_` przy istniejącym `6_info.py` daje kolejność `6_info` → `6_stopy_zwrotu` → `7_sp500`. Weryfikacja kolejności jest częścią testów; plan B opisany w sekcji „Ryzyka”.
3. **Strona premium**, wewnętrzny numer strony **26** (`require_premium(26)`, wpis w `PAGE_INFO`). Numer w nazwie pliku służy tylko do kolejności w menu.
4. **Dane miesięczne** (ceny z końca miesiąca) w całej stronie. Powody: standard przy analizie wieloletniej, spójność z miesięcznym kursem USD/PLN z FRED, prostsze stopy kroczące. Konsekwencja, którą strona mówi wprost: max drawdown z zamknięć miesięcznych jest płytszy niż z dziennych.
5. **Dwa tryby historii z przełącznikiem**: domyślnie prawdziwa historia ETF-u; opcjonalnie „Wydłuż historię o fundusze proxy”.
6. **Waluta: USD domyślnie, przełącznik PLN.**

## Mapa proxy

Stała w `data/long_returns.py`:

| ETF | Proxy | Uwagi |
|---|---|---|
| SPY, VOO | VFINX | S&P 500 |
| VTI | VTSMX | cały rynek USA |
| IWM | NAESX | małe spółki USA (indeks proxy nie jest identyczny z Russell 2000) |
| VEA, EFA | VGTSX | rynki poza USA; VGTSX zawiera też rynki wschodzące — przybliżenie |
| EEM, VWO | VEIEX | rynki wschodzące |
| VGK | VEURX | Europa |
| AGG, BND | VBMFX | obligacje USA, cały rynek |
| TLT | VUSTX | długie obligacje skarbowe |
| IEF | VFITX | średnie obligacje skarbowe |
| SHY | VBISX | krótkie obligacje (VBISX zawiera też korporacyjne — przybliżenie) |
| VNQ | VGSIX | nieruchomości (REIT) |

Bez proxy (prawdziwa historia): QQQ, ACWI, EWJ, EWU, FXI, TIP, GLD, IAU, GSG, DBC, VNQI, sektory XL*.

**Warunek jakości:** dla każdej pary korelacja miesięcznych stóp zwrotu ETF-u i proxy we wspólnym okresie musi być **> 0,95**. Para, która tego nie spełnia w teście, zostaje usunięta z mapy przed wdrożeniem (decyzja zapisana w commicie).

**Doklejanie:** proxy używane wyłącznie przed pierwszym miesiącem notowań ETF-u. Szereg zbudowany jest ze stóp zwrotu: miesięczne stopy proxy do miesiąca poprzedzającego start ETF-u, dalej wyłącznie stopy ETF-u. Brak skoku poziomu w punkcie połączenia. Funkcja zwraca też datę końca odcinka proxy (do oznaczeń).

## Strona — układ

Nagłówek i podpis, potem kontrolki:

- `multiselect` ETF-ów: min. 2, maks. 8, domyślnie `SPY, VEA, EEM, AGG, GLD`.
- `toggle` „Wydłuż historię o fundusze proxy” (domyślnie wyłączony).
- `radio` waluty: USD / PLN.

Cztery zakładki:

### 1. Tabela okresów
- Wiersze: ETF-y. Kolumny: 1, 3, 5, 10, 15, 20, 25, 30 lat, „Od startu”, „Dane od”.
- `radio`: „Średnioroczna (CAGR)” / „Skumulowana”.
- Wszystkie okresy kończą się na ostatnim pełnym miesiącu (wspólnym dla wybranych ETF-ów).
- Okres dłuższy niż dostępna historia → „—”.
- „Dane od”: rok startu; przy proxy np. „1980 (proxy VFINX do 01.1993)”.

### 2. Stopy roczne
- Heatmapa: lata kalendarzowe × ETF-y, skala zielono-czerwona, wartość w komórce. Bieżący rok oznaczony „YTD”. Pierwszy niepełny rok historii pominięty.
- Pod heatmapą tabela: najlepszy rok, najgorszy rok, % lat na plusie (bez roku YTD).

### 3. Stopy kroczące
- `select_slider` okna: 1, 3, 5, 10, 15, 20 lat (domyślnie 10).
- Wykres liniowy: CAGR w kroczącym oknie, punkt = miesiąc końca okna.
- Tabela: min, 25. percentyl, mediana, 75. percentyl, max, % okien ze stratą (CAGR < 0), liczba okien. ETF z historią krótszą niż okno → komunikat w tabeli, brak linii.

### 4. Wzrost i ryzyko
- `toggle` „Wspólny okres” (domyślnie włączony): przycina wszystkie szeregi do najpóźniejszego startu.
- Wykres wzrostu 10 000 (USD lub zł) w skali logarytmicznej; odcinek proxy linią przerywaną.
- Tabela: CAGR, zmienność roczna (odchylenie miesięcznych stóp × √12), max drawdown, Sharpe, Sortino, Calmar — przez istniejące `calc_stats(equity, trading_days=12, rf_decimal=...)` z `rf` z `get_risk_free()`.
- Notka: drawdown z danych miesięcznych.

Notki stałe na stronie (caption): źródła danych, metoda proxy, kurs PLN = średni miesięczny OECD/FRED, wyniki historyczne nie gwarantują przyszłych. `render_footer()` na końcu.

## Moduł `data/long_returns.py`

Czyste funkcje (bez Streamlita poza warstwą pobierania z cache):

- `PROXY_MAP: dict[str, str]`
- `to_monthly(daily: pd.Series) -> pd.Series` — ostatnia cena w miesiącu, indeks = koniec miesiąca, bez ostatniego niepełnego miesiąca.
- `splice_proxy(etf_m: pd.Series, proxy_m: pd.Series) -> tuple[pd.Series, pd.Timestamp | None]` — szereg doklejony ze stóp zwrotu + data końca odcinka proxy.
- `convert_to_pln(usd_m: pd.Series, fx_m: pd.Series) -> pd.Series` — iloczyn po wyrównaniu indeksów miesięcznych; miesiące bez kursu odrzucone.
- `period_returns(series_m, years=(1,3,5,10,15,20,25,30)) -> pd.DataFrame` — kolumny `total`, `cagr` dla każdego okresu + „od startu”; `NaN`, gdy historii za mało.
- `calendar_year_returns(series_m) -> pd.Series` — indeks = rok; bieżący rok oznaczony flagą (osobny zwrot lub atrybut).
- `rolling_cagr(series_m, years) -> pd.Series`
- `rolling_summary(rolling: pd.Series) -> dict` — min, p25, median, p75, max, pct_negative, count.
- `correlation_with_proxy(etf_m, proxy_m) -> float` — używane w teście jakości.

Pobieranie (z `@st.cache_data(ttl=86400)`, w module lub na stronie):
- ceny: `download_single(ticker, period="max")` → `to_monthly`;
- kurs: `fetch_usdpln_monthly()` — FRED CSV `https://fred.stlouisfed.org/graph/fredgraph.csv?id=CCUSMA02PLM618N`; przy błędzie fallback `download_single("USDPLN=X", period="max")` → `to_monthly` i flaga „PLN od 2003”.

## Obsługa błędów

- ETF się nie pobrał → `st.warning` z tickerem, ETF pominięty, reszta działa.
- Mniej niż 2 ETF-y z danymi → `st.info` i brak dalszych sekcji (bez `st.stop()` w zakładkach).
- Proxy się nie pobrało → prawdziwa historia ETF-u + `st.caption` z informacją.
- FRED niedostępny → fallback yfinance, `st.info` „Tryb PLN od grudnia 2003”.
- Wartości `inf`/`NaN` w tabelach → „—” (guard `np.isinf`).

## Integracja

- `app.py`: kafelek przed „S&P 500” (`(26, "📏", "Stopy zwrotu", "...", "pages/6_stopy_zwrotu.py")`).
- `components/auth.py`: wpis `PAGE_INFO[26]`.
- `components/sidebar.py`: separatory CSS `nth-child(8|12|15)` → `nth-child(9|13|16)` (nowy link przesuwa kolejne o jeden).
- `CLAUDE.md`: lista stron + opis modułu.

## Testy

`tests/test_long_returns.py` (pytest, dane syntetyczne, bez sieci):
- `period_returns`: szereg rosnący dokładnie 10%/rok → CAGR 10% dla każdego dostępnego okresu, `NaN` dla dłuższych niż historia.
- `splice_proxy`: stopy zwrotu po starcie ETF-u identyczne z ETF-em; przed — identyczne z proxy; brak skoku w punkcie połączenia; poprawna data końca proxy.
- `calendar_year_returns`: znane roczne wartości, pominięcie pierwszego niepełnego roku.
- `rolling_cagr` / `rolling_summary`: liczba okien = n − 12·lata; `pct_negative` na znanym przykładzie.
- `convert_to_pln`: stały kurs → stopy jak w USD; kurs rosnący o x% → stopa PLN = (1+r)(1+x)−1.
- `to_monthly`: odrzucenie bieżącego niepełnego miesiąca.

Test jakości proxy (`@pytest.mark.network`, uruchamiany ręcznie przed wdrożeniem): korelacja > 0,95 dla każdej pary z `PROXY_MAP`.

Smoke test strony: `streamlit.testing.v1.AppTest` dla `pages/6_stopy_zwrotu.py` z wyłączonym gatingiem premium — strona renderuje się bez wyjątku dla domyślnych ETF-ów, w trybie USD i PLN, z proxy i bez. Uruchamiany przed pushem.

Weryfikacja kolejności menu: po starcie aplikacji lokalnie link „Stopy zwrotu” jest między „Info” a „S&P 500”, a separatory stoją przed „S&P 500”, „Portfolio Builder” i „Makro Dashboard”.

## Ryzyka

- **Kolejność w menu przy dwóch plikach `6_`:** oczekiwane sortowanie to numer, potem nazwa (`info` < `stopy`). Jeśli test lokalny pokaże inną kolejność, plan B: przenumerować pliki `7_`–`25_` o +1 (`8_sp500.py` … `26_gem_gold_momentum.py`) i nadać nowej stronie `7_stopy_zwrotu.py`. Zmieniają się tylko nazwy plików; numery w `require_premium(...)` zostają, a wszystkie odwołania do ścieżek (`st.page_link`, `st.switch_page`, kafelki w `app.py`) aktualizowane po `grep -rn "pages/"`.
- **Seria FRED** może zostać zmieniona lub wycofana (tak było z LBMA gold w 2022). Fallback yfinance ogranicza tryb PLN do 2003+, ale strona działa.
- **Fundusze proxy** mają inne opłaty niż ETF-y (zwykle wyższe w latach 80.–90.), więc wyniki z odcinka proxy są lekko zaniżone względem hipotetycznego ETF-u. Notka na stronie.
- **Dane yfinance funduszy wzajemnych** (`auto_adjust=True`) zawierają reinwestowane dystrybucje — założenie sprawdzone w teście jakości przez porównanie z ETF-em we wspólnym okresie.

## Poza zakresem

- ETF-y UCITS (VWCE, IWDA) i z GPW — inne źródła i krótsza historia; ewentualnie osobny etap.
- Inflacja (stopy realne) — możliwe rozszerzenie później.
- Wpłaty okresowe (DCA) — jest kalkulator na portalu i strona Monte Carlo.
