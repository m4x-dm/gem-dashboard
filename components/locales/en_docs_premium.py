"""Katalog EN — dlugie opisy (tr_doc) na stronach Premium."""

DOCS_PREMIUM: dict[str, str] = {
    "backtest_gem": """
**Global Equity Momentum (GEM)** is a strategy developed by **Gary Antonacci**
(*Dual Momentum Investing*, 2014). It combines absolute momentum (vs the risk-free rate) with relative
momentum (comparing markets).

### Rules
| Step | Condition | Action |
|------|-----------|--------|
| 1 | QQQ 12M momentum < risk-free rate | → Bonds (AGG) |
| 2 | QQQ 12M > risk-free rate | → Compare QQQ vs VEA vs EEM vs ACWI, buy the best |

**Monthly rebalance** (every 21 trading days). Always 100% in one asset.
**12M momentum (no skip) — since 2026-05-23.** Previously skip-month (12-1), but a 14-year
backtest on the ETF basket showed +4.6 pp CAGR per year for plain 12M (skip-month works
for individual stocks, not for index ETFs).

### Advantages
- **Simple** — one decision a month, 5 assets
- **Systematic** — takes emotions out, clear rules
- **Protection in bear markets** — absolute momentum flags a downtrend
- **Geographic diversification** — moves between the US, developed and emerging markets

### Drawbacks
- **Lagging signals** — the 12M lookback reacts late to sudden reversals
- **Whipsaws** — false signals in a sideways market
- **No diversification** — 100% in one asset (all-in/all-out)
- **Transaction costs** — frequent signal changes mean commissions and taxes

Full description of the strategy → the **About the strategy** page in the menu.
""",
    "backtest_sma200": """
**SMA 200 (simple moving average)** is one of the oldest and simplest trend-following strategies.
The 200-day moving average smooths out price noise and shows the long-term direction of the trend.

### Rules
| Condition | Action |
|-----------|--------|
| QQQ price > SMA(200) | → Hold QQQ (uptrend) |
| QQQ price < SMA(200) | → Move to AGG bonds (downtrend) |

**Daily rebalance** — the strategy checks the condition every day (not monthly like GEM),
so it reacts faster to trend changes.

### Advantages
- **Simplicity** — one condition, zero subjectivity
- **Protection in bear markets** — historically sidesteps most large declines (2008, 2020, 2022)
- **Faster reaction than GEM** — a daily check vs a monthly rebalance

### Drawbacks
- **Whipsaw** — in a sideways market it produces many false signals (frequent crossings above/below the SMA)
- **Lag** — the SMA 200 reacts ~2-4 weeks late to a sudden change of trend
- **Transaction costs** — frequent switching = more commissions and taxable events
- **No relative momentum** — it does not compare markets with each other (only QQQ vs its SMA)

### Historical context
The SMA 200 strategy has been popular since the 1990s. Mebane Faber, in
*"A Quantitative Approach to Tactical Asset Allocation"* (2007), showed
that a 10-month SMA (≈200 days) significantly reduces drawdown while keeping
most of the stock market's returns.
""",
    "backtest_tqqq": """
**TQQQ + Momentum** combines the 3x leveraged NASDAQ 100 with momentum timing, to avoid
holding leverage in a bear market. TQQQ is **synthesised** from QQQ (daily return × 3), which allows
testing the strategy further back than 2010 (when the real TQQQ launched).

### Rules
| Condition | Action |
|-----------|--------|
| QQQ 12M momentum > risk-free rate | → Hold TQQQ (3x QQQ) |
| QQQ 12M momentum < risk-free rate | → Move to AGG bonds |

**Monthly rebalance** (every 21 trading days) — the same timing as classic GEM.
The signal is based on QQQ's **12M momentum (no skip)** vs the risk-free rate — since 2026-05-23.

### Advantages
- **Potential for extreme gains** — 3x leverage in a strong uptrend
- **Momentum protection** — exits leverage when the trend reverses
- **Simple signal** — the same 12M momentum as GEM, no extra complexity

### Drawbacks and risks
- **Extreme drawdown** — even with timing, max DD can exceed -50% to -80%
- **Volatility decay** — 3x daily leverage ≠ 3x the return over longer periods (erosion in sideways markets)
- **Lagging signal** — 12M momentum reacts late, and leverage magnifies losses in that window
- **Synthetic TQQQ** — ignores the cost of leverage (financing, tracking error of the real ETF). The `daily_return × 3` model overstates returns in volatile periods — the real TQQQ does worse because of volatility drag
- **Not for everyone** — requires a high risk tolerance and a long investment horizon

### TQQQ buy & hold vs TQQQ + Momentum
TQQQ buy & hold has historically delivered extremely high returns in bull markets, but drawdowns
of -70% to -80% are unbearable for most investors. Momentum timing significantly
reduces drawdown at the cost of part of the gains — whether that trade-off is worth it depends
on your individual risk tolerance.

> **WARNING:** this strategy is experimental and extremely risky.
> 3x leverage is not suitable for most investors.
""",
    "gem_extended_warning": """
**GEM Extended is NOT Antonacci's classic GEM.** Classic GEM holds 100% in one
of 5 ETFs — an academically tested "dual momentum" philosophy. Adding candidates (BTC, sectors,
REITs, gold) and holding the top N equal-weight is **multi-asset trend following**, which historically
gives a higher CAGR but demands a higher tolerance for drawdowns.

**The biggest pitfalls:**
- **Hindsight bias** — BTC has a 50% CAGR since 2014, but in 2014 nobody knew it would.
  Putting "BTC in the universe" is obvious in 2026; in 2014 it was not.
- **Drawdowns can exceed -50%** — the BTC + top-1 strategy had a max DD of -82% (the 2022 crypto crash).
  The backtest shows the numbers, but living through it is a different matter.
- **Backtest != live** — ignores slippage, the bid-ask spread, taxes on crypto trading
  (19% Polish capital gains tax + transaction tracking) and execution delays.
- **Survivorship bias** — the ETF/crypto universe that exists today is the one that survived.
  Those that collapsed (Luna, FTX-related tokens) are excluded — which inflates the results.
- **With BTC the philosophy changes** — the strategy stops being "Global EQUITY Momentum" and becomes
  "multi-asset trend following". It is not a worse strategy — but it is not GEM.

**Practical recommendation:** start with the **5-ETF baseline** (classic GEM). If you accept
a deeper drawdown for a higher CAGR, try **8 ETFs with gold/REIT/TLT (no crypto)**. Add crypto
ONLY once you understand the risk, and keep at most 5-10% of your portfolio in this allocation.
""",
}
