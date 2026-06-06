# Watchlist cross-feature domknięcie — design

**Data:** 2026-06-06
**Status:** Draft — czeka na review użytkownika
**Cel:** Rozszerzyć użycie `components/watchlist.py` (localStorage cross-feature, istnieje od F14) na 3 screenery: F12 Screener Fundamentalny, F13 Sprawozdania Q screener, F16 Bulk Insider Screener. Dodać filtr "⭐ Tylko watchlist" + edytowalną kolumnę ⭐ (toggle) w każdym.

## Kontekst

GEM Dashboard ma już:
- **`components/watchlist.py`** (F14, 2026-06-05, commit `e634b9e`) — `WATCHLIST_KEY = "gem_dashboard_watchlist_v1"` w localStorage przez `streamlit-local-storage`. API: `get_watchlist(ls)`, `save_watchlist(ls, set)`, `toggle_ticker(ls, ticker) -> bool`.
- **F14 Earnings Calendar** używa pełnego patternu (filter checkbox + ⭐ kolumna w `st.data_editor` z diff detection + `toggle_ticker` + `st.rerun`)

Watchlist jest **cross-feature module** — był zaplanowany do reuse od początku, ale faktycznie używany tylko w F14. F17 to **domknięcie** — pattern z F14 kopiowany do pozostałych screenerów:
- F12 Screener Fundamentalny (`tab6` w `pages/7_sp500.py` + `pages/8_gpw.py`)
- F13 Sprawozdania Q screener (`render_sprawozdania_screener` w `components/financials_ui.py`, wywoływana w `tab8` obu pages)
- F16 Bulk Insider Screener (`pages/23_insider_screener.py`)

## Scope MVP

**W MVP:**
- Filtr "⭐ Tylko watchlist" (checkbox w sekcji filtrów) w F12 + F13 + F16
- Kolumna ⭐ w tabeli (st.data_editor z `CheckboxColumn`, toggle przez diff detection + `toggle_ticker` + `st.rerun`) — **zamiana `st.dataframe` na `st.data_editor`** w 3 screenerach
- Session_state keys z `_v2` suffix dla nowych widgetów (cache safety przy zmianie z `st.dataframe`)
- Caption "Watchlist pusty — kliknij ⭐ w tabeli aby dodać" gdy `len(watchlist) == 0` i checkbox disabled

**Poza MVP (v2):**
- Standalone strona "Moje spółki" (`pages/24_watchlist.py`) — dashboard z key metrics per ticker w watchlist + linki do F13 deep dive
- Watchlist eksport / import JSON
- Watchlist sharing cloud (Supabase)
- Mini-dashboard watchlist w `app.py` sidebar (top-line metryki)

---

## Architektura

### Reuse `components/watchlist.py` bez zmian

API gotowe, używane już w F14:

```python
from streamlit_local_storage import LocalStorage
from components.watchlist import get_watchlist, toggle_ticker

ls = LocalStorage()
watchlist = get_watchlist(ls)  # set[str]
toggle_ticker(ls, "AAPL")  # bool: True jeśli w watchlist po toggle
```

Brak zmian w module. Jeśli okaże się że pattern integracji ma boilerplate — extract helpera w v2.

### Wzorzec integracji (kopia z F14)

Każdy screener dostaje **3 zmiany**:

**A. Imports + init (góra screenera):**
```python
from streamlit_local_storage import LocalStorage
from components.watchlist import get_watchlist, toggle_ticker

ls = LocalStorage()
watchlist = get_watchlist(ls)
```

**B. Filter checkbox (w sekcji filtrów obok pozostałych):**
```python
only_watchlist = st.checkbox(
    "⭐ Tylko watchlist",
    value=False,
    disabled=len(watchlist) == 0,
    help="Watchlist pusty — kliknij ⭐ w tabeli aby dodać." if not watchlist else None,
    key=f"{screener_prefix}_only_watchlist",
)
```

**C. Apply filter (po pozostałych filtrach):**
```python
if only_watchlist:
    filtered = filtered[filtered["ticker"].isin(watchlist)]
```

**D. Tabela z ⭐ kolumną (st.dataframe → st.data_editor):**
```python
display["in_watchlist"] = display["Ticker"].isin(watchlist)
cols_with_star = ["in_watchlist"] + [c for c in display_cols if c != "in_watchlist"]
display = display.rename(columns={"in_watchlist": "⭐"})

edited = st.data_editor(
    display[cols_with_star],
    column_config={
        "⭐": st.column_config.CheckboxColumn("⭐", width="small"),
        # ... reszta column_config bez zmian
    },
    disabled=[c for c in cols_with_star if c != "⭐"],
    hide_index=True,
    use_container_width=True,
    key=f"{screener_prefix}_table_v2",  # _v2 cache safety
)

diff_mask = edited["⭐"] != display["⭐"]
if diff_mask.any():
    for _, row in edited[diff_mask].iterrows():
        toggle_ticker(ls, row["Ticker"])
    st.rerun()
```

### Session_state keys per screener

| Screener | Prefix | Keys |
|----------|--------|------|
| F12 SP500 (tab6) | `sp500_screening` | `sp500_screening_only_watchlist`, `sp500_screening_table_v2` |
| F12 GPW (tab6) | `gpw_screening` | `gpw_screening_only_watchlist`, `gpw_screening_table_v2` |
| F13 SP500 (`render_sprawozdania_screener` market="SP500") | `SP500_sprawozdania` | `SP500_sprawozdania_only_watchlist`, `SP500_sprawozdania_table_v2` |
| F13 GPW (market="GPW") | `GPW_sprawozdania` | `GPW_sprawozdania_only_watchlist`, `GPW_sprawozdania_table_v2` |
| F16 (page 23) | `insider_screener` | `insider_screener_only_watchlist`, `insider_screener_table_v2` |

**`_v2` suffix obowiązkowy** — przy zmianie `st.dataframe` na `st.data_editor` ze starymi keys Streamlit może wystrzelić cache exception (`Cannot reuse key for different widget type`). Nowy key = clean state.

---

## Per-screener diffs

### F12 Screener Fundamentalny (`pages/7_sp500.py` + `pages/8_gpw.py` tab6)

**Lokalizacja:** wewnątrz `with tab6:` blok + `@st.fragment` w obu plikach.

**Aktualny stan:** `st.dataframe(filtered.head(top_n))` z 11 kolumnami (P/E, EV/EBITDA, ROE, FCF, etc.). Screener używa `bulk_fetch_universe` (cache 24h).

**Diff (po istniejących filtrach):**
1. Import `LocalStorage` + `get_watchlist`/`toggle_ticker` (na górze pliku)
2. `ls = LocalStorage(); watchlist = get_watchlist(ls)` (wewnątrz tab6, przed render)
3. Filter checkbox "⭐ Tylko watchlist" w sekcji filtrów (obok BUY only, sektor itp.)
4. Tabela → `st.data_editor` z ⭐ kolumną + diff detection + toggle + rerun

### F13 Sprawozdania Q screener (`components/financials_ui.py:render_sprawozdania_screener`)

**Lokalizacja:** funkcja `render_sprawozdania_screener(universe: list[str], market: str)` — wywoływana z `tab8` w `pages/7_sp500.py` (`market="SP500"`) i `pages/8_gpw.py` (`market="GPW"`).

**Aktualny stan:** `st.dataframe(filtered)` z 6 kolumnami (Ticker, Q, EPS est/act, EPS Δ%, Streak ProgressColumn). Filtry: Beat status, Min surprise, Min streak, Top N, Sort.

**Diff:**
1. Import `LocalStorage` + `get_watchlist`/`toggle_ticker` (na górze pliku — jeden raz)
2. Wewnątrz `render_sprawozdania_screener`: `ls = LocalStorage(); watchlist = get_watchlist(ls)`
3. Filter checkbox `f"{market}_sprawozdania_only_watchlist"`
4. Tabela `st.dataframe` → `st.data_editor` z ⭐ + diff + toggle + rerun
5. Klucz tabeli: `f"{market}_sprawozdania_table_v2"` (zamiast `f"{market}_screener_table"`)

### F16 Bulk Insider Screener (`pages/23_insider_screener.py`)

**Lokalizacja:** główny scope page.

**Aktualny stan:** `st.dataframe(display[display_cols])` z 11 kolumnami (sentiment, ticker, name, sektor, cap, net, buys, sells, top buyer, top fund, streak).

**Diff:**
1. Import `LocalStorage` + `get_watchlist`/`toggle_ticker` (góra)
2. Po `df = bulk_fetch_insider_screener(universe)` + `if df.empty: st.stop()`: `ls = LocalStorage(); watchlist = get_watchlist(ls)`
3. Filter checkbox `insider_screener_only_watchlist` w sekcji filtrów
4. Tabela → `st.data_editor` z ⭐ + diff + toggle + rerun
5. Klucz: `insider_screener_table_v2`

---

## Edge cases

### 1. Watchlist pusty + filtr aktywny
Checkbox `disabled=len(watchlist) == 0` + `help` text. Pattern z F14 — sprawdzone.

### 2. LocalStorage incognito mode
`get_watchlist` zwraca pusty `set()` (już obsługiwane w F14, test `test_watchlist_get_empty`). Watchlist degraduje się do session-only. Caption: "Watchlist nie persystuje w trybie prywatnym" — **opcjonalne**, w MVP nie dodajemy bo F14 też nie ma. v2 może dodać.

### 3. Streamlit `data_editor` rerun loop
**Krytyczne:** `diff_mask = edited["⭐"] != display["⭐"]` porównuje z `display` (pre-edit state), NIE `edited`. Po `toggle_ticker` + `st.rerun()` przy następnym render `watchlist` jest świeży z localStorage → `display["⭐"]` ma nowy stan → no diff → no loop.

Pattern z F14 — sprawdzony w produkcji.

### 4. Klucze widget cache konflikt
Zmiana `st.dataframe` (read-only) na `st.data_editor` (interactive) ze starym key → Streamlit `StreamlitDuplicateElementKey` lub `StreamlitMixedNumericTypesError`. **Fix:** `_v2` suffix przy każdym nowym kluczu (`sp500_screening_table_v2`, etc.). Stare klucze pozostają w session_state przeglądarki ale są ignorowane.

### 5. F13 universe vs watchlist mismatch
F13 screener używa universe `ALL_SP500_TICKERS` lub `ALL_GPW_TICKERS`. Watchlist może zawierać tickery z innego rynku (np. user dodał AAPL na page 22 Earnings Calendar, teraz patrzy na GPW screener). Filter `filtered = filtered[filtered["ticker"].isin(watchlist)]` poprostu nie pokaże nic — to OK, watchlist jest cross-market.

User edge case: "dlaczego pusto?" — caption helper text wyjaśnia.

### 6. F16 universe filter dla watchlist
F16 ma `bulk_fetch_insider_screener` które filtruje ETF na poziomie bulk. Watchlist może zawierać ETF (VOO, QQQ) z F14 calendar (gdzie nie filtrujemy bo ETF nie ma earnings, ale user mógł dodać). Filter `isin(watchlist)` po bulk → ETF nie pojawią się (bo nie ma ich w df). OK.

### 7. F12/F13/F16 — ⭐ pierwsza kolumna zamiast ostatniej
F14 pattern stawia ⭐ jako **pierwszą** kolumnę. Kopiujemy to. Wymaga zmiany `display_cols` lokalnie w każdym screenerze.

---

## Testing strategy

**Brak nowych unit testów** — pattern integracji to tylko boilerplate Streamlit calls (nie izolowana logika). Watchlist sam ma testy w `tests/test_calendar.py` (4 testy, pokrywają `get_watchlist`, `save_watchlist`, `toggle_ticker`).

**Manual QA matrix na produkcji:**
- [ ] F12 SP500 tab6 — ⭐ kolumna widoczna, checkbox "Tylko watchlist" działa, toggle ⭐ przy AAPL → reload page → state zachowany w localStorage
- [ ] F12 GPW tab6 — analogicznie z PKO.WA
- [ ] F13 SP500 tab8 screener — analogicznie
- [ ] F13 GPW tab8 screener — analogicznie
- [ ] F16 page 23 screener — analogicznie
- [ ] F14 page 22 Earnings Calendar — **bez zmian**, watchlist nadal działa (nie zepsuliśmy)
- [ ] Cross-screener: dodaj AAPL w F12 SP500 → idź do F16 → AAPL widoczny z ⭐ → filtr "Tylko watchlist" pokazuje AAPL
- [ ] Pusty watchlist — checkbox disabled, caption wyjaśnia

---

## Pliki do zmiany

**Modyfikowane (3 pliki + tests opcjonalne):**
- `pages/7_sp500.py` — import + tab6 (F12) + sprawdzić czy nie kolidują z istniejącymi imports z F13/F16
- `pages/8_gpw.py` — analogicznie
- `components/financials_ui.py` — `render_sprawozdania_screener` — import + body
- `pages/23_insider_screener.py` — import + body
- `CLAUDE.md` — F17 paragraph w Key Design Decisions

**Bez zmian:**
- `components/watchlist.py` — API gotowe
- `pages/22_earnings_calendar.py` (F14) — już ma watchlist
- `tests/` — pattern integracji nie wymaga nowych testów (logika watchlist już testowana w `test_calendar.py`)
- `app.py`, `components/auth.py` — sub-features, brak nowych pages w MVP

---

## Definition of Done

- [ ] `pages/7_sp500.py` tab6 (F12) ma checkbox + ⭐ kolumnę
- [ ] `pages/8_gpw.py` tab6 (F12) analogicznie
- [ ] `components/financials_ui.py:render_sprawozdania_screener` (F13) ma checkbox + ⭐ kolumnę dla obu market
- [ ] `pages/23_insider_screener.py` (F16) ma checkbox + ⭐ kolumnę
- [ ] Full test suite passing (52/52 — bez regresji)
- [ ] Manual QA matrix: 7 checków przeszło na produkcji
- [ ] `CLAUDE.md` F17 paragraph
- [ ] Commit + push do `m4x-dm/gem-dashboard` main
- [ ] Streamlit Cloud auto-deploy zweryfikowany
- [ ] MEMORY.md entry F17

---

## Szacowany czas

- Implementacja: ~2h (5 plików × 20-25 min każdy)
- Manual QA: ~30 min (cross-screener flow)
- **Total: ~2.5-3h** (jak rekomendowano przy wyborze "rozszerzony scope")
