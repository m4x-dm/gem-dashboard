# Implementation Plan: Tab "Finanse spółki"

**Data:** 2026-05-14
**Spec:** [2026-05-14-finanse-spolki-design.md](../specs/2026-05-14-finanse-spolki-design.md)
**Status:** Draft — do user review
**Estymacja:** ~4-6h pracy w 4 fazach

## Overview

Implementacja w 4 fazach z walidacją po każdej. Każda faza producuje deliverable który da się zweryfikować osobno przed przejściem dalej. Total: 1 nowy plik, 4 edytowane pliki.

```
Phase 1: Data layer foundation       (~1.5h)  → data/financials.py + GPW_BANKS w gpw_universe.py
Phase 2: UI cards components         (~1.5h)  → components/cards.py rozszerzony o 4 funkcje
Phase 3: Pages integration           (~1h)    → pages/7_sp500.py + pages/8_gpw.py z 6-tym tabem
Phase 4: Polish + smoke + deploy     (~1h)    → manual tests, mobile, CLAUDE.md, commit, push
```

## Prerequisites

- ✅ Spec accepted (commit `f8a4e91`)
- ✅ yfinance test passed (AAPL/MSFT/PKN happy, PKO/CCC edge cases verified)
- ✅ Visual companion mockup approved (tab layout 2×2 grid)
- ⏳ GEM dashboard local dev environment (`venv/Scripts/python.exe` + `streamlit run app.py`)

## Phase 1: Data Layer (foundation)

**Cel:** wszystkie funkcje fetch + cache działają niezależnie od UI, walidowane na 5 tickerach.

### Tasks

**1.1** Utwórz `data/financials.py` z 4 cached funkcjami:
   - `get_ratios_snapshot(ticker) -> dict` — 12 metryk z `yf.Ticker(ticker).info`
     - Klucze: `pe`, `fwd_pe`, `ev_ebitda`, `ebitda`, `roe`, `roa`, `profit_margin`, `gross_margin`, `fcf`, `debt_to_equity`, `price_to_book`, `dividend_yield`, `market_cap`, `current_price`
     - Wrapped w `try/except Exception` → return `{}` gdy fail
     - Decorator `@st.cache_data(ttl=86400)`
   - `get_forward_consensus(ticker) -> pd.DataFrame | None` — `yf.Ticker(t).earnings_estimate`
     - Cols: `avg`, `low`, `high`, `numberOfAnalysts`, `growth`
     - Index: period (0q/+1q/0y/+1y)
     - None gdy DataFrame empty lub `numberOfAnalysts.sum() == 0`
   - `get_earnings_history(ticker, n_quarters=8) -> pd.DataFrame | None` — `yf.Ticker(t).earnings_history`
     - Cols: `quarter`, `eps_estimate`, `eps_actual`, `surprise_pct`
     - Liczy `surprise_pct = (actual - estimate) / abs(estimate)` lokalnie
     - None gdy fail/empty
   - `get_analyst_recos(ticker) -> dict` — subset z `Ticker.info`
     - Klucze: `target_mean`, `target_median`, `target_high`, `target_low`, `recommendation_key`, `num_analysts`, `current_price`, `upside_pct` (computed)

**1.2** Dodaj helpers do `data/financials.py`:
   - `is_bank(ticker: str) -> bool` — sprawdza vs `GPW_BANKS` set z gpw_universe
   - `format_currency(value: float | None, ticker: str) -> str` — PLN dla `.WA`, USD pozostałe
   - `format_large_number(value)` — $4.4T / 160B / 101M / 25K formatting

**1.3** Edytuj `data/gpw_universe.py` — dodaj export `GPW_BANKS`:
   ```python
   GPW_BANKS: set[str] = {
       # WIG20
       "ALR.WA",   # Alior Bank
       "MBK.WA",   # mBank
       "PEO.WA",   # Bank Pekao
       "PKO.WA",   # PKO Bank Polski
       "SPL.WA",   # Santander Bank Polska
       # mWIG40
       "BHW.WA",   # Bank Handlowy
       "BNP.WA",   # BNP Paribas Bank Polska
       "ING.WA",   # ING Bank Śląski (jeśli w universe)
       "MIL.WA",   # Bank Millennium (jeśli w universe)
       # Last verified: 2026-05-14
   }
   ```

### Deliverable Phase 1

```
data/financials.py            (~120-150 LOC)
data/gpw_universe.py          (+10 LOC, GPW_BANKS export)
```

### Validation Phase 1

Standalone Python test (bez Streamlit):

```python
from data.financials import (
    get_ratios_snapshot, get_forward_consensus,
    get_earnings_history, get_analyst_recos, is_bank
)

# Happy path
assert "pe" in get_ratios_snapshot("AAPL")
assert get_ratios_snapshot("AAPL")["pe"] is not None
assert get_forward_consensus("AAPL") is not None  # 30+ analytics
assert len(get_earnings_history("AAPL", n_quarters=8)) > 0

# Edge: GPW bank
snap_pko = get_ratios_snapshot("PKO.WA")
assert snap_pko.get("ebitda") is None  # banks no EBITDA
assert is_bank("PKO.WA") is True
assert is_bank("PKN.WA") is False

# Edge: 404
snap_ccc = get_ratios_snapshot("CCC.WA")
assert snap_ccc == {} or snap_ccc.get("pe") is None  # graceful

# Cache (drugi call instant)
import time
t0 = time.time(); get_ratios_snapshot("MSFT"); t1 = time.time()
get_ratios_snapshot("MSFT"); t2 = time.time()
assert (t2-t1) < (t1-t0) * 0.1  # cache 10× szybsze
```

**Gate:** Wszystkie asserty zielone → Phase 2.

## Phase 2: UI Cards Components

**Cel:** 4 nowe funkcje w `components/cards.py` renderują się niezależnie. Visual review każdej osobno.

### Tasks

**2.1** Dodaj `ratios_card(snapshot: dict, is_bank: bool = False) -> None` do `components/cards.py`:
   - Empty snapshot → `st.html('<div class="finance-empty">Brak danych ze źródła yfinance</div>')`, return
   - Grid 4×3 z 12 metrykami przez `st.html()`
   - Każda komórka: `<div><span class="lbl">PE</span><span class="val">36.1</span></div>`
   - Dla `is_bank=True`: skip EBITDA/EV-EBITDA/FCF, replace with `<span class="val">N/A (bank)</span>`
   - Style inline (per CLAUDE.md `st.html()` strip `<style>` przez DOMPurify)
   - Użyj `fmt_pct`, `fmt_number`, `color_for_value` z `components/formatting.py`
   - Kolory: `GOLD`, `BG_CARD`, `BORDER`, `MUTED` z `components/formatting.py`

**2.2** Dodaj `forward_consensus_card(df: pd.DataFrame | None) -> None`:
   - None/empty → info box "Brak konsensusu analityków"
   - Plotly bar chart z `components/charts.py` pattern (`_base_layout()` jeśli istnieje, dark bg, gold bars)
   - X: period labels ("Q0", "Q+1", "FY", "FY+1")
   - Y: `avg` EPS estimate
   - Error bars: `low` do `high`
   - Hover: `growth`, `numberOfAnalysts`
   - `st.plotly_chart(fig, use_container_width=True)`

**2.3** Dodaj `earnings_history_card(df: pd.DataFrame | None) -> None`:
   - None/empty → "Brak historii earnings"
   - Header: `"Avg surprise: +X.X%"` (mean surprise_pct)
   - Tabela 8 wierszy: Quarter | Estimate | Actual | Surprise%
   - Surprise% kolor: `color_for_value()` z `components/formatting.py`
   - Render przez `st.html()` (NIE st.dataframe — chcemy spójny styl z innymi kartami)

**2.4** Dodaj `analyst_recos_card(recos: dict) -> None`:
   - Empty/no analysts → "Brak rekomendacji analityków"
   - Layout: 2 kolumny — left target_mean + upside %, right lista target_high/median/low
   - Recommendation badge: kolorowy box ze słowem "BUY"/"HOLD"/"SELL" zmapowane z `recommendation_key`
   - Mapping: `strong_buy`/`buy` → green, `hold` → yellow/MUTED, `sell`/`strong_sell` → red
   - `num_analysts` jako footer "Na podstawie X analityków"

### Deliverable Phase 2

```
components/cards.py    (+200-250 LOC)
```

### Validation Phase 2

Stwórz tymczasowy `pages/_test_finanse.py` z 4 cards renderującymi AAPL:

```python
import streamlit as st
from data.financials import *
from components.cards import (
    ratios_card, forward_consensus_card,
    earnings_history_card, analyst_recos_card
)

st.title("Test finanse cards")
ticker = st.text_input("Ticker", "AAPL")

col1, col2 = st.columns(2)
with col1:
    ratios_card(get_ratios_snapshot(ticker), is_bank=is_bank(ticker))
with col2:
    forward_consensus_card(get_forward_consensus(ticker))

col3, col4 = st.columns(2)
with col3:
    earnings_history_card(get_earnings_history(ticker))
with col4:
    analyst_recos_card(get_analyst_recos(ticker))
```

Manual: `streamlit run pages/_test_finanse.py`, przetestuj 5 tickerów (AAPL, MSFT, PKN, PKO, CCC).

**Gate:** 5/5 tickerów renderuje bez crash, układ pasuje do visual mockup → Phase 3. **Usuń `_test_finanse.py` przed commitem.**

## Phase 3: Pages Integration

**Cel:** tab "Finanse" widoczny w pages 7+8, selectbox działa, layout 2×2.

### Tasks

**3.1** Edytuj `pages/7_sp500.py`:
   - Zmień `tab1, tab2, tab3, tab4, tab5 = st.tabs([...])` → dodać 6-ty: `, "💰 Finanse"`
   - Dodaj sekcję `# ========================== TAB 6: FINANSE ==========================` po RS
   - `with tab6: @st.fragment def _finanse_fragment():`
   - Selectbox:
     - Default: spróbuj `st.session_state.get("sp_rank_top_ticker")` (set w `_ranking_fragment` po build_ranking)
     - Fallback: `sorted(SP500_NAMES.keys())[0]`
     - Lista: `sorted(SP500_NAMES.keys())` z formatter `f"{t} — {SP500_NAMES[t]}"`
   - Po wyborze ticker:
     - Spinner "Ładuję dane finansowe..."
     - 4 sekwencyjne calls do `data/financials.py`
   - Layout: 2 col × 2 row Streamlit columns z 4 cards
   - Plus `_ranking_fragment` minor edit: po `build_ranking` zapisać `st.session_state["sp_rank_top_ticker"] = ranking.iloc[0]["ticker"]` (jeśli klucz nie istnieje już)

**3.2** Edytuj `pages/8_gpw.py`:
   - Analogicznie jak 7_sp500 (tab6 Finanse)
   - Plus extra info box przed cards: `st.info("Niektóre wskaźniki niedostępne dla GPW spółek lub sektora bankowego.")`
   - `ratios_card(snap, is_bank=is_bank(ticker))` zamiast `is_bank=False`
   - Klucz session_state: `gpw_rank_top_ticker`

### Deliverable Phase 3

```
pages/7_sp500.py    (~50 LOC dodanych dla tab6)
pages/8_gpw.py      (~55 LOC dla tab6 + info box)
```

### Validation Phase 3

```bash
streamlit run app.py
```

Manual:
- Otwórz S&P 500 page → tab "Finanse" → selectbox pre-fill z top-1 ranking → wybór AAPL → 4 cards
- Przełącz na MSFT → szybko (cache) → 4 cards
- Przełącz na nieistniejący (typuj "XYZ123") → "Brak danych" 4× bez crash
- Otwórz GPW page → tab "Finanse" → info box widoczny
- PKN.WA → 4 cards działają
- PKO.WA → ratios_card pokazuje "N/A (bank)" w EBITDA/EV-EBITDA/FCF
- CCC.WA → "Brak danych" 4× bez crash

**Gate:** Wszystko OK → Phase 4.

## Phase 4: Polish + Smoke + Deploy

**Cel:** smoke test, mobile review, dokumentacja, push do main.

### Tasks

**4.1** Manual smoke test (per spec acceptance criteria):
   - SP500 happy: AAPL, MSFT, NVDA, CRWD, XOM (5 spółek)
   - SP500 edge: nieistniejący XYZ123, oraz 1 small cap z brakami
   - GPW happy: PKN, CDR, ALE (pełne pokrycie)
   - GPW bank: PKO, PEO, MBK (auto-hide EBITDA)
   - GPW edge: CCC.WA (404), 1 sWIG80 random

**4.2** Mobile review przez DevTools (Chrome → Toggle device toolbar):
   - 1920px desktop → 2×2 grid
   - 768px tablet → 2×2 lub 1col stack
   - 375px mobile → 1col stack, każda card full width
   - Sprawdź czy Plotly chart resize'uje się poprawnie

**4.3** Performance check:
   - Pierwszy click AAPL: ≤2s spinner
   - Drugi click AAPL: <100ms (cache)
   - Switch między 5 tickerami back-and-forth → tylko pierwsze fetch'e wolne

**4.4** Update dokumentacji:
   - `CLAUDE.md` w gem-dashboard: dodać krótki opis tab "Finanse" w sekcji Pages (7_sp500.py + 8_gpw.py), wspomnieć `data/financials.py`, `GPW_BANKS` w gpw_universe, `ratios_card`/etc w cards.py
   - Update liczby: "5 tabs" → "6 tabs" w pages 7+8 opisach

**4.5** Pre-commit cleanup:
   - Usuń `pages/_test_finanse.py` (z Phase 2)
   - `git status` → sprawdź że nie commitujemy `.superpowers/`, screenshots, `codes_plaintext.txt` etc.
   - Selektywne `git add` (nigdy `-A`/`.`)

**4.6** Commit + push:
   ```
   git add data/financials.py data/gpw_universe.py components/cards.py \
           pages/7_sp500.py pages/8_gpw.py CLAUDE.md \
           docs/superpowers/plans/2026-05-14-finanse-spolki-plan.md
   git commit -m "Add Finanse tab to SP500 + GPW pages (ratios, forward consensus, earnings history, recos)"
   git push origin main
   ```

**4.7** Verify deploy:
   - Streamlit Cloud auto-redeploy (~2-3 min)
   - Otwórz `https://gem-dashboard.streamlit.app/` → S&P 500 → Finanse → AAPL
   - Sprawdź czy działa identycznie jak lokalnie

### Deliverable Phase 4

Live na `gem-dashboard.streamlit.app`, dokumentacja zaktualizowana.

### Validation Phase 4

- Wszystkie 12 spółek z smoke testu renderują OK na produkcji
- Mobile responsywne (manual test telefonem lub DevTools)
- Logi Streamlit Cloud bez ERROR

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| yfinance API zmieni schema `earnings_estimate` / `earnings_history` | High — crashe | Try/except + None fallback w każdym `get_*`. Plus snapshot test po deploy. |
| `Ticker.info` rate limit 429 w godzinach szczytu | Med — slow UX | Cache 24h. Jeśli stanie się problemem → throttle (1 call/sec) w iteracji 2. |
| `st.session_state["sp_rank_top_ticker"]` collision z istniejącym kluczem | Low — bad default | Sprawdzić istniejące klucze w 7+8 przed nazwaniem (kompletny grep przed phase 3). |
| Plotly forward chart nie pasuje stylistycznie do reszty wykresów | Low — visual | Użyć `_base_layout()` z `components/charts.py` jeśli istnieje, inaczej replikować styl manually. |
| GPW bank detection — nowa fuzja/zmiana ticker | Low — wrong "N/A (bank)" | Review `GPW_BANKS` co kwartał. Plus "Last verified: YYYY-MM-DD" komentarz. |
| CCC.WA i podobne 404 = silent — user nie wie dlaczego "Brak danych" | Low — UX | W `analyst_recos_card` fallback: "Spółka niedostępna w yfinance (możliwe że ticker zmienił nazwę lub została wycofana)". |

## Out-of-Scope (Iteracja 2)

Powtórzone z spec dla jasności:

- Revision trend konsensusu (`Ticker.eps_revisions`)
- Session-state failure tracking (analog `_data_failures`)
- Peer comparison auto-pick z tego samego sektora
- Segmentowe KPI (wymaga MCP financial-datasets, płatne)
- PDF export integration
- GPW small caps via alternative source (stockwatch.pl / Macrotrends scrape)
- Krypto + ETF (nie ma EBITDA / nie ma sensu)

## Notes for Implementation Agent

Jeśli wracam do tego pliku w przyszłej sesji bez kontekstu:

1. **Spec źródło prawdy:** `../specs/2026-05-14-finanse-spolki-design.md`
2. **Konwencje GEM dashboard:** `../../../CLAUDE.md` — szczególnie `st.html()` vs `st.markdown(unsafe_allow_html)`, `_base_layout()`, color tokens
3. **yfinance test snippets:** zachowany w spec sekcji Testing
4. **Visual mockup:** `.superpowers/brainstorm/505-*/content/tab-mockup.html` (jeśli istnieje — może być wygasłe sesja)
5. **Git history:** ostatni commit przed tym task'iem to `f8a4e91` (spec) — wszystko po tym jest implementacja
