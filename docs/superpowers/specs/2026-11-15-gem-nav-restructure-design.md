# GEM Dashboard — przebudowa struktury i nawigacji (podprojekt 1)

**Data:** 2026-11-15
**Status:** zaakceptowany projekt, przed planem wdrożenia
**Gałąź:** `restructure-nav`

## Kontekst i cel

GEM Dashboard ma dziś 27 stron w jednej płaskiej liście w sidebarze (`pages/N_nazwa.py`, numery się dublują: `6_info`, `6_stopy_zwrotu`), separatory sekcji oparte o `nth-child(9/13/16)` w CSS oraz stronę startową z 27 kafelkami. Każda nowa strona przesuwa separatory i dokłada kafelek — struktura jest nieczytelna i nie skaluje się.

Ten podprojekt porządkuje strukturę, zanim dojdą nowe funkcje inspirowane Stoxly.ai. Kolejne podprojekty (osobne specyfikacje):

1. **Przebudowa struktury i nawigacji** ← ten dokument
2. Karta spółki (wyszukiwarka → jeden ticker, zakładki: Przegląd, Finanse, Wyniki, Akcjonariat, Dywidendy, Konkurencja)
3. Mój portfel (import XTB/mBank, IKE/IKZE/OKI, podatek Belki)
4. Warstwa AI (podsumowania spółek i newsów, Puls rynku, czat)

**Zasada:** przenosimy i scalamy, niczego nie wycinamy. Każda dzisiejsza funkcja ma swoje miejsce po przebudowie.

## Decyzje

| Decyzja | Wybór |
|---|---|
| Układ menu | Górne menu z rozwijanymi sekcjami (`st.navigation(position="top")`) |
| Strona startowa | Pulpit — centrum dowodzenia |
| Model darmowy | Darmowe: Pulpit (okrojony), Sygnał GEM (zakładka „Teraz”), Ranking ETF, O strategii; w podprojekcie 2 Karta spółki — tylko zakładka Przegląd |
| Podejście techniczne | Router `st.navigation` + strony w folderach sekcji + jeden rejestr stron |

## Architektura

### Router (`app.py`)

`app.py` przestaje być stroną. Kolejność:

1. `st.set_page_config(layout="wide", ...)`
2. `setup_sidebar()` — globalny CSS, inicjalizacja Premium z localStorage, pole kodu Premium, stopka sidebaru
3. Zbudowanie stron z rejestru i `pg = st.navigation(sections, position="top")`
4. Bramka dostępu: jeśli `pg` to strona płatna, a użytkownik nie ma Premium → `render_lock_screen(page)` zamiast `pg.run()`
5. W przeciwnym razie `pg.run()`

`setup_sidebar()` i bramka są wywoływane raz w routerze — znikają z poszczególnych stron.

### Rejestr stron (`components/nav.py`)

Jedyne źródło prawdy o stronach:

```python
@dataclass(frozen=True)
class PageDef:
    key: str          # stabilny identyfikator, np. "sp500"
    path: str         # "pages/spolki/sp500.py"
    title: str        # "S&P 500"
    icon: str         # "🇺🇸"
    section: str      # "Spółki" albo "" (link bezpośredni w menu)
    description: str  # opis do ekranu blokady (z dawnego PAGE_INFO)
    free: bool        # True = cała strona darmowa
    default: bool = False
```

Funkcje publiczne:

- `PAGES: list[PageDef]` — kolejność = kolejność w menu
- `build_navigation() -> dict[str, list[st.Page]]` — sekcje dla `st.navigation`
- `get(key) -> PageDef`
- `go(key)` — `st.switch_page` po kluczu (zastępuje twarde ścieżki)
- `link(key, label=None)` — `st.page_link` po kluczu

`FREE_PAGES = {0, 1, 2, 6}`, `PAGE_INFO` po numerach i `require_premium(N)` w 24 plikach zostają zastąpione polem `free` i bramką w routerze. Ekran blokady (`_render_lock_screen`) bierze ikonę, tytuł i opis z rejestru (opis = dotychczasowy tekst z `PAGE_INFO`, przeniesiony do pola `description: str` w `PageDef`).

Strony częściowo darmowe (Pulpit, Sygnał GEM; później Karta spółki) mają `free=True` w rejestrze i same sprawdzają `is_premium()` dla płatnych sekcji/zakładek.

### Górne menu

```
📈 Pulpit | Strategia GEM ▾ | ETF ▾ | Spółki ▾ | Krypto | Portfel ▾ | Rynek ▾
```

Pulpit i Krypto mają po jednej stronie → sekcja `""` (link bezpośredni). Na wąskich ekranach Streamlit sam przenosi menu pod ☰.

Pola wyszukiwania nie da się osadzić w górnym pasku Streamlita — wyszukiwarka spółek jest na górze Pulpitu.

### Sidebar

Zostaje wyłącznie na: filtry/ustawienia danej strony, aktywację/dezaktywację Premium, stopkę. Usunięte: CSS separatorów `nth-child`, style kafelków strony startowej.

## Mapa stron (27 → 24)

| Sekcja | Nowy plik | Klucz (URL = nazwa pliku) | Źródło | Darmowa |
|---|---|---|---|---|
| — | `pages/start/pulpit.py` | `pulpit` (domyślna) | `0_podsumowanie.py` + kafelki z `app.py` | częściowo |
| Strategia GEM | `pages/strategia/sygnal.py` | `sygnal` | `1_sygnal_gem.py` + `17_sygnaly.py` | częściowo |
| Strategia GEM | `pages/strategia/backtest.py` | `backtest` | `5_backtest.py` | nie |
| Strategia GEM | `pages/strategia/gem_extended.py` | `gem-extended` | `22_gem_extended.py` | nie |
| Strategia GEM | `pages/strategia/gem_zloto.py` | `gem-zloto` | `25_gem_gold_momentum.py` | nie |
| Strategia GEM | `pages/strategia/o_strategii.py` | `o-strategii` | `6_info.py` | tak |
| ETF | `pages/etf/ranking.py` | `ranking-etf` | `2_ranking.py` | tak |
| ETF | `pages/etf/porownaj.py` | `porownaj` | `3_wykresy.py` + `4_porownanie.py` + `21_side_by_side.py` | nie |
| ETF | `pages/etf/stopy_zwrotu.py` | `stopy-zwrotu` | `6_stopy_zwrotu.py` | nie |
| ETF | `pages/etf/drawdowny.py` | `drawdowny` | `16_drawdown.py` | nie |
| Spółki | `pages/spolki/sp500.py` | `sp500` | `7_sp500.py` | nie |
| Spółki | `pages/spolki/gpw.py` | `gpw` | `8_gpw.py` | nie |
| Spółki | `pages/spolki/top_picks.py` | `top-picks` | `9_top_picks.py` | nie |
| Spółki | `pages/spolki/screener.py` | `screener` | `12_screener.py` | nie |
| Spółki | `pages/spolki/kalendarz_wynikow.py` | `kalendarz-wynikow` | `23_earnings_calendar.py` | nie |
| Spółki | `pages/spolki/insiderzy.py` | `insiderzy` | `24_insider_screener.py` | nie |
| — | `pages/krypto/kryptowaluty.py` | `krypto` | `10_kryptowaluty.py` | nie |
| Portfel | `pages/portfel/portfolio_builder.py` | `portfolio-builder` | `11_portfolio.py` | nie |
| Portfel | `pages/portfel/monte_carlo.py` | `monte-carlo` | `18_monte_carlo.py` | nie |
| Rynek | `pages/rynek/makro.py` | `makro` | `13_makro.py` | nie |
| Rynek | `pages/rynek/sektory.py` | `sektory` | `19_sektory.py` | nie |
| Rynek | `pages/rynek/intermarket.py` | `intermarket` | `20_intermarket.py` | nie |
| Rynek | `pages/rynek/sezonowosc.py` | `sezonowosc` | `14_sezonowosc.py` | nie |
| Rynek | `pages/rynek/waluta.py` | `waluta` | `15_waluta.py` | nie |

Pliki przenoszone są przez `git mv`, żeby zachować historię.

### Scalenia

**Sygnał GEM** (`sygnal.py`) — zakładki:
- *Teraz* (treść `1_sygnal_gem.py`) — darmowa
- *Historia*, *Statystyki*, *Kalendarz* (zakładki z `17_sygnaly.py`; jego zakładka „Obecny sygnał” dubluje *Teraz* i odpada) — Premium; bez Premium zakładka pokazuje zaślepkę z przyciskiem „Odblokuj”

**Porównaj** (`porownaj.py`) — zakładki:
- *Wykresy* (`3_wykresy.py`: cena, momentum, drawdown)
- *Head-to-head* (`4_porownanie.py`: 2–4 ETF + macierz korelacji)
- *Side-by-side* (`21_side_by_side.py`)

Każda zakładka ma własne kontrolki wyboru tickerów wewnątrz zakładki (nie w sidebarze), bo sidebar jest wspólny dla całej strony. Kod każdej dawnej strony trafia do funkcji `render_<zakladka>()`, wywoływanej w `with tab:` — logika bez zmian.

## Pulpit

Układ od góry:

1. **Baner alertów cenowych** — jeśli któryś alert się uruchomił (logika z `0_podsumowanie.py`, sekcja F1)
2. **Wyszukiwarka spółki** — `st.selectbox` z podpowiedziami z S&P 500 + GPW (`"AAPL — Apple Inc."`). Do czasu Karty spółki: ustawia ticker w session_state (ta sama „pending flag” co cross-link F14→F13) i robi `nav.go("sp500")` lub `nav.go("gpw")`.
3. **Pasek stanu** — 3 karty:
   - 🎯 Sygnał GEM: pozycja, od kiedy, data następnego przeliczenia (pierwszy dzień roboczy kolejnego miesiąca)
   - Regime rynku: risk-on / risk-off
   - Wskaźniki rynku: VIX, S&P 500, WIG20, USD/PLN, złoto, BTC — poziom + zmiana dzienna
4. **Trzy kolumny** (Premium):
   - ⭐ Moja watchlista — cena, zmiana dzienna, sparkline 3M; źródło: `components/watchlist.py` (localStorage, ten sam zestaw co F14/F17); pusta → podpowiedź „Dodaj spółki gwiazdką w S&P 500 / GPW”
   - 📅 Wyniki w tym tygodniu — najpierw spółki z watchlisty, potem największe kapitalizacje SP500+GPW; max 10 pozycji
   - 🔥 Wygrani / przegrani dnia — top 5 / bottom 5 zmiany dziennej osobno dla SP500 i GPW
5. **Top 5 ETF wg momentum** (darmowe) + **wyniki strategii 5 lat** (Premium)
6. **Status danych** — `data_status_card()` w zwiniętym `st.expander`

**Bez Premium** karty z punktu 4 i wyniki 5 lat to zaślepki: tytuł, jedno zdanie, przycisk „Odblokuj Premium” (link Naffy jak na ekranie blokady).

### Dane i wydajność

- Pasek stanu i Top 5 korzystają z `download_prices(ALL_TICKERS)` — jak dziś. Brakujące w ETF-universe symbole wskaźników (VIX, WIG20, USD/PLN, BTC) pobierane przez `download_single` (cache 1 h).
- Wygrani/przegrani: nowa funkcja `data/movers.py::daily_movers(universe) -> pd.DataFrame` — `download_prices(tickers, period="5d")`, zmiana ostatniej sesji, `@st.cache_data(ttl=3600)` (cache globalny, wspólny dla wszystkich użytkowników). Renderowana w `@st.fragment` po reszcie strony, ze spinnerem.
- Kalendarz wyników: funkcje pobierania i filtrowania z `23_earnings_calendar.py` przenoszone do `data/earnings.py`; strona Kalendarz i Pulpit importują z jednego miejsca.

### Obsługa błędów

Każda karta Pulpitu renderowana niezależnie: wyjątek lub brak danych w jednej karcie → komunikat „Dane chwilowo niedostępne” w tej karcie, reszta Pulpitu działa. Wartości NaN/inf nie trafiają do formatowania (guard `np.isfinite`, zgodnie z konwencją projektu).

## Linki między stronami

Twarde ścieżki zastąpione kluczami rejestru:

| Miejsce | Było | Jest |
|---|---|---|
| Kalendarz wyników | `st.switch_page("pages/7_sp500.py")` / `8_gpw.py` | `nav.go("sp500")` / `nav.go("gpw")` |
| Insiderzy | `st.switch_page("pages/7_sp500.py")` | `nav.go("sp500")` |
| Pulpit (wyszukiwarka) | — | `nav.go("sp500")` / `nav.go("gpw")` |

Mechanizm „pending flag” + baner podpowiedzi (Streamlit nie preselekcjonuje zakładki) bez zmian.

## Testy

1. **Rejestr** (`tests/test_nav.py`, nowy):
   - każdy `path` istnieje
   - `key`, tytuły i nazwy plików unikalne (URL = nazwa pliku; router rozpoznaje stronę po tytule)
   - dokładnie jedna strona `default=True` (`pulpit`)
   - zbiór stron `free=True` = {`pulpit`, `sygnal`, `ranking-etf`, `o-strategii`}
   - każda sekcja niepusta; kolejność sekcji: "", Strategia GEM, ETF, Spółki, Krypto (""), Portfel, Rynek
   - żaden plik w `pages/` nie zawiera `require_premium(` ani `st.switch_page("pages/`
2. **Smoke AppTest dla każdej z 24 stron** (`tests/test_pages_smoke.py`, nowy), uruchamiany przez router:
   - z Premium: strona renderuje się bez wyjątku
   - bez Premium: strona płatna pokazuje ekran blokady i nie uruchamia swojej treści
   - sieć: testy działają na danych z `data/cache/*.csv` / zamockowanym `download_prices`, żeby nie zależały od yfinance
3. **Istniejące testy** — poprawione ścieżki (`test_stopy_zwrotu_page.py` ma twarde `pages/6_stopy_zwrotu.py` / `pages/7_sp500.py`; `test_calendar.py` importuje helpery, które przechodzą do `data/earnings.py`). Cała suita zielona przed scaleniem.

## Wdrożenie

1. Praca na gałęzi `restructure-nav`; `main` i Streamlit Cloud bez zmian do akceptacji.
2. Lokalnie: pełna suita testów + uruchomienie aplikacji; zrzuty ekranu górnego menu, Pulpitu (z Premium i bez), widoku telefonu → do akceptacji użytkownika.
3. Po akceptacji: merge do `main`, push, weryfikacja na `gem-dashboard.streamlit.app` (każda sekcja menu, Pulpit, ekran blokady).
4. Dokumentacja:
   - `CLAUDE.md` projektu: nowa struktura `pages/<sekcja>/`, rejestr `components/nav.py`, mapa stary→nowy plik
   - skille `gem-dashboard-page` (nowa strona = plik w folderze sekcji + wpis w `PAGES`), `gem-dashboard-audit` (checklisty po nowych ścieżkach), `gem-dashboard-deploy` (bez zmian merytorycznych, sprawdzić ścieżki w przykładach)

## Poza zakresem

- Karta spółki, Mój portfel, AI, Puls rynku — kolejne podprojekty
- Zmiany w logice obliczeń, backtestach i źródłach danych
- Przebudowa wnętrza stron S&P 500 / GPW (8 zakładek zostaje; ich część „pojedyncza spółka” przejdzie do Karty spółki w podprojekcie 2)
- Zmiany na portalu inwestowanie.edu.pl (linkuje tylko do adresu głównego aplikacji)
