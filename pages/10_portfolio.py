"""Strona 10: Portfolio Builder — budowanie i analiza portfela."""

import streamlit as st
import pandas as pd
import numpy as np
from components.sidebar import setup_sidebar, get_risk_free, render_footer
from data.etf_universe import ALL_TICKERS as ETF_TICKERS, ETF_NAMES
from data.gpw_universe import ALL_GPW_TICKERS, GPW_NAMES
from data.sp500_universe import ALL_SP500_TICKERS, SP500_NAMES
from data.crypto_universe import ALL_CRYPTO_TICKERS, CRYPTO_NAMES
from data.downloader import download_prices
from data.momentum import latest_returns, correlation_matrix
from components.formatting import (
    fmt_pct, fmt_number, color_for_value,
    GOLD, GREEN, RED, MUTED, BG_CARD, BORDER,
)
from components.charts import (
    price_chart, drawdown_chart, equity_chart, correlation_heatmap,
    category_pie, COLORS,
)
from components.cards import stats_table

st.set_page_config(page_title="Portfolio Builder", page_icon="🏗️", layout="wide")
setup_sidebar()

st.markdown("# 🏗️ Portfolio Builder")
st.caption("Zbuduj portfel z dowolnych aktywow, ustaw wagi i przeanalizuj wyniki")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_asset_class(ticker: str) -> str:
    """Wykrywa klase aktywow na podstawie tickera."""
    if ticker in ETF_NAMES:
        return "ETF"
    if ticker in GPW_NAMES:
        return "GPW"
    if ticker in SP500_NAMES:
        return "S&P 500"
    if ticker in CRYPTO_NAMES:
        return "Crypto"
    return "Inny"


def _ticker_name(ticker: str) -> str:
    """Nazwa tickera z odpowiedniego universum."""
    for names in [ETF_NAMES, SP500_NAMES, GPW_NAMES, CRYPTO_NAMES]:
        if ticker in names:
            return names[ticker]
    return ticker


def _has_crypto(tickers: list[str]) -> bool:
    """Czy lista zawiera kryptowaluty (wplywa na trading_days)."""
    return any(t in CRYPTO_NAMES for t in tickers)


def _risk_parity_weights(prices: pd.DataFrame, window: int = 60) -> dict[str, float]:
    """Wagi inverse-volatility (risk parity)."""
    rets = prices.pct_change().dropna()
    recent = rets.tail(window)
    vols = recent.std()
    vols = vols.replace(0, np.nan).dropna()
    if vols.empty:
        return {t: 1.0 / len(prices.columns) for t in prices.columns}
    inv_vol = 1.0 / vols
    weights = inv_vol / inv_vol.sum()
    return weights.to_dict()


def _backtest_portfolio(prices: pd.DataFrame, weights: dict[str, float],
                        start_capital: float = 10000,
                        rebalance_freq: int = 21,
                        trading_days_year: int = 252) -> dict:
    """Backtest portfela z rebalansowaniem.

    Returns dict z equity curve (pd.Series) i stats dict.
    """
    # Align prices — only common dates, forward fill
    aligned = prices[list(weights.keys())].dropna(how="all").ffill().dropna()
    if len(aligned) < 10:
        return None

    daily_rets = aligned.pct_change().dropna()
    dates = daily_rets.index

    w = np.array([weights.get(t, 0) for t in aligned.columns])
    w = w / w.sum()  # normalize

    equity = [start_capital]
    current_w = w.copy()

    for i, date in enumerate(dates):
        day_rets = daily_rets.loc[date].values
        # Update portfolio value
        port_ret = np.nansum(current_w * day_rets)
        equity.append(equity[-1] * (1 + port_ret))

        # Update weights after returns (drift)
        current_w = current_w * (1 + day_rets)
        w_sum = current_w.sum()
        if w_sum > 0:
            current_w = current_w / w_sum

        # Rebalance
        if (i + 1) % rebalance_freq == 0:
            current_w = w.copy()

    eq_series = pd.Series(equity[1:], index=dates, name="Portfel")

    # Stats
    years = len(eq_series) / trading_days_year
    total_ret = eq_series.iloc[-1] / eq_series.iloc[0] - 1
    cagr = (eq_series.iloc[-1] / eq_series.iloc[0]) ** (1 / years) - 1 if years > 0 else 0
    running_max = eq_series.cummax()
    drawdown = (eq_series - running_max) / running_max
    max_dd = drawdown.min()
    daily_ret = eq_series.pct_change().dropna()
    sharpe = daily_ret.mean() / daily_ret.std() * np.sqrt(trading_days_year) if daily_ret.std() > 0 else 0

    stats = {
        "CAGR": cagr,
        "Calkowity zwrot": total_ret,
        "Max Drawdown": max_dd,
        "Sharpe": sharpe,
    }

    return {"equity": eq_series, "stats": stats, "drawdown": drawdown}


# ---------------------------------------------------------------------------
# Build full ticker list with labels
# ---------------------------------------------------------------------------
ALL_OPTIONS = {}
for t in ETF_TICKERS:
    ALL_OPTIONS[t] = f"[ETF] {t} — {ETF_NAMES.get(t, t)}"
for t in ALL_SP500_TICKERS:
    if t not in ALL_OPTIONS:
        ALL_OPTIONS[t] = f"[S&P] {t} — {SP500_NAMES.get(t, t)}"
for t in ALL_GPW_TICKERS:
    ALL_OPTIONS[t] = f"[GPW] {t} — {GPW_NAMES.get(t, t)}"
for t in ALL_CRYPTO_TICKERS:
    ALL_OPTIONS[t] = f"[Crypto] {t} — {CRYPTO_NAMES.get(t, t)}"

ticker_list = list(ALL_OPTIONS.keys())

# ---------------------------------------------------------------------------
# 1. Wybor tickerow
# ---------------------------------------------------------------------------
st.markdown("### 1. Wybor aktywow")

selected = st.multiselect(
    "Wybierz aktywa (max 20)",
    options=ticker_list,
    default=[],
    max_selections=20,
    format_func=lambda t: ALL_OPTIONS.get(t, t),
)

if not selected or len(selected) < 2:
    st.info("Wybierz co najmniej 2 aktywa, aby rozpoczac analize.")
    st.stop()

# ---------------------------------------------------------------------------
# 2. Wagi
# ---------------------------------------------------------------------------
st.markdown("### 2. Wagi portfela")

# Presets
pcol1, pcol2, pcol3 = st.columns(3)
with pcol1:
    if st.button("Equal-weight", use_container_width=True):
        eq_w = round(100.0 / len(selected), 2)
        for t in selected:
            st.session_state[f"w_{t}"] = eq_w
with pcol2:
    if st.button("Risk Parity", use_container_width=True):
        with st.spinner("Obliczam wagi risk parity..."):
            rp_prices = download_prices(selected, period="1y")
            if rp_prices.empty or len(rp_prices) < 10:
                st.warning("Nie udalo sie pobrac danych — uzywam equal-weight.")
                rp_weights = {t: 1.0 / len(selected) for t in selected}
            else:
                rp_weights = _risk_parity_weights(rp_prices)
            for t in selected:
                st.session_state[f"w_{t}"] = round(rp_weights.get(t, 0) * 100, 2)
with pcol3:
    if st.button("Reset", use_container_width=True):
        for t in selected:
            st.session_state[f"w_{t}"] = 0.0

# Weight inputs
n_cols = min(len(selected), 4)
weight_cols = st.columns(n_cols)
weights_raw = {}

for i, t in enumerate(selected):
    col = weight_cols[i % n_cols]
    cls = _detect_asset_class(t)
    default_val = st.session_state.get(f"w_{t}", round(100.0 / len(selected), 2))
    w = col.number_input(
        f"{t} ({cls})",
        min_value=0.0, max_value=100.0,
        value=float(default_val), step=0.5,
        key=f"w_{t}",
    )
    weights_raw[t] = w

total_weight = sum(weights_raw.values())

# Validation
if abs(total_weight - 100.0) > 0.5:
    st.warning(f"Suma wag: **{total_weight:.1f}%** — powinna wynosic 100%. Roznica: {total_weight - 100:.1f}%")
    weights_valid = False
else:
    st.success(f"Suma wag: {total_weight:.1f}% ✓")
    weights_valid = True

if not weights_valid:
    st.stop()

# Normalize to fractions
weights = {t: w / 100.0 for t, w in weights_raw.items() if w > 0}
active_tickers = list(weights.keys())

if len(active_tickers) < 2:
    st.warning("Co najmniej 2 aktywa musza miec niezerowa wage.")
    st.stop()

# ---------------------------------------------------------------------------
# 3. Analiza portfela
# ---------------------------------------------------------------------------
st.markdown("### 3. Analiza portfela")

with st.spinner("Pobieram dane i analizuje portfel..."):
    prices = download_prices(active_tickers, period="2y")

if prices.empty:
    st.error("Nie udalo sie pobrac danych.")
    st.stop()

# -- Pie chart alokacji --
acol1, acol2 = st.columns([1, 2])
with acol1:
    pie_data = {f"{t} ({_detect_asset_class(t)})": weights_raw[t] for t in active_tickers}
    st.plotly_chart(category_pie(pie_data, "Alokacja portfela"), use_container_width=True)

# -- Tabela zwrotow holdingsow --
with acol2:
    st.markdown("#### Zwroty holdingsow")
    rets = latest_returns(prices)
    rets["Waga"] = rets.index.map(lambda t: weights.get(t, 0))
    rets["Nazwa"] = rets.index.map(lambda t: _ticker_name(t))
    display_rets = rets[["Nazwa", "Waga", "1M", "3M", "6M", "12M"]].copy()
    for col in ["1M", "3M", "6M", "12M"]:
        display_rets[col] = display_rets[col].apply(lambda x: fmt_pct(x) if pd.notna(x) else "—")
    display_rets["Waga"] = display_rets["Waga"].apply(lambda x: f"{x*100:.1f}%")
    st.dataframe(display_rets, use_container_width=True, height=min(400, 40 + 35 * len(display_rets)))

# -- Correlation heatmap --
st.markdown("#### Macierz korelacji")
corr = correlation_matrix(prices, period=252)
st.plotly_chart(correlation_heatmap(corr), use_container_width=True)

# -- Backtest --
st.markdown("#### Backtest portfela")

trading_days = 365 if _has_crypto(active_tickers) else 252

# Custom portfolio
result = _backtest_portfolio(prices, weights, trading_days_year=trading_days)

# Equal-weight benchmark
eq_weights = {t: 1.0 / len(active_tickers) for t in active_tickers}
result_eq = _backtest_portfolio(prices, eq_weights, trading_days_year=trading_days)

if result and result_eq:
    # Equity curves
    curves = {"Portfel custom": result["equity"]}
    curves["Equal-weight"] = result_eq["equity"]
    st.plotly_chart(equity_chart(curves, "Krzywa kapitalu — portfel vs equal-weight"), use_container_width=True)

    # Stats
    all_stats = {"Portfel custom": result["stats"]}
    all_stats["Equal-weight"] = result_eq["stats"]
    stats_table(all_stats)

    # Drawdown
    dd_df = pd.DataFrame({
        "Portfel custom": result["drawdown"],
        "Equal-weight": result_eq["drawdown"],
    })
    st.plotly_chart(drawdown_chart(dd_df, "Drawdown — spadek od szczytu"), use_container_width=True)
else:
    st.warning("Za malo danych do przeprowadzenia backtestu (wymagane min. 10 dni wspolnych danych).")

render_footer()
