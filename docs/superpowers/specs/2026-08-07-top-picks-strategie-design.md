# Top Picks — druga i trzecia strategia (Earnings Momentum, Jakość biznesu)

**Data:** 2026-08-07
**Status:** Draft — czeka na review użytkownika
**Cel:** Rozszerzyć stronę `pages/9_top_picks.py` o dwie dodatkowe strategie w osobnych zakładkach: **Earnings Momentum** (SP500) i **Jakość biznesu** (SP500 + GPW). Każda z własnym append-only logiem i własnym `RULE_VERSION`.

## Kontekst

F18 (2026-08-06) dał jedną strategię — czyste momentum cenowe — z append-only logiem i miesięcznym GitHub Action. 2026-08-07 strona została przeniesiona na pozycję 9 (pod GPW) i przebudowana wizualnie (commit `d0f5201`).

Użytkownik chce drugiej i trzeciej reguły, żeby piątka nie opierała się na jednym wymiarze informacji. Momentum mówi **co zrobił kurs**; brakuje **co zrobił biznes** i **jaki ten biznes jest**.

## Pomiar pokrycia danych (2026-08-07, próbka 25 SP500 + 30 GPW)

To jest fundament wszystkich decyzji poniżej. Liczby zmierzone, nie założone:

| Sygnał | SP500 | GPW |
|---|---|---|
| earnings history ≥ 4Q | 100% | **10%** |
| earnings history brak | 0% | **80%** |
| rewizje `eps_trend` | 100% | 67% |
| ROE | 92% | 100% |
| P/E | 100% | 77% |
| FCF | 96% | 73% |

**Dwa wnioski, które przesądzają o zakresie:**

1. **GPW nie ma historii EPS.** 24 z 30 spółek próbki nie mają żadnych danych earnings (m.in. MIL, ING, ALR, GPW, PCO). Earnings Momentum obejmuje wyłącznie SP500. Precedens w kodzie: F16 Bulk Insider Screener też jest SP500-only.
2. **yfinance zwraca 4 kwartały, nie 8.** Żadna z 55 spółek nie miała ≥8Q; wszystkie SP500 miały dokładnie 4. Symulacja wstecz na tak krótkiej historii (~12 rebalansów miesięcznych) nie niesie informacji. **Obie nowe strategie są forward-only.**

Efekt uboczny pomiaru: `_compute_beat_streak()` i `ProgressColumn` w F13 deklarują zakres 0–8, a dane fizycznie kapują się na 4. Osobna sprawa, poza zakresem tego specu — do zgłoszenia użytkownikowi.

## Decyzje projektowe

| Pytanie | Wybór | Odrzucone alternatywy |
|---|---|---|
| Układ UI | 3 zakładki `st.tabs` na stronie 9 | Trzy osobne strony (rozmywa „Top Picks" jako jedno miejsce z typami); jedna zakładka z selectboxem strategii (chowa istnienie pozostałych) |
| Storage | Osobny plik JSON na strategię | Jeden plik z wymiarem strategii (wymaga migracji jedynego prawdziwego track recordu w aplikacji); jeden plik na miesiąc (rozsypuje katalog) |
| Earnings Momentum na GPW | Nie — info box wyjaśniający brak danych | Wpuścić te ~10% GPW z danymi (po progu płynności zostałoby kilka spółek — „wybór" z pustego zbioru); przemilczeć GPW (użytkownik nie wie, czy to decyzja, czy bug) |
| Symulacja wstecz nowych strategii | Brak — jawny komunikat, że track record narasta od dziś | Symulacja na 4 kwartałach (liczba wyglądałaby jak wynik, nie będąc nim); backfill loga (miesza symulowane z realnymi) |
| Rozszerzenie silnika | `select_picks(..., scorer=...)` — jeden opcjonalny kwarg | Osobne funkcje `select_picks_earnings()` / `_quality()` (trzy kopie filtra płynności i limitu sektorowego) |

## Architektura

### Kluczowy problem: scorery fundamentalne nie znają `asof`

`select_picks()` przyjmuje `asof` i obcina dane do tej daty — dzięki temu `simulate_rule()` może wołać ją w pętli po historycznych datach bez lookahead bias.

Scorery fundamentalne **fizycznie nie potrafią** tego uszanować: `get_ratios_snapshot()` i `get_earnings_history()` zwracają stan na dziś, niezależnie od tego, o jaką datę poprosisz. Gdyby wpiąć je w `simulate_rule()`, każda historyczna data dostałaby dzisiejsze fundamenty — lookahead bias w najczystszej postaci, i to cichy.

**Zabezpieczenie w typie, nie w komentarzu:** każdy scorer niesie flagę `supports_asof`. `simulate_rule()` sprawdza ją i podnosi `ValueError` przy scorerze bez wsparcia. Nie da się przypadkiem zasymulować strategii fundamentalnej.

```python
@dataclass(frozen=True)
class Scorer:
    name: str
    supports_asof: bool
    fn: Callable[[list[str], pd.DataFrame, pd.Timestamp], pd.Series]
```

### Silnik (`data/top_picks.py`)

`select_picks()` dostaje jeden opcjonalny kwarg. Sygnatura pozostaje wstecznie zgodna — wywołania bez `scorer` zachowują się identycznie, co jest kontraktem sprawdzanym przez istniejące 13 testów F18.

```python
def select_picks(prices, volumes, groups, asof,
                 top_n=5, max_per_group=2, min_turnover=0.0,
                 scorer: Scorer | None = None) -> list[dict]:
    # scorer=None -> MOMENTUM_SCORER (dotychczasowe zachowanie)
```

Niezmienione i wspólne dla wszystkich trzech strategii: filtr historii ≥273 sesji, filtr płynności (mediana obrotu 60d), limit `max_per_group` na sektor, top 5 równych wag, kształt zwracanego dicta (`ticker`/`group`/`score`/`entry_price`/`entry_date`/`weight`).

Trzy scorery:

| Scorer | `supports_asof` | Wejście | Ranking |
|---|---|---|---|
| `MOMENTUM_SCORER` | `True` | ceny | `latest_returns()` → `rank_based_score(12M .40 / 6M .30 / 3M .20 / 1M .10, anti_1m)` |
| `EARNINGS_SCORER` | `False` | `bulk_fetch_earnings_history()` + `fetch_earnings_trend()` | percentyl beat streak (0–4) `.40` + percentyl EPS surprise % ostatniego kwartału `.35` + percentyl rewizji konsensusu `.25` |

Rewizja konsensusu = zmiana szacunku EPS na **bieżący kwartał** (`0q`) w oknie **90 dni**, liczona z `fetch_earnings_trend()`: `(estimate_now − estimate_90d_ago) / |estimate_90d_ago|`. Dodatnia = analitycy podnoszą prognozy. Spółka bez kompletu trzech komponentów dostaje score renormalizowany do dostępnych wag (wzorzec `_flexible_score()`), a przy zerze dostępnych komponentów wypada z rankingu.
| `QUALITY_SCORER` | `False` | `bulk_fetch_universe()` | percentyl ROE `.30` + marża `.25` + wzrost przychodów `.25` + odwrócony percentyl debt/equity `.20` |

Wszystkie trzy zwracają `pd.Series` ticker → score w tej samej skali percentylowej (0–1), żeby liczba „score" na karcie znaczyła to samo w każdej zakładce.

**GPW w `QUALITY_SCORER`:** banki (`GPW_BANKS`) mają nieporównywalne debt/equity i marże. Reużywamy mechanizmu z F11/F12 — dla banków komponent debt/equity jest pomijany, a wagi pozostałych trzech renormalizowane do 1.0. Ten sam wzorzec co `_flexible_score()` w `momentum.py`.

### Storage

Trzy niezależne pliki, każdy w formacie identycznym z obecnym:

| Plik | Strategia | Rynki |
|---|---|---|
| `data/top_picks_history.json` | momentum | SP500 + GPW |
| `data/top_picks_earnings_history.json` | earnings | SP500 |
| `data/top_picks_quality_history.json` | quality | SP500 + GPW |
| `data/top_picks_sim.json` | symulacja momentum | bez zmian |

`load_history()` i `append_snapshot()` już przyjmują `path` — nie wymagają zmian. `portfolio_equity()` też działa bez modyfikacji, bo operuje na strukturze snapshotu, nie na ścieżce.

`RULE_VERSION` staje się słownikiem per strategia (`{"momentum": 1, "earnings": 1, "quality": 1}`), żeby zmiana wag jednej reguły nie unieważniała ostrzeżenia o mieszanych wersjach w pozostałych.

### Import Streamlita w silniku — świadome nadłamanie reguły F18

`data/top_picks.py` jest celowo wolny od Streamlita, żeby chodzić w GitHub Action. Nowe scorery potrzebują `data/financials.py`, który importuje `st` i dekoruje funkcje `@st.cache_data`.

Zweryfikowane 2026-08-07: poza runtime Streamlita te funkcje działają (`MemoryCacheStorageManager`, cache bez persystencji między procesami). Streamlit jest już w `requirements.txt`, więc Action go ma.

**Decyzja:** akceptujemy import, bo alternatywa (wyciąganie surowych fetcherów z `financials.py` do modułu bez Streamlita) to duży refaktor pod jedną funkcjonalność. **Warunek:** import `financials` siedzi wewnątrz funkcji scorera, nie na górze modułu — `data/top_picks.py` importowany sam z siebie (i wszystkie testy F18) nadal nie ciągnie Streamlita.

### CI (`scripts/update_top_picks.py`)

Jeden run liczy trzy strategie. Guardy pozostają per strategia i per rynek — niepełna piątka w jednej strategii nie może wywalić zapisu pozostałych, bo dziura w logu jest nieodwracalna (append-only).

Runtime rośnie z ~1m10s do szacowanych 10–15 min (bulk earnings 456 spółek + bulk ratios ~600, zimny cache w każdym runie — Action nie ma persystentnego cache'u parquet). Mieści się w limitach GitHub Actions z dużym zapasem.

Nowy guard: strategia, dla której pokrycie danych spadnie poniżej **80% universe po filtrze płynności** (ten sam próg co dziś dla momentum), **pomija zapis swojego snapshotu i loguje ostrzeżenie**, zamiast wywalać cały run. Momentum nie może paść przez to, że yfinance akurat nie oddał earningsów.

Pozostałe guardy F18 działają bez zmian dla każdej strategii osobno: niepełna piątka i grupa `"?"` blokują zapis danego snapshotu. Guard „ceny starsze niż 5 dni" dotyczy `entry_price`, więc obowiązuje wszystkie trzy strategie — ceny wejścia pochodzą z tego samego źródła niezależnie od scorera.

### UI (`pages/9_top_picks.py`)

Trzy zakładki `st.tabs`. Renderowanie jest wspólne — dzisiejszy kod sekcji „skład" i „wyniki live" idzie do funkcji przyjmującej `(history, markets, strategy_label)`, wołanej trzy razy. Komponenty z `cards.py` (`top_pick_cards`, `section_band`, `kpi_card`) i `charts.py` (`picks_return_bar`, `category_pie`, `equity_chart`) nie wymagają zmian.

Różnice per zakładka:

- **Momentum** — bez zmian, z sekcją symulacji
- **Earnings Momentum** — tylko SP500; pod piątką info box w stylu F16 wyjaśniający, że yfinance nie ma historii EPS dla ~80% GPW; zamiast symulacji komunikat o forward-only
- **Jakość biznesu** — SP500 + GPW; przy GPW nota o bankach i renormalizacji wag; zamiast symulacji komunikat o forward-only

Kolumny w expanderze „szczegóły" różnią się per strategia — dla earnings pokazujemy beat streak / surprise / rewizję, dla quality ROE / marżę / debt-equity. Momentum zostaje przy dzisiejszych kolumnach fundamentalnych jako kontekst.

## Poza zakresem

- Backfill logów nowych strategii — z definicji niemożliwy bez historycznych fundamentów
- Porównanie trzech strategii między sobą na jednym wykresie — sensowne dopiero po kilku rebalansach, osobna iteracja
- Naprawa `beat_streak` 0–8 vs 4 w F13 — osobna, niezależna sprawa
- Zmiana reguły momentum — nietykalna, chroni ją 13 testów i istniejący track record

## Ryzyka

| Ryzyko | Skutek | Mitygacja |
|---|---|---|
| Lookahead bias przy symulacji strategii fundamentalnej | Fałszywy wynik wyglądający wiarygodnie | `supports_asof=False` + `ValueError` w `simulate_rule()` |
| Zimny cache w Action wydłuża run | Timeout / koszt | Guard per strategia zamiast globalnego; limit Actions ma zapas |
| yfinance zmienia kształt `earnings_history` | Scorer zwraca pustkę | Guard pokrycia pomija zapis snapshotu zamiast zapisać niepełny |
| Skład quality prawie się nie zmienia miesiąc do miesiąca | Zakładka wygląda martwo | Świadome i zgodne z naturą sygnału; UI pokazuje datę ostatniej zmiany składu |

## Testy

- Istniejące 13 testów F18 przechodzą **bez zmiany treści** — kontrakt, że ścieżka momentum nie drgnęła
- `simulate_rule()` ze scorerem `supports_asof=False` podnosi `ValueError`
- Każdy scorer na sztucznych danych: kształt wyjścia, skala 0–1, obsługa NaN i pustego wejścia
- `QUALITY_SCORER` dla banku GPW: pominięty debt/equity, wagi zrenormalizowane do 1.0
- Limit sektorowy i próg płynności działają identycznie dla wszystkich trzech scorerów
- Guard pokrycia: strategia poniżej progu nie zapisuje snapshotu, pozostałe zapisują
