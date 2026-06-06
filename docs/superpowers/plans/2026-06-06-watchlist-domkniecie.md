# Watchlist cross-feature domknięcie Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rozszerzyć `components/watchlist.py` (cross-feature module z F14) na 3 screenery: F12 Screener Fundamentalny (tab6 SP500+GPW), F13 Sprawozdania Q screener (`render_sprawozdania_screener`), F16 Bulk Insider Screener. Filtr "⭐ Tylko watchlist" + edytowalna kolumna ⭐ z toggle w każdym.

**Architecture:** `st.dataframe` → `st.data_editor` z `CheckboxColumn("⭐")` + diff detection + `toggle_ticker(ls, ticker)` + `st.rerun()`. Pattern skopiowany z F14 (sprawdzony w produkcji). F12 wymaga dodatkowej zmiany: zastąpienie `on_select="rerun"` selectboxem + button "Pokaż w 💰 Finanse" (analogicznie do cross-link F13/F16) — `st.data_editor` nie obsługuje on_select.

**Tech Stack:** Streamlit 1.55+ (`st.data_editor` z `CheckboxColumn`), `streamlit_local_storage` (już w requirements), pandas 2.0+. Brak nowych zależności.

**Reference:** Spec `docs/superpowers/specs/2026-06-06-watchlist-domkniecie-design.md` (commit `dd38cb5`).

---

## File Structure

**Modyfikujemy (4 pliki):**
- `pages/7_sp500.py` — tab6 F12 Screener Fundamentalny (import + checkbox + data_editor + selectbox-finanse)
- `pages/8_gpw.py` — tab6 analogicznie do SP500
- `components/financials_ui.py` — `render_sprawozdania_screener` (F13, działa dla obu market)
- `pages/23_insider_screener.py` — F16
- `CLAUDE.md` — F17 paragraph

**Bez zmian:**
- `components/watchlist.py` — API gotowe, F14 używa
- `pages/22_earnings_calendar.py` — F14 już ma watchlist
- `tests/` — brak nowych testów (pattern integracji to boilerplate Streamlit, sam watchlist już testowany w `tests/test_calendar.py` z F14)
- `app.py`, `components/auth.py` — sub-features, brak nowych pages

---

## Task 1: F12 Screener Fundamentalny w `pages/7_sp500.py` (tab6 SP500)

**Files:**
- Modify: `pages/7_sp500.py:tab6`

- [ ] **Step 1.1: Dodać importy na górze pliku**

Znajdź sekcję importów (linie ~1-40). Po istniejącym `from components.auth import require_premium` dopisz:

```python
from streamlit_local_storage import LocalStorage
from components.watchlist import get_watchlist, toggle_ticker
```

- [ ] **Step 1.2: Sprawdzić obecny stan tab6 (linia ~584)**

```bash
sed -n '670,700p' pages/7_sp500.py
```

Powinieneś zobaczyć:
```python
df_display = _format_screener_df(df_sorted, currency_sym="$")
sel = st.dataframe(
    df_display, height=500, use_container_width=True,
    on_select="rerun", selection_mode="single-row",
)
if sel and hasattr(sel, "selection") and sel.selection.rows:
    clicked = df_display.index[sel.selection.rows[0]]
    st.session_state["sp_finanse_ticker"] = clicked
    st.info(f"✓ Wybrano **{clicked}** — przelacz na tab 💰 Finanse aby zobaczyc szczegoly")
```

- [ ] **Step 1.3: Dodać `ls + watchlist + filter checkbox` przed renderem tabeli**

Znajdź linię z `df_display = _format_screener_df(df_sorted, currency_sym="$")`. **PRZED** nią dopisz blok z filtrem watchlist. Pełna zamiana sekcji od `_render_screener_summary` do tabeli włącznie:

Znajdź:
```python
# 5. Summary cards
_render_screener_summary(df_sorted, total=len(df_full))
st.markdown("---")

# 6. Tabela
df_display = _format_screener_df(df_sorted, currency_sym="$")
sel = st.dataframe(
    df_display, height=500, use_container_width=True,
    on_select="rerun", selection_mode="single-row",
)
if sel and hasattr(sel, "selection") and sel.selection.rows:
    clicked = df_display.index[sel.selection.rows[0]]
    st.session_state["sp_finanse_ticker"] = clicked
    st.info(f"✓ Wybrano **{clicked}** — przelacz na tab 💰 Finanse aby zobaczyc szczegoly")
```

Zamień na:
```python
# 5. Summary cards
_render_screener_summary(df_sorted, total=len(df_full))
st.markdown("---")

# 5b. Watchlist (F17)
ls = LocalStorage()
watchlist = get_watchlist(ls)
only_watchlist = st.checkbox(
    "⭐ Tylko watchlist",
    value=False,
    disabled=len(watchlist) == 0,
    help="Watchlist pusty — kliknij ⭐ w tabeli aby dodac." if not watchlist else None,
    key="sp500_screening_only_watchlist",
)
if only_watchlist:
    df_sorted = df_sorted[df_sorted.index.isin(watchlist)]

# 6. Tabela z ⭐ kolumna (st.data_editor zamiast st.dataframe)
df_display = _format_screener_df(df_sorted, currency_sym="$")
df_display.insert(0, "⭐", df_display.index.isin(watchlist))
edited = st.data_editor(
    df_display,
    height=500,
    use_container_width=True,
    column_config={
        "⭐": st.column_config.CheckboxColumn("⭐", width="small"),
    },
    disabled=[c for c in df_display.columns if c != "⭐"],
    key="sp500_screening_table_v2",
)
# Diff detection -> toggle watchlist
diff_mask = edited["⭐"] != df_display["⭐"]
if diff_mask.any():
    for ticker in edited[diff_mask].index:
        toggle_ticker(ls, ticker)
    st.rerun()

# 6b. Selectbox + button -> pre-fill tab 💰 Finanse (zamiast on_select)
st.markdown("---")
col_sel, col_btn = st.columns([3, 1])
with col_sel:
    selected_finanse = st.selectbox(
        "Wybierz ticker do tab '💰 Finanse':",
        options=[""] + df_sorted.index.tolist(),
        key="sp500_screening_finanse_select",
    )
with col_btn:
    st.write("")  # spacer
    show_btn = st.button(
        "💰 Pokaz w Finanse",
        key="sp500_screening_show_finanse",
        disabled=not selected_finanse,
    )
if show_btn and selected_finanse:
    st.session_state["sp_finanse_ticker"] = selected_finanse
    st.info(f"✓ Wybrano **{selected_finanse}** — przelacz na tab 💰 Finanse aby zobaczyc szczegoly")
```

- [ ] **Step 1.4: Syntax + regression**

```bash
./venv/Scripts/python.exe -c "
import ast
with open('pages/7_sp500.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('Syntax OK')
" && ./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```

Expected: Syntax OK + 52/52 PASS.

- [ ] **Step 1.5: Commit**

```bash
git add pages/7_sp500.py
git commit -m "Add watchlist do F12 SP500 (tab6): filter + ⭐ kolumna + selectbox-finanse"
```

---

## Task 2: F12 GPW w `pages/8_gpw.py` (tab6 GPW)

**Files:**
- Modify: `pages/8_gpw.py:tab6`

- [ ] **Step 2.1: Recon — znaleźć tab6 + obecną tabelę w GPW**

```bash
grep -n "with tab6\|st.dataframe\|sp_finanse_ticker\|gpw_finanse_ticker" pages/8_gpw.py | head -10
```

Sprawdź czy struktura jest analogiczna do SP500 (powinna być — tab6 to F12 Screener Fundamentalny, ten sam moduł).

- [ ] **Step 2.2: Dodać importy**

Po `from components.auth import require_premium` w `pages/8_gpw.py`:

```python
from streamlit_local_storage import LocalStorage
from components.watchlist import get_watchlist, toggle_ticker
```

(Jeśli imports już są — np. ktoś dodał je inną drogą — pomiń. `grep -n "from components.watchlist" pages/8_gpw.py` żeby sprawdzić.)

- [ ] **Step 2.3: Zastąpić tab6 tabelę analogicznie do SP500**

Znajdź sekcję analogiczną do SP500 tab6 (zwykle wzór: `_render_screener_summary` → tabela → on_select check → CSV).

Zamień bloki:
```python
# 5. Summary cards
_render_screener_summary(df_sorted, total=len(df_full))
st.markdown("---")

# 6. Tabela
df_display = _format_screener_df(df_sorted, currency_sym="zl")
sel = st.dataframe(
    df_display, height=500, use_container_width=True,
    on_select="rerun", selection_mode="single-row",
)
if sel and hasattr(sel, "selection") and sel.selection.rows:
    clicked = df_display.index[sel.selection.rows[0]]
    st.session_state["gpw_finanse_ticker"] = clicked
    st.info(f"✓ Wybrano **{clicked}** — przelacz na tab 💰 Finanse aby zobaczyc szczegoly")
```

Zamień na:
```python
# 5. Summary cards
_render_screener_summary(df_sorted, total=len(df_full))
st.markdown("---")

# 5b. Watchlist (F17)
ls = LocalStorage()
watchlist = get_watchlist(ls)
only_watchlist = st.checkbox(
    "⭐ Tylko watchlist",
    value=False,
    disabled=len(watchlist) == 0,
    help="Watchlist pusty — kliknij ⭐ w tabeli aby dodac." if not watchlist else None,
    key="gpw_screening_only_watchlist",
)
if only_watchlist:
    df_sorted = df_sorted[df_sorted.index.isin(watchlist)]

# 6. Tabela z ⭐ kolumna
df_display = _format_screener_df(df_sorted, currency_sym="zl")
df_display.insert(0, "⭐", df_display.index.isin(watchlist))
edited = st.data_editor(
    df_display,
    height=500,
    use_container_width=True,
    column_config={
        "⭐": st.column_config.CheckboxColumn("⭐", width="small"),
    },
    disabled=[c for c in df_display.columns if c != "⭐"],
    key="gpw_screening_table_v2",
)
diff_mask = edited["⭐"] != df_display["⭐"]
if diff_mask.any():
    for ticker in edited[diff_mask].index:
        toggle_ticker(ls, ticker)
    st.rerun()

# 6b. Selectbox + button -> pre-fill tab 💰 Finanse
st.markdown("---")
col_sel, col_btn = st.columns([3, 1])
with col_sel:
    selected_finanse = st.selectbox(
        "Wybierz ticker do tab '💰 Finanse':",
        options=[""] + df_sorted.index.tolist(),
        key="gpw_screening_finanse_select",
    )
with col_btn:
    st.write("")
    show_btn = st.button(
        "💰 Pokaz w Finanse",
        key="gpw_screening_show_finanse",
        disabled=not selected_finanse,
    )
if show_btn and selected_finanse:
    st.session_state["gpw_finanse_ticker"] = selected_finanse
    st.info(f"✓ Wybrano **{selected_finanse}** — przelacz na tab 💰 Finanse aby zobaczyc szczegoly")
```

- [ ] **Step 2.4: Syntax + regression**

```bash
./venv/Scripts/python.exe -c "
import ast
with open('pages/8_gpw.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('Syntax OK')
" && ./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```

Expected: Syntax OK + 52/52 PASS.

- [ ] **Step 2.5: Commit**

```bash
git add pages/8_gpw.py
git commit -m "Add watchlist do F12 GPW (tab6): filter + ⭐ kolumna + selectbox-finanse"
```

---

## Task 3: F13 `render_sprawozdania_screener` w `components/financials_ui.py`

**Files:**
- Modify: `components/financials_ui.py:render_sprawozdania_screener`

- [ ] **Step 3.1: Dodać importy**

Na górze `components/financials_ui.py` (po istniejących `from components.constants import ...`) dopisz:

```python
from streamlit_local_storage import LocalStorage
from components.watchlist import get_watchlist, toggle_ticker
```

- [ ] **Step 3.2: Znaleźć funkcję `render_sprawozdania_screener`**

```bash
grep -n "def render_sprawozdania_screener\|st.dataframe" components/financials_ui.py | head -3
```

Linia ~143 powinna mieć `st.dataframe(display, ...)`.

- [ ] **Step 3.3: Dodać watchlist init na początku funkcji + filter checkbox w sekcji filtrów**

Znajdź wewnątrz `render_sprawozdania_screener` po istniejących filtrach (Beat status, Min surprise, Min streak), DODAJ nowy filter checkbox PRZED bulk fetch (`df = bulk_fetch_earnings_history(tuple(universe))`):

```python
# Watchlist (F17)
ls = LocalStorage()
watchlist = get_watchlist(ls)
only_watchlist = st.checkbox(
    "⭐ Tylko watchlist",
    value=False,
    disabled=len(watchlist) == 0,
    help="Watchlist pusty — kliknij ⭐ w tabeli aby dodac." if not watchlist else None,
    key=f"{market}_sprawozdania_only_watchlist",
)
```

Po `filtered = filtered.sort_values(...)` (przed `display = filtered.rename(...)`) DODAJ filter apply:

```python
if only_watchlist:
    filtered = filtered[filtered["ticker"].isin(watchlist)]
```

- [ ] **Step 3.4: Zamienić `st.dataframe` na `st.data_editor` z ⭐ kolumną**

Znajdź:
```python
st.dataframe(
    display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "EPS est": st.column_config.NumberColumn(format="%.2f"),
        "EPS act": st.column_config.NumberColumn(format="%.2f"),
        "EPS Δ%": st.column_config.NumberColumn(format="%+.1f%%"),
        "Streak": st.column_config.ProgressColumn(
            min_value=0, max_value=8, format="%d Q",
        ),
    },
)
```

Zamień na:
```python
# Dodaj ⭐ kolumna jako pierwsza
display.insert(0, "⭐", display["Ticker"].isin(watchlist))

edited = st.data_editor(
    display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "⭐": st.column_config.CheckboxColumn("⭐", width="small"),
        "EPS est": st.column_config.NumberColumn(format="%.2f"),
        "EPS act": st.column_config.NumberColumn(format="%.2f"),
        "EPS Δ%": st.column_config.NumberColumn(format="%+.1f%%"),
        "Streak": st.column_config.ProgressColumn(
            min_value=0, max_value=8, format="%d Q",
        ),
    },
    disabled=[c for c in display.columns if c != "⭐"],
    key=f"{market}_sprawozdania_table_v2",
)
# Diff detection -> toggle watchlist
diff_mask = edited["⭐"] != display["⭐"]
if diff_mask.any():
    for _, row in edited[diff_mask].iterrows():
        toggle_ticker(ls, row["Ticker"])
    st.rerun()
```

- [ ] **Step 3.5: Syntax + regression**

```bash
./venv/Scripts/python.exe -c "
import ast
with open('components/financials_ui.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('Syntax OK')
" && ./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```

Expected: Syntax OK + 52/52 PASS.

- [ ] **Step 3.6: Commit**

```bash
git add components/financials_ui.py
git commit -m "Add watchlist do F13 render_sprawozdania_screener: filter + ⭐ kolumna (oba market)"
```

---

## Task 4: F16 `pages/23_insider_screener.py`

**Files:**
- Modify: `pages/23_insider_screener.py`

- [ ] **Step 4.1: Dodać importy**

Po istniejących `from data.financials import ...` w `pages/23_insider_screener.py`:

```python
from streamlit_local_storage import LocalStorage
from components.watchlist import get_watchlist, toggle_ticker
```

- [ ] **Step 4.2: Dodać `ls + watchlist + filter checkbox` w sekcji filtrów**

Znajdź sekcję filtrów (`with st.expander("Filtry", expanded=True):`). Wewnątrz `with c3:` (gdzie są: Min Cap, Sort by, Top N, Refresh) DODAJ filter watchlist:

```python
with c3:
    cap_options = [...]
    min_cap_choice = st.selectbox(...)
    sort_by = st.selectbox(...)
    top_n = st.selectbox(...)
    
    # F17 watchlist filter
    ls = LocalStorage()
    watchlist = get_watchlist(ls)
    only_watchlist = st.checkbox(
        "⭐ Tylko watchlist",
        value=False,
        disabled=len(watchlist) == 0,
        help="Watchlist pusty — kliknij ⭐ w tabeli aby dodac." if not watchlist else None,
        key="insider_screener_only_watchlist",
    )
    
    if st.button("🔄 Refresh cache", key="insider_screener_refresh"):
        ...
```

Po istniejących `if sector_filter: ...`, `if status_filter: ...` itd. DODAJ apply filter:

```python
if only_watchlist:
    filtered = filtered[filtered["ticker"].isin(watchlist)]
```

- [ ] **Step 4.3: Zamienić `st.dataframe` na `st.data_editor` z ⭐ kolumną**

Znajdź sekcję 2 (tabela screener):
```python
st.dataframe(
    display[display_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Cap": st.column_config.NumberColumn("Cap", format="$%.0f"),
        "Net 6mc": st.column_config.NumberColumn("Net 6mc", format="$%+.0f"),
        "Streak": st.column_config.ProgressColumn(
            "Streak", min_value=0, max_value=6, format="%d mc",
        ),
    },
)
```

Zamień na:
```python
# Dodaj ⭐ kolumna jako pierwsza
display.insert(0, "⭐", display["Ticker"].isin(watchlist))
display_cols_with_star = ["⭐"] + display_cols

edited = st.data_editor(
    display[display_cols_with_star],
    use_container_width=True,
    hide_index=True,
    column_config={
        "⭐": st.column_config.CheckboxColumn("⭐", width="small"),
        "Cap": st.column_config.NumberColumn("Cap", format="$%.0f"),
        "Net 6mc": st.column_config.NumberColumn("Net 6mc", format="$%+.0f"),
        "Streak": st.column_config.ProgressColumn(
            "Streak", min_value=0, max_value=6, format="%d mc",
        ),
    },
    disabled=[c for c in display_cols_with_star if c != "⭐"],
    key="insider_screener_table_v2",
)
# Diff detection -> toggle watchlist
diff_mask = edited["⭐"] != display[display_cols_with_star]["⭐"]
if diff_mask.any():
    for _, row in edited[diff_mask].iterrows():
        toggle_ticker(ls, row["Ticker"])
    st.rerun()
```

- [ ] **Step 4.4: Syntax + regression**

```bash
./venv/Scripts/python.exe -c "
import ast
with open('pages/23_insider_screener.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('Syntax OK')
" && ./venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```

Expected: Syntax OK + 52/52 PASS.

- [ ] **Step 4.5: Commit**

```bash
git add pages/23_insider_screener.py
git commit -m "Add watchlist do F16 Insider Screener: filter + ⭐ kolumna"
```

---

## Task 5: CLAUDE.md F17 + Final QA + push + MEMORY.md

**Files:**
- Modify: `CLAUDE.md`
- Modify: `C:\Users\m4x\.claude\projects\C--Users-m4x-Desktop-AI-ebook-white-new-A4\memory\MEMORY.md`
- Create: `C:\Users\m4x\.claude\projects\C--Users-m4x-Desktop-AI-ebook-white-new-A4\memory\project_gem_dashboard_watchlist_domkniecie.md`

- [ ] **Step 5.1: Dopisać F17 paragraph w `CLAUDE.md`**

Znajdź wpis F16 w Key Design Decisions. Dopisz po nim:

```markdown
- **Watchlist cross-feature domknięcie (F17):** Rozszerzenie `components/watchlist.py` (z F14) na 3 screenery: F12 Screener Fundamentalny (`pages/7_sp500.py` + `pages/8_gpw.py` tab6), F13 Sprawozdania Q screener (`components/financials_ui.py:render_sprawozdania_screener`, oba market), F16 Bulk Insider Screener (`pages/23_insider_screener.py`). Wzorzec z F14: filter checkbox "⭐ Tylko watchlist" (disabled gdy pusty) + ⭐ kolumna w `st.data_editor` z `CheckboxColumn` + diff detection (`edited["⭐"] != display["⭐"]`) + `toggle_ticker(ls, ticker)` + `st.rerun()`. Klucze widget z `_v2` suffix (cache safety przy zmianie `st.dataframe` → `st.data_editor`). **F12 dodatkowy edge case:** `st.data_editor` nie obsługuje `on_select="rerun"` — zastąpiono mechanizm klik-row pre-fillijący `sp_finanse_ticker`/`gpw_finanse_ticker` osobnym selectboxem + button "💰 Pokaż w Finanse" (pattern z F13/F16 cross-link). Spec: `docs/superpowers/specs/2026-06-06-watchlist-domkniecie-design.md`. Plan: `docs/superpowers/plans/2026-06-06-watchlist-domkniecie.md`. Tests: brak nowych (pattern integracji = boilerplate Streamlit; sam watchlist testowany w `tests/test_calendar.py` z F14, 52/52 full suite).
```

- [ ] **Step 5.2: Commit CLAUDE.md**

```bash
git add CLAUDE.md
git commit -m "Update CLAUDE.md — F17 Watchlist cross-feature domkniecie"
```

- [ ] **Step 5.3: Final test suite + commits inventory**

```bash
./venv/Scripts/python.exe -m pytest tests/ -v 2>&1 | tail -5
git log origin/main..HEAD --oneline
```

Expected: 52/52 PASS + 6 commitów (1 spec `dd38cb5` + plan + 4 task commits + CLAUDE.md).

- [ ] **Step 5.4: Push**

```bash
git push origin main
```

Streamlit Cloud auto-redeploy ~3-5 min.

- [ ] **Step 5.5: Manual QA matrix na produkcji**

Otwórz `https://gem-dashboard.streamlit.app/`. Cross-screener flow:

1. **Page 22 (F14 Earnings Calendar)** — dodaj **AAPL** do watchlist (klik ⭐ w tabeli)
2. **Page 7 SP500 → tab6 "📊 Screening" (F12)** — sprawdź:
   - [ ] Widoczna ⭐ kolumna jako pierwsza
   - [ ] AAPL ma ⭐ ✅ (dodany na page 22)
   - [ ] Checkbox "⭐ Tylko watchlist" → tylko AAPL widoczny
   - [ ] Toggle ⭐ przy MSFT → reload → MSFT zachowany
   - [ ] Selectbox + button "💰 Pokaż w Finanse" → tab 7 Finanse pre-fillowany
3. **Page 7 SP500 → tab8 "📈 Sprawozdania Q" → Screener** — sprawdź:
   - [ ] ⭐ kolumna widoczna, AAPL+MSFT mają ⭐ ✅
   - [ ] Filter "Tylko watchlist" działa
   - [ ] Toggle ⭐ przy NVDA → reload → NVDA zachowany
4. **Page 8 GPW → tab6 (F12 GPW)** — sprawdź dla PKO.WA (toggle, filter)
5. **Page 23 (F16 Insider Screener)** — sprawdź:
   - [ ] ⭐ kolumna, AAPL+MSFT+NVDA mają ⭐ ✅
   - [ ] Filter "Tylko watchlist" działa
6. **Sanity check F14 nie zepsute:** Page 22 → ⭐ AAPL nadal działa, watchlist persystuje

- [ ] **Step 5.6: MEMORY.md entry**

Najpierw utwórz topic file `project_gem_dashboard_watchlist_domkniecie.md`:

```markdown
---
name: project-gem-dashboard-watchlist-domkniecie
description: F17 Watchlist cross-feature domknięcie — WGRANE 2026-06-06, watchlist filter+⭐ kolumna w F12+F13+F16
metadata:
  type: project
---

# F17 Watchlist domknięcie — WGRANE 2026-06-06

**Final commit:** `<HASH>` na main. Live: `gem-dashboard.streamlit.app`.
**6 commitów** total (1 spec `dd38cb5` + 1 plan + 4 task commits + CLAUDE.md).

## Co zostało dodane

Rozszerzenie `components/watchlist.py` (z F14) na 3 screenery:
- **F12 Screener Fundamentalny** (tab6 SP500+GPW) — filter + ⭐ kolumna + selectbox-finanse (zamiast on_select)
- **F13 Sprawozdania Q screener** (`render_sprawozdania_screener`, oba market) — filter + ⭐ kolumna
- **F16 Bulk Insider Screener** (page 23) — filter + ⭐ kolumna

Pattern z F14 (sprawdzony):
- Filter checkbox "⭐ Tylko watchlist" (disabled gdy pusty)
- `st.data_editor` z `CheckboxColumn("⭐")` + diff detection + `toggle_ticker` + `st.rerun()`
- Klucze widget z `_v2` suffix (cache safety przy zmianie `st.dataframe` → `st.data_editor`)

## Decyzje architektoniczne

- **F12 wymagała wymiany on_select** — `st.data_editor` nie obsługuje `on_select="rerun"`. Selectbox + button "💰 Pokaż w Finanse" zastąpił klik-row pre-fill. UX podobny do F13/F16 cross-link.
- **Brak nowych testów** — pattern integracji to boilerplate Streamlit. Sam watchlist testowany w F14 (`tests/test_calendar.py`, 4 testy).
- **Bez standalone strony** "Moje spółki" (page 24) — przeniesione do v2 backlog.

## Cross-feature flow (po F17)

1. Dodaj AAPL do watchlist w F14 calendar (page 22) → klik ⭐
2. AAPL ma ⭐ w F12 screener tabach, F13 screener, F16 screener (same localStorage)
3. Filter "⭐ Tylko watchlist" w każdym → tylko twoje spółki
4. Toggle ⭐ z dowolnego ekranu zmienia stan globalnie

## v2 backlog

- Standalone strona "Moje spółki" (`pages/24_watchlist.py`) — dashboard z key metrics per ticker + linki do F13 deep dive
- Watchlist eksport / import JSON
- Watchlist sharing cloud (Supabase)
- Mini-dashboard watchlist w `app.py` sidebar (top-line metryki)

## Powiązane

- [[project-gem-dashboard-earnings-calendar]] — F14 (źródło watchlist module)
- [[project-gem-dashboard-insider-trading]] — F15
- [[project-gem-dashboard-insider-screener]] — F16
- [[feedback-streamlit-session-state-widget-keys]] — pattern session_state widget keys
```

(`<HASH>` podstaw z `git log -1 --oneline` po pushu.)

Następnie dopisz 1-liniowy entry w `MEMORY.md` w sekcji "Projekt: gem-dashboard" (po wpisie F16):

```markdown
- [F17 Watchlist domknięcie — WGRANE 2026-06-06](project_gem_dashboard_watchlist_domkniecie.md) — filter + ⭐ kolumna w F12+F13+F16 (cross-feature reuse `components/watchlist.py` z F14). F12 wymagała wymiany `on_select` na selectbox+button. Final commit `<HASH>`. 52/52 tests PASS.
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ F12 SP500 tab6 (Task 1)
- ✅ F12 GPW tab6 (Task 2)
- ✅ F13 `render_sprawozdania_screener` oba market (Task 3, używa `market` arg)
- ✅ F16 page 23 (Task 4)
- ✅ CLAUDE.md F17 (Task 5)
- ✅ Manual QA matrix (Task 5.5)
- ✅ MEMORY.md (Task 5.6)
- ✅ F12 edge case `on_select` → selectbox-finanse (Task 1, Task 2 — explicit replacement)
- ✅ `_v2` suffix klucze (Task 1-4)

**Placeholder scan:**
- ✅ Brak TBD/TODO
- ✅ `<HASH>` w MEMORY.md template — zamierzone (engineer wypełnia z `git log`)

**Type consistency:**
- ✅ `get_watchlist(ls) -> set[str]` używane w Task 1-4 identycznie
- ✅ `toggle_ticker(ls, ticker) -> bool` używane w Task 1-4 identycznie
- ✅ Klucze widget per screener — unikatowe, zgodne ze spec
- ✅ F13 `market` arg używany jako prefix (Task 3) — zgodne ze spec
- ✅ F12 `df_sorted.index` jako ticker source (F12 trzyma ticker w index, NIE kolumnie) — różni się od F13/F16 które mają `display["Ticker"]`. To **prawidłowe** — F12 używa `bulk_fetch_universe → to_screener_df` które stawia ticker jako index.

**Spec gaps:** brak. Decyzja F12 on_select → selectbox dodana inline do spec po brainstormingu (commit `dd38cb5`).
