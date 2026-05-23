# CLAUDE.md — GEM ETF Dashboard

## Overview
Polish-language Streamlit dashboard for ETF analysis using Gary Antonacci's Global Equity Momentum (GEM) strategy. Analyzes 37 ETFs globally + 121 Polish stocks from GPW (WIG20/mWIG40/sWIG80) + ~200 cryptocurrencies + ~456 US stocks from S&P 500. 21 pages total.

## Tech Stack
- **Python 3.14**, **Streamlit 1.55**, **yfinance**, **pandas**, **numpy**, **plotly**, **reportlab**
- No database — data fetched live from Yahoo Finance (yfinance) + stooq.com (GPW indices) + CoinGecko (crypto fallback) + local CSV cache (GPW indices fallback for cloud)
- Cache: `st.cache_data` (prices TTL=1h, risk-free rate TTL=6h)
- Deploy: Streamlit Community Cloud at `https://gem-dashboard.streamlit.app/` (repo `m4x-dm/gem-dashboard`, branch `main`)

## Running
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project Structure
```
app.py                  # Entrypoint, sidebar, settings
.streamlit/config.toml  # Dark theme (gold #C9A84C, bg #0B0E1A)
data/
  etf_universe.py       # 37 ETFs with Polish names + categories (incl. ACWI + 6 sector SPDRs)
  gpw_universe.py       # 121 Polish stocks (WIG20/mWIG40/sWIG80) with .WA suffix
  crypto_universe.py    # ~200 cryptocurrencies with -USD suffix, 11 categories
  sp500_universe.py     # ~456 US stocks (S&P 500) with 11 GICS sectors
  downloader.py         # yfinance + stooq.com + CoinGecko fallback + CSV cache, st.cache_data, source tracking
  cache/                # Local CSV cache for GPW indices (wig20.csv, mwig40.csv, swig80.csv) — fallback when stooq blocked on cloud
  momentum.py           # Momentum calculations, GEM signals, backtest, seasonality, drawdowns, Monte Carlo, TA indicators, relative strength
components/
  formatting.py         # Polish formatting (%, numbers, colors)
  charts.py             # Plotly charts (price, momentum, drawdown, sparkline, seasonality heatmap, fan chart, TA overview/MACD/RSI)
  cards.py              # Signal cards, metric cards, macro cards, stats table, TA signal card, data status, alert banner (st.html)
  pdf_report.py         # PDF report generator (reportlab) — text+tables, no charts
  sidebar.py            # Shared sidebar config + CSS injection + favorites + alerts
pages/
  1_sygnal_gem.py       # Classic GEM signal + top 5 ETFs
  2_ranking.py          # Sortable ranking table 30+ ETFs
  3_wykresy.py          # Price, momentum, drawdown charts
  4_porownanie.py       # Compare 2-4 ETFs/indices + stats + correlation (incl. WIG20/mWIG40/sWIG80)
  5_backtest.py         # Backtest strategii (GEM, QQQ+SMA200, TQQQ+Momentum, porownanie)
  6_info.py             # GEM strategy explanation (Polish)
  7_sp500.py            # S&P 500 US stocks (7 tabs: ranking, wykresy, porownanie+stats, backtest, RS, screening, finanse)
  8_gpw.py              # Polish stocks GPW (7 tabs: ranking, wykresy, porownanie+stats incl. WIG20/mWIG40/sWIG80, backtest, RS, screening, finanse)
  9_kryptowaluty.py     # Crypto (7 tabs: ranking, alt/BTC ratio, wykresy, porownanie+stats, backtest, sygnaly TA, RS)
  10_portfolio.py       # Portfolio Builder (ticker selection, weights, backtest, correlation)
  11_screener.py        # Cross-Asset Screener (unified ranking from all 4 universes)
  12_makro.py           # Macro Dashboard (VIX, yield curve, DXY, S&P+200MA, gold, oil)
  13_sezonowosc.py      # Seasonality (monthly returns heatmap, avg month, Sell in May)
  14_waluta.py          # Currency PLN/USD impact on ETF returns
  15_drawdown.py        # Drawdown analysis (top N, duration, recovery, histogram)
  16_sygnaly.py         # GEM signal history (timeline, stats, calendar heatmap)
  17_monte_carlo.py     # Monte Carlo simulation (fan chart, distribution, probabilities)
  18_sektory.py         # Sector rotation (11 GICS sectors, heatmap, cycle)
  19_intermarket.py     # Intermarket analysis (overlay, ratio, rolling corr, regime)
  20_side_by_side.py    # Side-by-Side comparison of two assets (price, drawdown, RS)
```

## Key Design Decisions
- **Theme:** Gold `#C9A84C` accent, dark bg `#0B0E1A` — matches inwestowanie.edu.pl
- **Risk-free rate:** ^IRX (13-week T-bill) auto-fetched, with manual override in sidebar
- **GEM logic:** Classic (QQQ/VEA/EEM/ACWI/AGG) + Extended (31 ETFs, composite score)
- **Momentum 12M dla ETF (no skip) — od 2026-05-23:** `backtest_gem()`, `backtest_tqqq_mom()` i `walk_forward_gem()` używają default `lookback=252, skip=0` (czyste 12M). Powód: backtest 14y (2012-2026) na QQQ/VEA/EEM/ACWI/AGG wykazał +4,6 p.p. CAGR/rok (15,8% vs 11,2%), lepszy Sharpe (0,65 vs 0,42), mniejszy MaxDD (-29% vs -36%), PF 15,7 vs 3,8 — czyste 12m wygrywa zdecydowanie na koszykach ETF. Skip-month (Jegadeesh & Titman 1993) działa dla akcji indywidualnych — neutralizuje short-term reversal — ale na ETF indeksowych ten efekt znika, a opóźnienie sygnału o miesiąc szkodzi. Backwards compat: `backtest_gem(prices, rf, lookback=273, skip=21)` reprodukuje stary wynik.
- **Momentum 12-1 (skip-month) dla AKCJI indywidualnych:** `latest_returns()`, `calc_returns()` i `backtest_rotation()` (S&P 500 / GPW / krypto top N) DALEJ używają 12M-1 skip-month: `price(t-21) / price(t-273) - 1`, czyli zwrot od 13 mies. wstecz do 1 mies. wstecz. Akademicki konsensus pozostaje aktualny dla pojedynczych spółek.
- **Composite score:** 12M×50% + 6M×25% + 3M×15% + 1M×10% (12M=no-skip dla ETF w backtest_gem/tqqq, =skip-month dla rotation akcji przez latest_returns)
- **Backtest GEM:** Monthly rebalancing, GEM vs QQQ B&H vs ACWI B&H vs AGG B&H. Strategy selector: GEM Klasyczny, QQQ+SMA200, TQQQ+Momentum, Porownanie wszystkich
- **Backtest QQQ+SMA200:** Daily trend following — QQQ when price > SMA(200), AGG otherwise. `backtest_sma200()` in `momentum.py`
- **Backtest TQQQ+Momentum:** Synthetic TQQQ (QQQ daily return × 3), monthly momentum timing (QQQ 12M no-skip > rf → TQQQ, else AGG). `backtest_tqqq_mom()` in `momentum.py`. **Od 2026-05-23 default zmieniony z 12M-1 skip-month na czyste 12M.**
- **GEM Extended (page 21):** Rozszerzenie GEM o konfigurowalne universe (do 10+ ETF + krypto), top N equal-weight, safe_asset fallback (AGG/TLT/IEF/BIL/SHV/BND). `backtest_gem_extended()` w `momentum.py`. 5 presets (5-ETF baseline / 8-ETF gold-REIT-TLT / 3 z BTC). Backtest 11.5y (2014-2026) z BTC + 9 ETF Top-2: CAGR 42,8% / Sharpe 1,10 / MaxDD -52% (vs baseline 5-ETF: CAGR 15,8% / Sharpe 0,65 / MaxDD -29%). Strona ma duży disclaimer expander: hindsight bias (BTC), -50%+ DD, survivorship bias, deviation from Antonacci GEM philosophy. Commit 794bdd3.
- **Backtest GPW:** Momentum rotation (top N stocks) vs equal-weight B&H
- **Backtest Crypto:** Momentum rotation (top N) vs BTC B&H vs equal-weight B&H (365 trading days/year)
- **Backtest S&P 500:** Momentum rotation (top N) vs equal-weight B&H vs SPY B&H (252 trading days/year)
- **Alt/BTC ratio:** Measures altcoin strength vs Bitcoin — ratio = alt_price / btc_price, momentum of ratio. Filter: Top 10/20/50/100/200 (by market cap) or by category. Uses `_flexible_score()` (renormalized weights for available periods). Period selector includes "Strategia 12-1" (`iloc[-273:-21]`).
- **Inf handling:** `fmt_pct`/`color_for_value` treat `inf`/`-inf` as missing ("—"). `latest_returns` replaces inf with NaN at source
- **HTML rendering:** Use `st.html()` for custom HTML cards (NOT `st.markdown(unsafe_allow_html=True)` — causes code block rendering in Streamlit 1.55+). EXCEPTION: `st.html()` renders in sandboxed iframe — links (`<a href>`) cannot navigate parent app. Use `st.page_link()` for navigation.
- **CSS injection:** Only `sidebar.py` and `app.py` use `st.markdown(<style>..., unsafe_allow_html=True)` for CSS — `st.html()` strips `<style>` via DOMPurify
- **Homepage navigation:** `app.py` uses `st.container(border=True)` + `st.page_link()` for clickable cards (not `st.html()` which can't navigate)
- **Sidebar:** `header` element must NOT be hidden (`visibility:hidden`) — it contains sidebar toggle button. Use `[data-testid="stToolbar"]` targeting instead. Config: `toolbarMode = "minimal"`
- **Period "Strategia 12-1":** Available in Wykresy (page 3), Porownanie (page 4), Alt/BTC ratio (page 9), and comparison tabs in S&P 500 (page 7), GPW (page 8), Kryptowaluty (page 9) — downloads 2y data, trims to `iloc[-273:-21]` (the exact 12-1 momentum window)
- **Backtest periods:** Selector includes short intervals (1mo, 2mo, 3mo, 6mo, 1y) plus standard (2y–20y, max). GEM requires 273+ trading days — short periods show error message. yfinance has no "2mo" period — mapped to "3mo".
- **Portfolio Builder:** Multiselect from all 4 universes (max 20), 3 weight presets (equal, risk parity, reset), backtest custom vs equal-weight, correlation heatmap, drawdown
- **Cross-Asset Screener:** Unified `pd.concat()` ranking from ETF+S&P+GPW+Crypto, filters (class, min score, mom abs, top N), bar chart colored by asset class, CSV export
- **Macro Dashboard:** 2x3 grid of macro indicators (VIX, yield curve 10Y-13W, DXY, S&P+200MA, gold, oil), `macro_card()` + `sparkline_chart()`, traffic light signals, interpretation expander
- **Macro tickers:** ^VIX, ^TNX, ^IRX, ^IXIC, DX-Y.NYB, GC=F (gold spot USD/oz), CL=F, ^GSPC — each downloaded individually for reliability
- **Display vs Strategy tickers:** Market overview (sparklines, regime, intermarket) uses indices: `^IXIC` (Nasdaq Composite), `^TNX` (10Y Treasury yield), `GC=F` (gold spot). GEM strategy logic uses ETFs (QQQ, AGG) as trading instruments — do NOT change strategy tickers. `^TNX` is a yield (not price), so regime logic is inverted compared to AGG (rising yield = risk-on for equities).
- **Stooq.com integration:** GPW indices (WIG20, mWIG40, sWIG80) downloaded from `https://stooq.com/q/d/l/?s={sym}&i=d` via `download_stooq()` in `downloader.py`. Yahoo Finance has no historical data for these indices (returns only 1 row). Available in Porownanie (page 4) and GPW Porownanie tab (page 8). **Cloud fallback:** Stooq blocks GCP IPs (Streamlit Cloud), so `download_stooq()` falls back to local CSV cache in `data/cache/`. CSVs contain 10 years of data and should be periodically updated. All stooq requests use `requests.get()` with User-Agent header (NOT `pd.read_csv(url)` — it has no `timeout` parameter).
- **Data merge & trailing NaN:** When combining data from different sources (yfinance + stooq/CSV), series may end on different dates. `latest_returns()` applies `ffill()` before computing returns to avoid NaN from date misalignment.
- **Footer:** `render_footer()` in `sidebar.py` — called at the end of every page via `st.html()`. Shows "© 2026 M4X · Wszelkie prawa zastrzeżone"
- **Seasonality (page 13):** `monthly_returns_matrix()` in `momentum.py` — pivot year×month. `seasonality_heatmap()` in `charts.py` — RED→BG→GREEN. Tabs: heatmap, avg month bar, Sell in May (May-Oct vs Nov-Apr).
- **Currency PLN/USD (page 14):** `USDPLN=X` from yfinance. Formula: `ret_PLN = (1+ret_USD)*(1+ret_USDPLN)-1`. Tabs: kurs, USD vs PLN table, dual-axis overlay, hedging explainer.
- **Drawdown Analysis (page 15):** `top_drawdowns()` in `momentum.py` — iterates drawdown series, finds peak/trough/recovery. Tabs: annotated underwater chart, table, multi-asset comparison, histogram.
- **Signal History (page 16):** Reuses `backtest_gem()` with period="max" for full signal log. Tabs: current signal card, Gantt-style timeline, pie chart of time allocation, year×month calendar heatmap (colored by signal).
- **Monte Carlo (page 17):** `monte_carlo_simulation()` in `momentum.py` — bootstrap daily returns. `fan_chart()` in `charts.py` — percentile bands P5/P25/P50/P75/P95. Tabs: fan chart, final value histogram, probability cards.
- **Sector Rotation (page 18):** 11 SPDR sector ETFs (XLK,XLF,XLE,XLV,XLI,XLY,XLP,XLC,XLRE,XLU,XLB). Added 6 missing ETFs to `etf_universe.py`. Tabs: rolling 3M momentum heatmap, ranking bar, business cycle explainer, comparison.
- **Intermarket (page 19):** SPY,^TNX,GC=F,DX-Y.NYB,CL=F — cross-asset relationships. Tabs: normalized overlay, ratio pairs, rolling correlation, correlation matrix, risk-on/risk-off regime classifier. Note: uses ^TNX (yield) instead of AGG (price) — regime logic inverted for yields.
- **TA Signals (page 9, tab 6):** Trend-following system with 5 indicators, each scoring -1/0/+1:
  1. **Trend (EMA 200):** Price > EMA(200) = +1, below = -1. Primary trend filter. Skipped if <200 data points.
  2. **EMA crossover:** EMA(short) > EMA(long) = +1, below = -1.
  3. **MACD + histogram:** Requires crossover AND histogram direction confirmation. Cross+ with growing hist = +1, cross- with shrinking = -1, else 0.
  4. **RSI momentum:** RSI > 50 AND rising (5d) = +1, RSI < 50 AND falling = -1, else 0. No extreme 30/70 levels (avoids catching falling knives).
  5. **Bollinger %B:** %B > 0.5 (above middle band) = +1, < 0.5 = -1.
  - **Aggregate:** sum of 5 signals (-5 to +5). Threshold: >=3 = KUP, <=-3 = SPRZEDAJ, else NEUTRALNY. With 4 indicators (no EMA200): >=2 / <=-2.
  - Functions: `calc_ema()`, `calc_macd()`, `calc_rsi()`, `calc_bollinger()` in `momentum.py`. Charts: `ta_overview_chart()`, `macd_chart()`, `rsi_chart()` in `charts.py`. Card: `ta_signal_card()` in `cards.py`.
  - Daily signal markers on chart (BUY triangles up green, SELL triangles down red). Signal history table (last 20).
- **Sidebar separators:** nth-child(8) = ETF→markets, nth-child(11) = markets→tools, nth-child(14) = tools→analytics
- **Multi-source Fallback (F2):** `download_single()` tries yfinance → stooq.com → CoinGecko. `download_prices()` (bulk) also retries failed tickers individually via `_yfinance_single()` before stooq/CoinGecko fallback. Tracks sources in `st.session_state["_data_sources"]` and failures in `["_data_failures"]`. `COINGECKO_IDS` dict in `crypto_universe.py` (~50 top coins).
- **Small-selection download pattern:** Pages with 2-5 ticker selection (comparison, charts, RS tabs on pages 7, 8) use `download_single()` per ticker instead of bulk `download_prices()`. Each ticker gets its own cache entry and full fallback chain. More reliable than bulk download which can silently fail for individual tickers. Ranking/backtest tabs with 100+ tickers still use bulk `download_prices()`.
- **`latest_returns()` thresholds:** yfinance returns fewer rows than ideal trading days (6mo=123 not 126, 1y=250 not 252). Minimum thresholds: 1M≥19, 3M≥58, 6M≥115, 12M≥230. Uses ideal lookback (21/63/126) capped at `n-1`. 12M fallback: simple return from `iloc[0]` to `iloc[-1]` when skip-month (273 rows) unavailable but 230+ rows available.
- **Data Status (F3):** `data_status_card()` in `cards.py` — traffic light (green/yellow/red) based on failure %. Shows on page 0.
- **Price Alerts (F1):** Max 5 alerts in `st.session_state["alerts"]`. Sidebar expander to add (ticker, condition, threshold, period). `alert_banner()` in `cards.py` shows on page 0.
- **Favorites (F8):** Max 8 tickers in `st.session_state["favorites"]`. Sidebar section. Sparklines grid on page 0.
- **Relative Strength (F6):** `relative_strength(asset, benchmark)` in `momentum.py` — RS=asset/benchmark normalized to 100 + SMA(50,200). `rs_chart()` in `charts.py`. Integrated as new tabs on pages 7 (vs SPY), 8 (vs WIG20), 9 (vs BTC), and as section on page 4.
- **Side-by-Side (F9):** Page 20 (`pages/20_side_by_side.py`) — two-column comparison of any two assets. Includes price chart, drawdown, stats table, correlation, RS chart. Premium page.
- **Finanse tab (F11):** 7-my tab w `pages/7_sp500.py` + `pages/8_gpw.py` (`💰 Finanse`). 4 karty w grid 2×2: ratios snapshot (PE/Fwd PE/EV-EBITDA/EBITDA/ROE/ROA/FCF/Debt-E/P-B/Div Yield/Profit M./Rev Gr.), forward konsensus EPS (Plotly bar chart 4 periods z error bars), earnings history (tabela last 8Q actual vs estimate z surprise %), analyst recos (target mean + upside % + reco badge). Dane z yfinance (`Ticker.info`, `.earnings_estimate`, `.earnings_history`). Cache 24h przez `@st.cache_data(ttl=86400)` w `data/financials.py`. Selectbox pre-fill z `st.session_state["sp_finanse_default"]` / `["gpw_finanse_default"]` ustawionych w ranking tabach. Spec: `docs/superpowers/specs/2026-05-14-finanse-spolki-design.md`.
- **Screener Fundamentalny (F12):** 6-ty tab `📊 Screening` (przed `💰 Finanse`) w pages 7_sp500 + 8_gpw. Pełna tabela 11 wskaźników dla subset universe (SP500_TOP100 + WIG20+mWIG40 = ~160 spółek). Filtry: 6 main (P/E max, ROE min, EV/EBITDA max, sektor, cap min, BUY only) + 5 advanced (div yield, rev growth, debt/E, profit margin, P/B). Sort by 9 wskaźników (ascending properly per metric: P/E rosnąco = taniej, ROE malejąco = więcej). Top N: 5/10/15/25/all. 4 summary cards + CSV export. Klik wiersza → pre-fill `sp_finanse_ticker` / `gpw_finanse_ticker` w session_state. Reuses `bulk_fetch_universe()` w `data/financials.py` (cache 24h, reuses `_fetch_info` per ticker — 1 yfinance call per ticker per 24h dla obu tabów Finanse+Screening). GPW edge case: kolumna EV/EBITDA pokazuje "N/A bank" dla `GPW_BANKS`. Spec: `docs/superpowers/specs/2026-05-18-screener-fundamentalny-design.md`. **Pułapka:** helpery `_apply_screener_filters` etc. MUSZĄ być zdefiniowane PRZED `with tab6:` (Streamlit `@st.fragment` wykonuje fragment przy linii wywołania — NameError gdy helpery niżej w pliku).
- **SP500_TOP100:** statyczna lista 100 spółek by market cap w `data/sp500_universe.py`. Refresh raz na 6 miesięcy (Q1 + Q3 results). Last verified: 2026-05-18. 5 tickerów (BX/UBER/MMC/ANET/INTC) brak w lokalnym ALL_SP500_TICKERS — yfinance obsłuży je bezpośrednio.
- **CRITICAL `@st.cache_data` gotcha (utrwalone 2026-05-19):** argumenty z **`_` prefix są IGNOROWANE w cache key** (Streamlit konwencja). `def f(_arg)` cache'uje pod kluczem bez `_arg` — wszystkie wywołania z różnymi `_arg` trafiają w ten sam cache. Skutek: bug `bulk_fetch_universe(_tickers_tuple)` zwracał SP500 dict dla GPW request (commit `0842cbe` fix). **Nigdy nie prefiksuj `_` argumentów które MUSZĄ być w cache key.** Tuple jest hashable, więc nie ma potrzeby workaround.
- **yfinance Cloud bot detection:** Streamlit Cloud (GCP IPs) ma blokowany TLS fingerprint przez Yahoo Finance. Fix w `data/financials.py:_get_yf_session()` używa `curl_cffi.requests.Session(impersonate="chrome")` — Chrome TLS handshake omija detection. Plus retry 3× z exponential backoff (0.5s/1.5s/4.5s) gdy info bez `currentPrice`/`regularMarketPrice`/`trailingEps`. Wymaga `curl-cffi>=0.7.0` w `requirements.txt`. Lokalnie bez curl_cffi fallback do default yfinance (graceful).
- **GPW banks edge case:** `data/gpw_universe.py` eksportuje `GPW_BANKS: set[str]` (PKO/PEO/SPL/MBK/BHW/BNP/ING/MIL/ALR). `data/financials.is_bank(ticker)` lookup. Tab Finanse na GPW page wywołuje `ratios_card(snap, is_bank=is_bank(ticker))` — dla banków EBITDA/EV-EBITDA/FCF ukryte z labelem "N/A bank" (banki używają NII/NIM zamiast EBITDA). Last verified: 2026-05-15.
- **yfinance Ticker.info gotcha:** `Ticker.info` to OSOBNE API niż `yf.download()` — działa per-ticker bez rate-limit problemów. `earnings_estimate` / `earnings_history` to lazy properties zwracające pandas DataFrame; mogą zwrócić empty DF dla nieznanych tickerów (np. `CCC.WA` 404). Wszystkie 4 funkcje w `data/financials.py` wrapped w `try/except Exception` → return `{}` / `None` (graceful).
- **PDF Export (F10):** `components/pdf_report.py` — reportlab-based, text+table report (no charts). Font: Arial (Windows) / Helvetica (Linux). Integrated on page 0 via expander with section checkboxes + download button.

## ETF Universe (37 tickers, 7 categories)
Akcje USA (SPY, QQQ, VTI, VOO, IWM), Rynki rozwinięte (VEA, EFA, ACWI, VGK, EWJ, EWU),
Rynki wschodzące (VWO, EEM, FXI), Obligacje USA (AGG, BND, TLT, IEF, SHY, TIP),
Złoto/surowce (GLD, IAU, GSG, DBC), REIT (VNQ, VNQI),
Sektory USA (XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLC, XLRE, XLU, XLB)

## GPW Universe (121 tickers, 3 indices)
- **WIG20** (19 spolek): PKO, CDR, KGH, PZU, LPP, DNP, PKN, PEO, ALE, etc.
- **mWIG40** (36 spolek): 11B, ACP, BFT, CAR, CCC, DOM, ING, WPL, **XTB**, **GPP** (Grupa Pracuj), etc.
- **sWIG80** (66 spolek): PLW, MBR, SNT, RBW, TOR, VOX, OPN, **MUR** (Murapol), **VOT** (Votum), etc.
- All tickers use `.WA` suffix for Yahoo Finance

## Crypto Universe (~194 tickers, 11 categories)
Layer 1 (BTC, ETH, SOL, ADA, XRP...), Layer 2/Skalowanie (MATIC, OP, ARB...),
DeFi (UNI, LINK, AAVE, MKR...), Exchange Tokens (OKB, CRO, LEO...),
Memecoiny (DOGE, SHIB, PEPE...), Gaming/Metaverse (AXS, SAND, MANA...),
AI/Data (RNDR, FET, TAO...), Prywatnosc (XMR, ZEC...), Infrastruktura (QNT, ENS, CHZ...),
RWA/Tokenizacja (ONDO, MNT...), Inne (LTC, BCH, ETC...)
- All tickers use `-USD` suffix for Yahoo Finance
- `CRYPTO_BY_MCAP` — ordered list ~195 tickers by approximate market cap (for Top N filters)

## S&P 500 Universe (~456 tickers, 11 GICS sectors)
Information Technology (AAPL, MSFT, NVDA, AVGO...), Health Care (LLY, UNH, JNJ, ABBV...),
Financials (BRK-B, JPM, V, MA...), Consumer Discretionary (AMZN, TSLA, HD, MCD...),
Communication Services (META, GOOG, NFLX...), Industrials (GE, CAT, RTX, UNP...),
Consumer Staples (PG, COST, KO, PEP...), Energy (XOM, CVX, COP...),
Utilities (NEE, SO, DUK...), Real Estate (AMT, PLD, CCI...), Materials (LIN, APD, ECL...)
- No ticker suffix — Yahoo Finance handles US stocks natively
- Backtest uses SPY as additional benchmark

## Notes
- All UI text is in Polish
- Users can add custom tickers via sidebar
- "Odśwież dane" button clears st.cache_data
- GPW stocks: yfinance supports `.WA` suffix for Warsaw Stock Exchange
- GPW indices: WIG20/mWIG40/sWIG80 from stooq.com with CSV fallback (yfinance returns only 1 row for these)
- Stooq downloads: ALWAYS use `requests.get(url, headers=_HEADERS, timeout=15)` + `pd.read_csv(StringIO(resp.text))`. NEVER use `pd.read_csv(url, timeout=N)` — `timeout` is not a valid pd.read_csv parameter
