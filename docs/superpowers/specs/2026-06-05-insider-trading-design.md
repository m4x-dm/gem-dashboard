# Insider Trading & Institutional Holdings — design

**Data:** 2026-06-05
**Status:** Draft — czeka na review użytkownika
**Cel:** Dodać 5. sub-tab "👥 Insiders" w F13 Sprawozdania Q deep dive (`render_sprawozdania_deep_dive` w `components/financials_ui.py`) — pełen obraz smart money: insider transactions, roster, institutional holders, mutual fund holders, major holders breakdown.

## Kontekst

GEM Dashboard ma już:
- **F13 Sprawozdania Q** (2026-06-02, commit `8f73d6e`) — `render_sprawozdania_deep_dive` z 4 sub-tabami (BeatMiss / IS / BS / CF)
- **F14 Earnings Calendar** (2026-06-05, commit `4912ad0`) — cross-link do F13 deep dive
- Stabilne yfinance endpointy: `earnings_history`, `earnings_estimate`, `info`, `quarterly_*_stmt`, `calendar`
- Lesson learned: niektóre endpointy yfinance są flaky (`earnings_dates`) — zawsze testować na produkcji

Nowa funkcjonalność rozszerza F13 deep dive o **6 sekcji insider/institutional** w jednym sub-tabie.

## Scope MVP

**W MVP:**
- 6 funkcji w `data/financials.py`:
  - `fetch_insider_transactions(ticker)` — historia 6mc (Date/Insider/Position/Type/Shares/Value)
  - `fetch_insider_purchases(ticker)` — agregat 6mc (Total Purchases / Sales / Net / % Change)
  - `fetch_insider_roster_holders(ticker)` — kto z zarządu trzyma (Name/Position/Latest/Shares)
  - `fetch_institutional_holders(ticker)` — top 10 funduszy (Holder/%/Shares/Value/Date)
  - `fetch_mutualfund_holders(ticker)` — top 10 mutual funds (analogicznie)
  - `fetch_major_holders(ticker)` — dict {insider_pct, institutional_pct, institutional_count, float_pct}
- Helper `_normalize_transaction_type` (Sale → Sell, Purchase → Buy)
- 5. sub-tab "👥 Insiders" w `render_sprawozdania_deep_dive`
- 6 sekcji UI w sub-tabie (Major Holders cards, Purchases summary, Transactions + bar chart, Roster, Institutional + pie chart, Mutual Fund)
- GPW fallback: gdy wszystkie 6 endpointów None → info box z linkiem do gpw.pl
- Tests pytest 6+ mock-based
- CLAUDE.md F15 paragraph

**Effective universe:** wszystkie spółki dostępne w F13 deep dive (SP500 + GPW). Dla GPW realnie tylko fallback info box (yfinance nie ma SEC Form 4 dla polskich spółek — raporty bieżące idą przez ESPI).

**Poza MVP (v2):**
- Bulk screener "kto najwięcej kupił/sprzedał w SP500" (osobna strona lub tab w F13 obok deep dive)
- Cross-link transactions → F14 Earnings Calendar (insider sale przed earnings = red flag signal)
- Alerty: "CEO/CFO kupili >$X z Twojego watchlistu w ostatnich N dniach"
- Polskie ESPI integracja (scraping gpw.pl/komunikaty-spolek)
- Insider sentiment score (composite z transactions + holdings)

---

## Architektura

### Data layer (`data/financials.py` — +6 funkcji + 1 helper)

```python
def _normalize_transaction_type(raw: str) -> str:
    """Mapuje yfinance raw type (Sale (Non Open Market) / Purchase / itd.)
    na ujednolicone 'Buy' / 'Sell' / oryginalny string dla pozostalych
    (Exercise of Options, Conversion etc. zostawione jako label)."""

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_insider_transactions(ticker: str) -> pd.DataFrame | None:
    # yfinance: Ticker.insider_transactions
    # Rename kolumn + normalize Type
    # Returns: Date (index), Insider, Position, Type, Shares, Value
    # None gdy empty/exception

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_insider_purchases(ticker: str) -> pd.DataFrame | None:
    # yfinance: Ticker.insider_purchases — agregat 6mc

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_insider_roster_holders(ticker: str) -> pd.DataFrame | None:
    # yfinance: Ticker.insider_roster_holders

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_institutional_holders(ticker: str) -> pd.DataFrame | None:
    # yfinance: Ticker.institutional_holders (top 10)

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_mutualfund_holders(ticker: str) -> pd.DataFrame | None:
    # yfinance: Ticker.mutualfund_holders (top 10)

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_major_holders(ticker: str) -> dict | None:
    # yfinance: Ticker.major_holders
    # Defensywny parser (dict ALBO DataFrame format).
    # Returns dict: insider_pct, institutional_pct,
    #               institutional_count, float_pct
```

**Brak parquet cache** — lekkie endpointy (~5-30 rows DF), in-memory wystarczy.

### UI layer (`components/financials_ui.py`)

`render_sprawozdania_deep_dive` zmiana:
```python
sub1, sub2, sub3, sub4, sub5 = st.tabs([
    "📊 Beat/Miss historia",
    "📑 Income Statement",
    "💰 Balance Sheet",
    "💵 Cash Flow",
    "👥 Insiders",  # NEW
])
with sub5:
    _render_insiders_tab(ticker)
```

Nowy helper `_render_insiders_tab(ticker)` + 2 chart helpers:
- `_chart_insider_net_per_month(transactions_df)` — Plotly bar (green/red)
- `_chart_institutional_pie(institutional_df)` — Plotly donut top 10 + Reszta

---

## UI — Sub-tab "👥 Insiders" layout

### Sekcja 1: Major Holders (4 metric cards 2×2)

```
% Insider     │  % Institutional   │  # Institutions  │  % Float
0.07%         │  62.5%             │  4,892           │  99.93%
```

`st.columns(4)` + `st.metric()` per pole. Format: `%.2f%%` dla pct, `f"{n:,}"` dla count.

### Sekcja 2: Insider Purchases summary (3 metric cards)

```
Total Purchases     │  Total Sales         │  Net (6 mc)
12 / $4.2M          │  47 / $128.5M        │  -35 / -$124.3M ❌
```

`st.metric` z delta colorem (zielony positive, czerwony negative).

### Sekcja 3: Insider Transactions + bar chart

```
#### 📊 Historia transakcji insiderów (6 mc)

Wykres Plotly bar: net buy/sell value per miesiąc
(zielony=buy, czerwony=sell). 6 słupków (full range,
puste miesiące = 0 wypełnione).

Tabela st.dataframe (max 30 rows):
Date    │ Insider           │ Position │ Type │ Shares │ Value
2026-05 │ TIMOTHY D. COOK   │ CEO      │ Sell │ 100,000│ $20M
```

### Sekcja 4: Insider Roster (sama tabela)

```
#### 🏢 Roster zarządu

Name        │ Position │ Latest Trans │ Shares Owned
Tim Cook    │ CEO      │ 2026-05-15   │ 3,280,000
```

### Sekcja 5: Institutional Holders + pie chart (2 kolumny)

```
#### 🏛️ Top 10 funduszy instytucjonalnych

┌─Tabela (60%)──────────┐  ┌─Pie chart donut (40%)──┐
│ Holder      │% │Shares │  │  Vanguard 8.2%         │
│ Vanguard    │8.2│1.3B  │  │  BlackRock 6.5%        │
│ ...                   │  │  Reszta 75.7%          │
```

Pie chart kolory: top 5 gold variants (`GOLD`, `#E8C96A`, `#FFD700`, `#B8860B`, `#DAA520`), top 6-10 grays.

### Sekcja 6: Mutual Fund Holders (sama tabela)

```
#### 💼 Top 10 mutual funds

Holder              │ % Out │ Shares  │ Value    │ Date
Vanguard Total Mkt  │ 2.3%  │ 365M    │ $73B     │ 2026-03
```

---

## GPW fallback

```python
def _render_insiders_tab(ticker: str) -> None:
    major = fetch_major_holders(ticker)
    purchases = fetch_insider_purchases(ticker)
    transactions = fetch_insider_transactions(ticker)
    roster = fetch_insider_roster_holders(ticker)
    institutional = fetch_institutional_holders(ticker)
    mutual = fetch_mutualfund_holders(ticker)

    # Wszystkie None → GPW (lub spółka bez coverage) — pokazujemy info
    if all(x is None for x in [major, purchases, transactions, roster, institutional, mutual]):
        st.info(
            "⚠️ Brak danych insider/institutional dla tego tickera.\n\n"
            "Dla spółek GPW raporty bieżące idą przez ESPI (poza zakresem yfinance).\n"
            "Sprawdź ręcznie: https://www.gpw.pl/komunikaty-spolek"
        )
        return

    # ... render 6 sekcji (każda z lokalnym empty-state)
```

Per sekcja jeśli **dana sekcja** ma None ale inne mają dane → `st.caption("Brak danych dla {section}.")` w miejscu sekcji.

---

## Format wartości

- **Shares** — `format_large_number()` (1.3B / 890M / 365M) — z F11
- **Value USD** — `$` + `format_large_number()` — uwaga: yfinance zwraca **zawsze USD**, nawet dla GPW
- **Date** — `st.column_config.DateColumn(format="YYYY-MM-DD")`
- **% Out** — `st.column_config.NumberColumn(format="%.2f%%")`
- **Type** — TextColumn (Buy/Sell + emoji ✅/❌ jako prefix)

---

## Edge cases

### 1. yfinance empty / crash
Wszystkie 6 fetch: `try/except Exception: return None` + `if df is None or df.empty: return None`. UI: `st.caption("Brak danych...")` per sekcja, fallback info-box jeśli wszystkie None.

### 2. Transaction Type normalizacja
yfinance zwraca różne labele:
- "Sale (Non Open Market)" / "Sale at Public Offering" / "Sale" / "Sell" → **"Sell"**
- "Purchase" / "Buy" → **"Buy"**
- "Conversion" / "Exercise of Options" → zostawiamy oryginał (informacyjne, NIE liczymy w net buy/sell)

```python
def _normalize_transaction_type(raw: str) -> str:
    raw_lower = str(raw).lower()
    if "sale" in raw_lower or "sell" in raw_lower:
        return "Sell"
    if "purchase" in raw_lower or "buy" in raw_lower:
        return "Buy"
    return str(raw).split("(")[0].strip()
```

### 3. Net per miesiąc — puste miesiące
Reindexujemy do full 6mc range:
```python
all_months = pd.period_range(end=pd.Timestamp.now().to_period("M"), periods=6, freq="M")
agg = agg.reindex(all_months, fill_value=0)
```

### 4. `Ticker.major_holders` — dict ALBO DataFrame
Defensywny parser:
```python
if isinstance(raw, dict):
    out["insider_pct"] = raw.get("insidersPercentHeld")
    # ...
elif isinstance(raw, pd.DataFrame) and not raw.empty:
    # Index = label string, kolumna 0 = value
    # Matching po lowercase substring
```

### 5. Pie chart — % out > 100% (rzadkie, yfinance bug)
`rest_pct = max(0, 100 - top10["% Out"].sum())` — clamp do 0.

### 6. F14 cross-link side-effect
F14 `_navigate_to_deep_dive` ustawia `{market}_deep_dive_ticker` + `{market}_pending_view = "deep_dive"` i wywołuje `st.switch_page("pages/7_sp500.py")`. F13 deep dive z 5 sub-tabami (zamiast 4) — cross-link nadal działa, sub-taby ładują się w kontekście strony 7/8.

### 7. Banki USA — brak special handling
JPM/BAC/GS itd. mają taką samą strukturę yfinance — działają out-of-the-box.

### 8. yfinance flaky endpoint risk
Lesson z F14 hotfix: niektóre endpointy yfinance są flaky. Mitigacja:
- Każdy z 6 fetch jest izolowany (jeden None nie blokuje innych)
- Manual QA na produkcji **PO** pierwszym deploy (AAPL/TSLA/JPM coverage check)
- Jeśli któryś endpoint okaże się flaky — usuwamy sekcję lub fallback do innego

---

## Testing strategy

**Nowe testy w `tests/test_financials.py`** (~6-8 testów mock-based):

```python
def test_normalize_transaction_type_sale_variants()
def test_normalize_transaction_type_purchase()
def test_normalize_transaction_type_other_kept()
def test_fetch_insider_transactions_normalizes_types()  # mock yfinance, sprawdza Sell/Buy
def test_fetch_insider_transactions_returns_none_on_empty()
def test_fetch_institutional_holders_returns_df()
def test_fetch_major_holders_dict_format()  # parser case 1
def test_fetch_major_holders_df_format()    # parser case 2
def test_fetch_major_holders_returns_none_when_all_empty()
```

**Manual QA na produkcji:**
- AAPL — wszystkie 6 sekcji renderują, real dane (Tim Cook sells widoczne)
- JPM — banki USA bez special handling, dane są
- TSLA — różne transaction types (Elon: Conversion, Exercise, Sale)
- MSFT — institutional dominance (Vanguard/BlackRock w top)
- PKO.WA — GPW info box ("Brak danych..." + link)
- 11B.WA — analogicznie GPW empty
- KGH.WA — GPW empty

---

## Pliki do utworzenia / zmiany

**Modyfikowane:**
- `data/financials.py` — +6 funkcji fetch_* + 1 helper `_normalize_transaction_type` (~250 LOC)
- `components/financials_ui.py` — +5. sub-tab w `render_sprawozdania_deep_dive` + helper `_render_insiders_tab` + 2 chart helpers (`_chart_insider_net_per_month`, `_chart_institutional_pie`) (~250 LOC)
- `tests/test_financials.py` — +6-8 testów mock-based
- `CLAUDE.md` — Pages structure bez zmian (to sub-tab nie nowa strona) + F15 paragraph w Key Design Decisions

**Bez nowych plików** — wszystko jako rozszerzenie istniejących modułów.

**Bez zmian:**
- `pages/7_sp500.py` + `pages/8_gpw.py` — F13 tab8 bez zmian (sub-tab dochodzi w UI helper, ale to wewnętrzna struktura `render_sprawozdania_deep_dive`)
- `app.py`, `auth.py` — bez zmian (sub-tab, nie nowa strona)

---

## Definition of Done

- [ ] 6 fetch funkcji w `data/financials.py` z `@st.cache_data(ttl=86400)` + graceful None
- [ ] `_normalize_transaction_type` helper + tests
- [ ] `_render_insiders_tab` w `components/financials_ui.py` z 6 sekcjami
- [ ] 2 chart helpers (bar net, donut institutional)
- [ ] GPW fallback (info box gdy wszystkie 6 None)
- [ ] 5. sub-tab "👥 Insiders" w `render_sprawozdania_deep_dive`
- [ ] Tests pytest 6+ mock-based, full suite passing
- [ ] Manual QA matrix: AAPL/JPM/TSLA/MSFT/PKO.WA/11B.WA/KGH.WA wszystko ✓
- [ ] CLAUDE.md F15
- [ ] Commit + push do `m4x-dm/gem-dashboard` main
- [ ] Streamlit Cloud auto-deploy zweryfikowany
- [ ] MEMORY.md entry
