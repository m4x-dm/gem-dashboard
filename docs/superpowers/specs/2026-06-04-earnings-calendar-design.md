# Earnings Calendar — design

**Data:** 2026-06-04
**Status:** Draft — czeka na review użytkownika
**Cel:** Nowa strona `pages/22_earnings_calendar.py` z kalendarzem nadchodzących i niedawnych raportów (±28 dni) dla SP500 + GPW, plus watchlist persystowany w localStorage, plus cross-link do F13 Sprawozdania Q.

## Kontekst

GEM Dashboard ma już:
- **F13 Sprawozdania Q** (2026-06-02, commit `8f73d6e`) — `data/financials.py` z `bulk_fetch_earnings_history` + `fetch_earnings_trend` + `fetch_quarterly_statements` + `fetch_annual_statements`
- 22 strony, 8 tabów per page 7+8
- Watchlist nie istnieje (cross-feature opportunity)
- `streamlit-local-storage` w `requirements.txt` (już używany)

Nowa funkcjonalność jest **naturalnym rozszerzeniem F13**: F13 patrzy wstecz (beat/miss historia), Calendar patrzy ±4 tyg. (przed-raportowe planowanie + post-raport refresher).

## Scope MVP

**W MVP:**
- Nowa strona `pages/22_earnings_calendar.py` (page 22, w sidebarze po GEM Extended page 21)
- Data layer (`data/financials.py` rozszerzony):
  - `fetch_earnings_dates(ticker, n_history=4, n_future=4)` — yfinance `Ticker.earnings_dates` + parquet cache 24h
  - `bulk_fetch_earnings_calendar(universe)` — ThreadPool 8 + retry + `@st.cache_data` + filter ETF (no earnings)
- Watchlist module (`components/watchlist.py` nowy) — localStorage, JSON array, cross-feature
- UI: tabela `st.data_editor` (z checkbox ⭐) + heatmapa Plotly 8 tygodni + 4 summary cards + filtry + CSV export
- Cross-link do F13: button "Pokaż szczegóły" → `st.switch_page` z session_state pre-set
- Tests: 7+ unit testów

**Effective universe: SP500 (456) + GPW (121) = 577.** ETF wyłączone — nie mają earnings (`Ticker.earnings_dates` zwraca empty dla VOO/QQQ/etc.).

**Poza MVP (v2):**
- ETF Distribution Calendar (dystrybucje/dywidendy)
- Email alerts z watchlistu
- Filtr "ile dni do raportu" slider
- Earnings calls transcripts integration
- Watchlist cloud sync (Supabase)

---

## Architektura

### Data layer (`data/financials.py` — dopisać po `bulk_fetch_earnings_history`)

```python
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_earnings_dates(ticker: str) -> pd.DataFrame | None:
    """Pobiera earnings dates dla tickera (z historia + future).

    yfinance Ticker.earnings_dates zwraca DF z indeksem DatetimeIndex
    (data raportu) + kolumnami: EPS Estimate, Reported EPS, Surprise(%).

    Returns DF z normalizowanymi kolumnami:
        eps_estimate, eps_actual, eps_surprise_pct, is_future, q_label
    Plus index DatetimeIndex (znormalizowany tz_localize(None)).
    None gdy brak danych.

    Cache parquet 24h: data/cache/earnings_dates/{ticker}.parquet
    """

@st.cache_data(ttl=86400, show_spinner="Pobieram kalendarz earnings…")
def bulk_fetch_earnings_calendar(
    tickers_tuple: tuple[str, ...],
    max_workers: int = 8,
    window_days: int = 28,
) -> pd.DataFrame:
    """Bulk fetch earnings dla universe (filtruje ETF — no earnings).

    Returns DataFrame z kolumnami:
        ticker, date, q_label, eps_estimate, eps_actual,
        eps_surprise_pct, is_future, sector, market, name

    Filter: data ± window_days od dziś.
    ThreadPool + retry exp backoff (jak bulk_fetch_earnings_history).
    """
```

**Reuse z F13:**
- `_quarter_label(date)` — bez zmian
- `_get_yf_session()` — curl_cffi session
- Retry pattern z `_fetch_earnings_for_one` (exp backoff 1s/2s/4s)
- Parquet cache pattern

### Watchlist module (`components/watchlist.py` — nowy)

```python
WATCHLIST_KEY = "gem_dashboard_watchlist_v1"

def get_watchlist(ls: LocalStorage) -> set[str]: ...
def save_watchlist(ls: LocalStorage, tickers: set[str]) -> None: ...
def toggle_ticker(ls: LocalStorage, ticker: str) -> bool: ...
```

JSON array sorted, version-suffixed klucz (`_v1` dla migracji).
Cross-feature — używać w F13 screener i v2 features.

### UI module-level helpers (`pages/22_earnings_calendar.py`)

Musimy mieć helpery na poziomie modułu (regula `@st.fragment` z d7c3407):
- `_status_badge(date, eps_act, eps_est) -> str`
- `_detect_market(ticker) -> str` ("SP500" / "GPW" / "ETF")
- `_navigate_to_deep_dive(ticker)` — `st.switch_page` z session_state pre-set
- `_render_heatmap(df, window_days)` — Plotly calendar heatmap
- `_render_calendar_table(df, ls, watchlist)` — main data_editor + edit detection

---

## UI

### Page layout (single page, no internal tabs)

```
┌─ HEADER ─────────────────────────────────────────────────────┐
│ 📅 Earnings Calendar — najbliższe i niedawne raporty         │
│ Window: ±28 dni · Universe: SP500 + GPW (577 spółek)        │
└──────────────────────────────────────────────────────────────┘

┌─ FILTRY (expander, default expanded) ────────────────────────┐
│ Market [SP500/GPW/All]   │  Sektor [multiselect]            │
│ Status [Future/Past/All] │  ⭐ Tylko watchlist               │
│ Sort [date/surprise/...] │  [🔄 Refresh cache]               │
└──────────────────────────────────────────────────────────────┘

┌─ SUMMARY (4 metryki) ────────────────────────────────────────┐
│ Total ±28d: X │ Future: Y (Z w tym tyg.) │ Past Beat: A / Miss: B │ Avg Δ% │
└──────────────────────────────────────────────────────────────┘

┌─ HEATMAPA (8 tyg., Plotly) ──────────────────────────────────┐
│        Pon Wt Śr Cz Pt                                      │
│ -3       ▒  ▒  ▒  3  ▒                                      │
│ -2       ▒  4  ▒  ▒  ▒                                      │
│ -1       ▒  ▒  5  7  ▒                                      │
│ 0        ▒  ▒ [DZIŚ]▒                                       │
│ +1       ▒  ▒  2  ▒  ▒                                      │
│ ...                                                          │
│ Hover: lista do 5 tickerów + ilość pozostałych              │
└──────────────────────────────────────────────────────────────┘

┌─ TABELA (st.data_editor) ────────────────────────────────────┐
│ ⭐│Ticker│Nazwa│Market│Sektor│Data│Q│EPS est│EPS act│Δ%│Status│
│ ☑│AAPL│Apple│SP500│Tech│2026-07-30│Q3'26│1.72│—│—│🔜 W26d│
│ ☐│JPM │JP Morgan│SP500│Fin│2026-05-15│Q1'26│4.20│4.55│+8.3%│✅ Beat│
└──────────────────────────────────────────────────────────────┘

┌─ DEEP DIVE (selectbox + button) ─────────────────────────────┐
│ Wybierz ticker: [selectbox]  [📈 Pokaż szczegóły]             │
└──────────────────────────────────────────────────────────────┘

[📥 Eksport CSV]
```

### Tabela kolumny

| Kol | Typ | Width | Źródło |
|-----|-----|-------|--------|
| ⭐ | CheckboxColumn | small | localStorage watchlist |
| Ticker | str | small | universe |
| Nazwa | str | medium | `SP500_NAMES` / `GPW_CATEGORIES` |
| Market | str (badge) | small | "SP500" / "GPW" |
| Sektor | str | medium | `SP500_SECTOR_MAP` / WIG index |
| Data | datetime | medium | `earnings_dates.index` |
| Q | str | small | `_quarter_label(date)` |
| EPS est | NumberColumn 2dec | small | `epsEstimate` |
| EPS act | NumberColumn 2dec / "—" | small | `epsActual` (None dla future) |
| Δ% | NumberColumn signed % | small | `surprisePercent` |
| Status | str (badge) | medium | `_status_badge()` |

### `_status_badge` logika

```python
def _status_badge(date, eps_act, eps_est) -> str:
    today = pd.Timestamp.now().normalize()
    days_diff = (pd.Timestamp(date).normalize() - today).days

    if days_diff > 0:  # Future
        if days_diff <= 7:
            return f"🔜 W {days_diff}d"
        elif days_diff <= 14:
            return f"⏰ W {days_diff}d"
        else:
            return f"📅 {pd.Timestamp(date).strftime('%d.%m')}"
    elif days_diff == 0:
        return "🔥 DZIŚ"
    else:  # Past
        if pd.notna(eps_act) and pd.notna(eps_est):
            if eps_act > eps_est:
                return f"✅ Beat ({abs(days_diff)}d temu)"
            return f"❌ Miss ({abs(days_diff)}d temu)"
        return f"⚪ {abs(days_diff)}d temu"
```

### Default sort

"Data (najbliżej dziś)" — by abs(days_diff) ascending.

Inne opcje: "Data chronologicznie", "EPS surprise % (past)", "Ticker A-Z".

### Heatmapa Plotly

- 8 wierszy (tygodnie: -3 do +4)
- 5 kolumn (Pon-Pt; weekendy ukryte)
- Komórka = jeden dzień. Kolor = ilość raportów (0=bg gray, max=intense gold)
- Liczba w celli gdy >0
- Past dni opacity 0.6, future opacity 1.0
- Dziś = 1px czerwona ramka (#EF4444)
- Hover: tooltip z listą tickerów (max 5 + "+ N więcej")

### Watchlist UI w tabeli

`st.data_editor` z `CheckboxColumn("⭐", width="small")`. Pozostałe kolumny `disabled`. Po edycji:

```python
edited = st.data_editor(display_df, column_config=..., disabled=...)

# Diff toggles
diff = edited["in_watchlist"] != display_df["in_watchlist"]
for _, row in edited[diff].iterrows():
    toggle_ticker(ls, row["ticker"])

if diff.any():
    st.rerun()  # refresh state
```

### Cross-link "Pokaż szczegóły"

Selectbox + button poza tabelą:

```python
selected = st.selectbox(
    "Wybierz ticker do deep dive:",
    options=[""] + filtered["ticker"].tolist(),
    key="calendar_deep_dive_select",
)
if st.button("📈 Pokaż szczegóły", disabled=not selected):
    _navigate_to_deep_dive(selected)


def _navigate_to_deep_dive(ticker):
    market = _detect_market(ticker)
    if market == "SP500":
        st.session_state["sp500_deep_dive_ticker"] = ticker
        st.session_state["sp500_pending_view"] = "deep_dive"
        st.switch_page("pages/7_sp500.py")
    elif market == "GPW":
        st.session_state["gpw_deep_dive_ticker"] = ticker
        st.session_state["gpw_pending_view"] = "deep_dive"
        st.switch_page("pages/8_gpw.py")
    else:  # ETF — defensywne, ale ETF wykluczone z universe na poziomie fetch
        st.warning(f"Deep dive niedostępny dla ETF ({ticker}).")
```

Pattern session_state zgodny z F13 hotfix (commit `b1f8502`). ETF gałąź jest defensywna — ETF są filtrowane na poziomie `bulk_fetch_earnings_calendar`, więc nigdy nie powinny pojawić się w tabeli kalendarza. Gdyby ktoś dodał ETF do watchlistu manualnie (przyszły feature) — pokazujemy warning zamiast crashu.

---

## Cache i performance

### Cache strategy

| Dane | Klucz | TTL | Lokalizacja |
|------|-------|-----|-------------|
| `fetch_earnings_dates(ticker)` | ticker | 24h | `data/cache/earnings_dates/{ticker}.parquet` |
| `bulk_fetch_earnings_calendar()` | hash(universe) | 24h | `@st.cache_data` in-memory |
| Watchlist | `gem_dashboard_watchlist_v1` | persistent | browser localStorage |

### Performance budget

| Akcja | Budżet |
|-------|--------|
| Cold cache (577 tickerów) | <2 min |
| Warm cache (in-memory) | <1 sek |
| Heatmap render | <0.5 sek |
| Filter/sort (client-side) | <0.3 sek |
| Cross-link → page switch | <2 sek |

---

## Edge cases

### 1. yfinance pusty DF
Small cap GPW + niektóre spółki bez earnings coverage. Skutek: NaN row, pomijane przy filtrowaniu po dacie (NaT).

### 2. ETF — no earnings
`Ticker('VOO').earnings_dates` zwraca empty. Filter na data layer: `tickers = [t for t in universe if t not in ETF_TYPES]`. ETF set ładowany z `etf_universe.ETF_UNIVERSE.keys()`.

### 3. Fiskalny ≠ kalendarzowy Q
Apple ma fiskalny Q1 w Oct-Dec. `_quarter_label` używa **kalendarzowego Q daty publikacji**. Caption pod tabelą: *"Q label = kwartał kalendarzowy daty publikacji. Spółki o niestandardowym roku fiskalnym mogą mieć rozbieżne 'Q wewnętrzne'."*

### 4. Time zones
yfinance daty z różnymi TZ. Normalizujemy: `df.index = pd.to_datetime(df.index).tz_localize(None).normalize()`.

### 5. localStorage niedostępny (incognito)
Watchlist degraduje się do session-only. Caption: *"Watchlist nie persystuje w trybie prywatnym przeglądarki."*

### 6. Pusty watchlist + checkbox "Tylko watchlist"
Checkbox disabled gdy `len(watchlist) == 0`. Caption: "Watchlist pusty — kliknij ⭐ w tabeli."

### 7. Pusta heatmapa
Wszystkie dni 0 (np. po restrykcyjnym filtrze). Pokazujemy heatmapę z szarym tłem + caption "Brak raportów w wybranym oknie".

### 8. Cache invalidation gdy day shift
Window przesuwa się każdego dnia. Cache parquet zawiera ±20 dat z yfinance, więc `bulk_fetch` re-filtruje `is_future = date > now` na każdym renderze (cheap).

### 9. `@st.fragment` pułapka (jak F13)
Wszystkie helpery (`_status_badge`, `_detect_market`, `_navigate_to_deep_dive`, `_render_heatmap`, `_render_calendar_table`) MUSZĄ być na poziomie modułu PRZED `@st.fragment` blokiem. Patrz: F12 commit `d7c3407`, F13 build pattern.

### 10. Streamlit `data_editor` rerun loop
Po `toggle_ticker(ls, ...)` → `st.rerun()` może triggerować zapętlenie. Diff detection musi porównywać `in_watchlist` z **prev state** (session_state) nie current display_df.

---

## Testing strategy

**Nowy plik `tests/test_calendar.py`** (~7 testów):

```python
def test_quarter_label_consistent_z_F13():
    """_quarter_label spójny z F13."""

def test_status_badge_future_within_week():
    """Date dziś+3 → status '🔜 W 3d'."""

def test_status_badge_past_beat():
    """Date dziś-5, eps_act > eps_est → '✅ Beat (5d temu)'."""

def test_status_badge_past_miss():
    """Date dziś-5, eps_act < eps_est → '❌ Miss (5d temu)'."""

def test_status_badge_today():
    """Date dziś → '🔥 DZIŚ'."""

def test_detect_market_sp500():
    assert _detect_market("AAPL") == "SP500"

def test_detect_market_gpw():
    assert _detect_market("PKO.WA") == "GPW"

def test_detect_market_etf():
    assert _detect_market("VOO") == "ETF"

def test_bulk_fetch_filters_etf():
    """ETF tickery nie powinny być fetchowane przez yfinance."""

def test_watchlist_toggle_add():
    """Toggle empty watchlist + AAPL → ['AAPL']."""

def test_watchlist_toggle_remove():
    """Toggle ['AAPL','MSFT'] + AAPL → ['MSFT']."""

def test_watchlist_corrupt_json():
    """getItem zwraca '!@#invalid' → get_watchlist zwraca set()."""
```

**Manual QA na produkcji:**
- AAPL — najbliższy raport poprawnie wyśrodkowany (Q3'26 ~2026-07-30)
- JPM — past beat z Q1'26
- 11B.WA — może mieć NaN row (small cap GPW)
- VOO / QQQ — sprawdzić że filtrowane out, brak crashu
- Watchlist: dodać 3 tickery, F5 page, sprawdzić persystencję
- Cross-link: klik "Pokaż szczegóły" AAPL → land na page 7 tab 8 deep dive AAPL z pre-set ticker

---

## Pliki do utworzenia / zmiany

**Nowe pliki:**
- `pages/22_earnings_calendar.py` (~250 LOC)
- `components/watchlist.py` (~60 LOC)
- `tests/test_calendar.py` (~150 LOC)
- `data/cache/earnings_dates/` (auto-create katalog)

**Modyfikowane:**
- `data/financials.py` — dopisać `fetch_earnings_dates` + `bulk_fetch_earnings_calendar` + import `etf_universe.ETF_UNIVERSE` (do filter)
- `components/auth.py` — `PAGE_INFO` dodać entry `22: ("📅", "Earnings Calendar", "Kalendarz nadchodzących i niedawnych raportów…")` (mapping istnieje — page 21 jest w pliku)
- `app.py` — dodać kartę dla page 22 w gridzie (analogicznie do entry page 21 w linii 43: tuple `(num, icon, title, desc, path)`)
- `CLAUDE.md` — sekcja "Pages" + nowy F14 w Key Design Decisions

**Bez zmian:**
- `pages/7_sp500.py`, `pages/8_gpw.py` — F13 funkcjonuje, tylko reagują na pre-set session_state (już działa)
- `components/financials_ui.py` — F13 deep dive bez zmian

---

## Definition of Done

- [ ] `fetch_earnings_dates` + `bulk_fetch_earnings_calendar` w `data/financials.py` z parquet cache + retry
- [ ] `components/watchlist.py` z localStorage (toggle/get/save)
- [ ] `pages/22_earnings_calendar.py` z full UI (header + filtry + summary + heatmapa + tabela + cross-link + CSV)
- [ ] `tests/test_calendar.py` — 10+ unit testów PASS
- [ ] Manual QA matrix: AAPL/JPM/11B.WA/VOO/Watchlist/Cross-link wszystko ✓
- [ ] `app.py` + `auth.py` + `CLAUDE.md` zaktualizowane
- [ ] Commit + push do `m4x-dm/gem-dashboard` main
- [ ] Streamlit Cloud auto-deploy zweryfikowany
- [ ] MEMORY.md entry o nowym feature
