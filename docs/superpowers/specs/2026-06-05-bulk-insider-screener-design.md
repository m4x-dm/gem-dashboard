# Bulk Insider Screener — design

**Data:** 2026-06-05
**Status:** Draft — czeka na review użytkownika
**Cel:** Nowa strona `pages/23_insider_screener.py` — bulk screener insider activity dla SP500 (456 spółek): top buyers/sellers w 6mc, sektorowa heatmapa, tabela z filtrami, cross-link do F13 deep dive Insiders.

## Kontekst

GEM Dashboard ma już:
- **F15 Insider Trading** (2026-06-05, commit `9777d91`) — `data/financials.py` z 6 funkcjami insider/institutional + `_try_insider_endpoint` fallback chain (property → get_*() → bez session)
- **F14 Earnings Calendar** (2026-06-05, commit `4912ad0`) — wzorzec bulk screener (`bulk_fetch_earnings_calendar` z ThreadPool 8 workers + cross-link do F13)
- **F12 Screener Fundamentalny** (2026-05-18) — wzorzec tabeli screener z filtrami

Nowa funkcjonalność rozszerza F15 z per-ticker deep dive na bulk universe view. Naturalny next step: zamiast szukać ręcznie kto kupuje, screener pokazuje **all SP500 jednocześnie**.

## Scope MVP

**W MVP:**
- `pages/23_insider_screener.py` (~250 LOC)
- `data/financials.py` +3 funkcje (~150 LOC):
  - `_compute_buy_streak(transactions_df)` — kolejne miesiące buy > sell (0-6)
  - `_aggregate_insider_for_ticker(ticker)` — agregat per spółka (16 pól)
  - `bulk_fetch_insider_screener(tickers_tuple)` — ThreadPool 8 workers + `@st.cache_data(ttl=86400)`
- Reuse z F15: `fetch_insider_transactions`, `fetch_institutional_holders`, `_try_insider_endpoint`
- Reuse z F11: `get_ratios_snapshot` (sektor + market cap)
- Reuse z F14: `_get_etf_set` (filter ETF z input)
- UI: filtry expander (6 kontrolek) + 4 summary cards + 2 Plotly bar charts top buyers/sellers + tabela 11 kolumn + sektorowa Plotly bar + cross-link selectbox+button do F13 + CSV
- Tests: 6 mock-based w `tests/test_financials.py`
- `app.py` + `auth.py` PAGE_INFO[23] + `CLAUDE.md` F16

**Effective universe:** **SP500 (456 spółek)**. ETF filtered out (no insider data — jak w F14). GPW wykluczone (yfinance nie ma SEC Form 4 dla PL — F15 lesson).

**Poza MVP (v2):**
- Multi-window toggle (3mc / 6mc / 12mc)
- Cross-feature watchlist filter (reuse `components/watchlist.py` z F14)
- "Smart insider" composite score (transactions × consistency × institutional change)
- Historical mini-sparkline per ticker (miesięczny net value)
- Alerty Telegram/email "CEO/CFO kupili >$X w SP500 dzisiaj"
- GPW ESPI scraping
- Mode "tylko z watchlisty"

---

## Architektura

### Data layer (`data/financials.py` — rozszerzenie)

```python
def _compute_buy_streak(transactions: pd.DataFrame) -> int:
    """Liczy kolejne ostatnie miesiące gdzie buy_value > sell_value.

    Iteruje od najnowszego miesiąca wstecz. Stop na pierwszym miesiącu
    gdzie buy <= sell. Max 6.
    Returns: int 0-6.
    """


def _aggregate_insider_for_ticker(ticker: str) -> dict | None:
    """Agregat insider activity dla 1 tickera.

    Pobiera (z fallback chain F15):
    - fetch_insider_transactions (6mc historia)
    - fetch_institutional_holders (top 10 fundusz)
    - get_ratios_snapshot (sektor + market_cap z Ticker.info)

    Returns dict z 16 polami: ticker, name, sector, market_cap,
        net_value_6m, n_buys, n_sells, avg_buy_size, avg_sell_size,
        top_buyer, top_buyer_value, top_seller, top_seller_value,
        top_institutional, top_inst_pct, sentiment (🟢/🔴/🟡/⚪),
        beat_streak_buys (0-6).

    Sentiment:
    - 🟢 net > 0 i n_buys >= 2
    - 🔴 net < 0 i n_sells >= 2
    - 🟡 mixed (np. net < 0 ale n_sells = 1)
    - ⚪ brak danych

    None gdy zarówno transactions jak i institutional pusty
    (filter out z bulk).
    """


@st.cache_data(ttl=86400, show_spinner="Pobieram bulk insider screener (~5-7 min cold cache)…")
def bulk_fetch_insider_screener(
    tickers_tuple: tuple[str, ...],
    max_workers: int = 8,
) -> pd.DataFrame:
    """Bulk insider screener.

    Filtruje ETF (_get_etf_set). ThreadPool + as_completed + st.progress.
    Default sort: net_value_6m DESC, NaN na końcu.

    Returns DataFrame 16-kolumnowy (lub pusty gdy żaden ticker nie ma danych).
    """
```

**Reuse z F15:** `fetch_insider_transactions` i `fetch_institutional_holders` mają fallback chain `_try_insider_endpoint` (property → get_*() → bez session). Każdy ticker indywidualnie używa tego pattern — bulk korzysta automatycznie.

**Cache strategy:**
- `bulk_fetch_insider_screener` `@st.cache_data(ttl=86400)` in-memory (hash universe)
- Underlying `fetch_insider_transactions` + `fetch_institutional_holders` + `get_ratios_snapshot` — wszystkie też 24h cache per ticker
- Pierwszy bulk = cold cache ~5-7 min. Kolejne wywołania (lub inne universe) = warm cache hits per ticker → <2s

### UI (`pages/23_insider_screener.py`)

```python
st.set_page_config(page_title="Insider Screener", page_icon="👥", layout="wide")
setup_sidebar()
if not require_premium(23):
    st.stop()

st.markdown("# 👥 Bulk Insider Screener")
st.caption(
    "Bulk insider activity dla SP500 (456 spółek). "
    "Window: ostatnie 6 mc. ETF wykluczone (no insider data). "
    "GPW pominięte (yfinance nie ma SEC Form 4 dla PL)."
)

universe = tuple(ALL_SP500_TICKERS)
df = bulk_fetch_insider_screener(universe)

# Filtry expander
# Summary cards
# Sekcja 1: Top buyers + Top sellers bar charts
# Sekcja 2: Tabela screener
# Sekcja 3: Sektorowa heatmapa
# Cross-link selectbox + button
# CSV export
```

---

## UI szczegółowo

### Filtry expander (6 kontrolek)

```
┌─ FILTRY (expander, default expanded) ──────────────────────┐
│ Sektor [multiselect]    │  Status [Buy/Sell/Mixed/All]    │
│ Min |Net Value| ($)     │  Min beat streak (0-6 mc)       │
│ Min Market Cap (5 opt.) │  Sort by (9 metryk)             │
│ Top N (10/25/50/100/250)│  [🔄 Refresh cache]              │
└────────────────────────────────────────────────────────────┘
```

### Summary cards (4 metryki)

```
Spółek z danymi: X/456 │ Net Buyers 🟢: Y │ Net Sellers 🔴: Z │ Avg Net 6mc: $A
```

### Sekcja 1 — Top movers (2 bar charts side-by-side)

`st.columns(2)` — lewy: Top 10 Buyers (green bars, sortowane DESC po `net_value_6m`), prawy: Top 10 Sellers (red bars, sortowane ASC). Horizontal bars, `text=format_large_number(value)` outside.

### Sekcja 2 — Tabela screener (`st.dataframe`)

Kolumny: 🎯 Sentiment / Ticker / Nazwa / Sektor / Cap / Net 6mc / #Buys / #Sells / Top Buyer / Top Fund / Streak (ProgressColumn 0-6).

`st.column_config`:
- `Cap`: NumberColumn format "$%.0f"
- `Net 6mc`: NumberColumn format "$%+.0f"
- `Streak`: ProgressColumn min=0 max=6 format "%d mc"

(`top_inst_pct` jest w danych ale **nie wyświetlamy go w tabeli** — 11 kolumn już mocno przeładowane. Wartość dostępna w CSV export oraz przy hover na "Top Fund".)

### Sekcja 3 — Sektorowa heatmapa

Plotly horizontal bar, agregat `sector_agg = filtered.groupby("sector")["net_value_6m"].sum().sort_values()`. Kolory: green jeśli >0, red jeśli <0. Tekst outside z `format_large_number`.

### Cross-link do F13 (pattern z F14)

Selectbox (filtered tickers) + button "📈 Pokaż szczegóły":
```python
st.session_state["sp500_deep_dive_ticker"] = selected_ticker
st.session_state["sp500_pending_view"] = "deep_dive"
st.switch_page("pages/7_sp500.py")
```

**Bez `_navigate_to_deep_dive` helper** — wszystkie spółki SP500, brak rozgałęzienia na GPW.

### CSV export

```python
st.download_button(
    "📥 Eksport CSV (screener)",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name=f"insider_screener_sp500_{pd.Timestamp.now():%Y%m%d}.csv",
    mime="text/csv",
)
```

---

## Agregat logic — szczegóły

### `_aggregate_insider_for_ticker(ticker)`

1. **Fetch 3 endpointy** (każdy z F15 fallback chain):
   - `fetch_insider_transactions(ticker)` — 6mc historia
   - `fetch_institutional_holders(ticker)` — top 10 fundusze
   - `get_ratios_snapshot(ticker)` — sektor + market cap (z `Ticker.info`)

2. **Fallback sektor + nazwa:** jeśli `get_ratios_snapshot` zwróci None (yfinance.info fail), używamy lokalnego `SP500_SECTOR_MAP` + `SP500_NAMES`. Te są pełne dla 456 spółek, więc zawsze coś zwrócimy.

3. **Agregat transactions:**
   - `buys = transactions[Type == "Buy"]`, `sells = transactions[Type == "Sell"]`
   - `net_value_6m = sum(buys.Value) - sum(sells.Value)`
   - `n_buys`, `n_sells`, `avg_buy_size`, `avg_sell_size`
   - `top_buyer` = `buys.nlargest(1, "Value")` insider name (truncated 40 znaków)
   - `top_seller` = analogicznie
   - `sentiment`:
     - 🟢 jeśli `net > 0` i `n_buys >= 2`
     - 🔴 jeśli `net < 0` i `n_sells >= 2`
     - 🟡 mixed (np. tylko 1 transakcja, lub net mieszany)
   - `beat_streak_buys = _compute_buy_streak(transactions)`

4. **Agregat institutional:**
   - `top_institutional` = `institutional.iloc[0]["Holder"]` (truncated 40)
   - `top_inst_pct` = `institutional.iloc[0]["% Out"]`

5. **None gdy oba endpointy puste** — filter out z bulk DF.

### `_compute_buy_streak(transactions)`

```python
df["_yearmonth"] = pd.to_datetime(df.index).to_period("M")
months_sorted = sorted(df["_yearmonth"].unique(), reverse=True)

streak = 0
for ym in months_sorted[:6]:
    month_df = df[df["_yearmonth"] == ym]
    buy = month_df[month_df["Type"] == "Buy"]["Value"].sum()
    sell = month_df[month_df["Type"] == "Sell"]["Value"].sum()
    if buy > sell:
        streak += 1
    else:
        break
return streak
```

Exercise/Conversion ignorowane (informacyjne).

---

## Cache + Performance

| Dane | Klucz | TTL | Lokalizacja |
|------|-------|-----|-------------|
| `bulk_fetch_insider_screener(universe)` | hash(universe) | 24h | `@st.cache_data` in-memory |
| `fetch_insider_transactions(ticker)` (F15) | ticker | 24h | `@st.cache_data` |
| `fetch_institutional_holders(ticker)` (F15) | ticker | 24h | `@st.cache_data` |
| `get_ratios_snapshot(ticker)` (F11) | ticker | 24h | `@st.cache_data` |

**Performance budget:**
| Akcja | Budżet |
|-------|--------|
| Cold cache (456 spółek, fallback chain F15) | <8 min |
| Warm cache (in-memory) | <2 sek |
| Filtr/sort (client-side pandas) | <0.3 sek |
| Charts render | <1 sek |
| Cross-link → page 7 deep dive | <2 sek |

---

## Edge cases

### 1. yfinance flaky per ticker
Każdy `_aggregate_insider_for_ticker` używa F15 fallback chain. Per-ticker fail = None row → pomijany. Bulk akceptuje że X/456 nie zwróci.

### 2. Sekcja "Spółek z danymi" jako sanity check
Pokazujemy `X/456` w summary card. Jeśli `<50/456` → yfinance globalnie blocked, user widzi że to nie jego filtr.

### 3. Top buyer ≠ Top buyer value
`top_buyer` = insider z największą **pojedynczą** buy transakcją. Suma w `net_value_6m`. To pasuje do narracji "Tim Cook kupił $5M jednym ruchem".

### 4. Sektor mapping
Najpierw live yfinance.info, fallback do `SP500_SECTOR_MAP`. SP500 (456) zawsze ma sektor w static mapping. Edge case: spółka nowo dodana do SP500 ale nie w naszej mapie → "—".

### 5. Market cap None
yfinance `info["marketCap"]` może być None. Filter "Min Market Cap" traktuje NaN jako 0 — spółka odpada przy >0.

### 6. Sentiment 🟡 mixed
Edge case 1 transakcja: `net < 0` ale `n_sells = 1` → 🟡 (nie 🔴). User widzi że to nie konsystentny sygnał.

### 7. Beat streak — yfinance daty
`transactions.index` w F15 jest `DatetimeIndex` (z `Ticker.insider_transactions` index). Konwersja do period('M') powinna być bezpieczna. Edge case: timezone-aware → `pd.to_datetime(df.index).to_period("M")` normalizuje.

### 8. ETF w universe
ETF filtered out na poziomie `bulk_fetch_insider_screener` (`_get_etf_set` z F14). Defensive — nawet jeśli ktoś poda mieszankę.

### 9. Cross-link bez F14 watchlist
F16 nie używa watchlistu (jak F14). v2 może dodać filtr "tylko z watchlist".

### 10. Streamlit auto-deploy po pushu
Po dotychczasowych F13-F15 wszystkie deploy działają. Reboot rzadko potrzebny.

---

## Testing strategy

**Nowe testy w `tests/test_financials.py`** (~6 mock-based):

```python
def test_compute_buy_streak_full_buys()
def test_compute_buy_streak_breaks_on_sell_month()
def test_compute_buy_streak_empty()
def test_aggregate_insider_for_ticker_full_data()
def test_aggregate_insider_returns_none_when_no_data()
def test_bulk_fetch_insider_screener_filters_etf()
```

**Manual QA na produkcji:**
- AAPL — top buyer typowo Tim Cook, sentiment 🟢/🟡
- TSLA — typowo net seller (Elon)
- JPM — institutional dominance widoczna
- Bulk "Spółek z danymi" > 200/456 (sanity check)
- Sektorowa heatmapa renderuje (Tech, Health zwykle dominują)
- Cross-link AAPL → page 7 tab 8 deep dive 5. sub-tab Insiders
- ETF VOO/QQQ NIE w tabeli (filter ETF)
- Filtr Min Market Cap "$10B+" odsiewa małe cap
- Filtr "Net Buyers 🟢" → tylko 🟢 sentiment

---

## Pliki do utworzenia / zmiany

**Nowe pliki:**
- `pages/23_insider_screener.py` (~250 LOC)

**Modyfikowane:**
- `data/financials.py` — `_compute_buy_streak` + `_aggregate_insider_for_ticker` + `bulk_fetch_insider_screener` (~150 LOC)
- `tests/test_financials.py` — +6 testów
- `components/auth.py` — `PAGE_INFO[23] = ("👥", "Insider Screener", "Bulk insider activity SP500 — top buyers/sellers, sektory, beat streak")`
- `app.py` — `(23, "👥", "Insider Screener", "Bulk insider screener SP500 — kto kupuje, kto sprzedaje, sektorowa heatmapa", "pages/23_insider_screener.py")`
- `CLAUDE.md` — Pages structure (page 23 entry) + F16 paragraph w Key Design Decisions

**Bez zmian:**
- `pages/7_sp500.py`, `pages/8_gpw.py`, `pages/22_earnings_calendar.py` — F13/F14 reagują na session_state pre-set (już działa)
- `components/financials_ui.py` — F15 deep dive Insiders bez zmian

**Bez nowych modułów** — wszystko jako rozszerzenie istniejących.

---

## Definition of Done

- [ ] `_compute_buy_streak`, `_aggregate_insider_for_ticker`, `bulk_fetch_insider_screener` w `data/financials.py`
- [ ] `pages/23_insider_screener.py` z full UI (header + filtry + summary + 2 bar charts + tabela + heatmapa + cross-link + CSV)
- [ ] Tests pytest 6 nowych, full suite passing
- [ ] Manual QA na produkcji (AAPL/TSLA/JPM/ETF filter/sektorowa heatmapa/cross-link)
- [ ] `app.py` + `auth.py` + `CLAUDE.md` zaktualizowane
- [ ] Commit + push do `m4x-dm/gem-dashboard` main
- [ ] Streamlit Cloud auto-deploy zweryfikowany
- [ ] MEMORY.md entry F16
