"""Historia portfela odtworzona z operacji gotowkowych XTB + symulacja 'co gdyby' benchmarku.

Spec: docs/superpowers/specs/2026-11-20-moj-portfel-wykresy-design.md
Wartosc konta w dniu d = gotowka (suma wszystkich operacji do d) + sztuki x kurs (PLN).
Sztuki odtwarzamy z komentarzy 'OPEN BUY X 3 @ 100' / 'CLOSE BUY X 1.5/3 @ 110'.
Przeplywy (wplaty/wyplaty/przelewy) liczone per konto: przelew zwykle->IKE znosi sie
w widoku wszystkich kont, a w widoku samego IKE jest wplata.
"""
from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

from data.portfolio.tickers import currency_for, fx_ticker, price_divisor, xtb_to_yahoo
from data.portfolio.xtb_parser import XtbAccount

# Ticker w komentarzu bywa pominiety (wtedy bierzemy kolumne ticker); "a/b" = a z b sztuk (czesciowe wykonanie/zamkniecie)
TRADE_RE = re.compile(r"^(OPEN|CLOSE) BUY (?:([A-Z0-9.\-]*[A-Z][A-Z0-9.\-]*) )?([\d.]+)(?:/[\d.]+)? @ ([\d.]+)")
_TRADE_TYPES = ("stock purchase", "stock sell", "stock sale")
_FLOW_WORDS = ("deposit", "withdraw", "transfer")

# nazwa -> (ticker Yahoo funduszu total return, kurs waluty do PLN lub None)
BENCHMARKS: dict[str, tuple[str, str | None]] = {
    "WIG20": ("ETFBW20TR.WA", None),
    "mWIG40": ("ETFBM40TR.WA", None),
    "S&P 500": ("SPY", "USDPLN=X"),
    "Nasdaq 100": ("QQQ", "USDPLN=X"),
}
_SANITY = 0.5  # rozjazd kursu Yahoo vs cena transakcji (ETF-y LSE notowane przez XTB w USD)


def is_flow(op_type) -> bool:
    t = str(op_type or "").lower()
    return any(w in t for w in _FLOW_WORDS)


def parse_trades(cash_ops: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Transakcje akcji/ETF -> (DataFrame[time, xtb_ticker, qty, price, amount_pln], liczba niesparsowanych)."""
    rows, unparsed = [], 0
    for r in cash_ops.itertuples(index=False):
        if not str(r.type or "").lower().startswith(_TRADE_TYPES):
            continue
        m = TRADE_RE.match(str(r.comment or "").strip())
        if not m:
            unparsed += 1
            continue
        side, ticker, qty, price = m.group(1), m.group(2) or r.ticker, float(m.group(3)), float(m.group(4))
        if not ticker:
            unparsed += 1
            continue
        rows.append({"time": pd.Timestamp(r.time), "xtb_ticker": ticker,
                     "qty": qty if side == "OPEN" else -qty, "price": price,
                     "amount_pln": float(r.amount_pln or 0.0)})
    cols = ["time", "xtb_ticker", "qty", "price", "amount_pln"]
    return pd.DataFrame(rows, columns=cols), unparsed


def _daily_cum(times: pd.Series, values: pd.Series, idx: pd.DatetimeIndex) -> pd.Series:
    """Skumulowana suma wartosci na koniec kazdego dnia z idx (operacje weekendowe -> nastepna sesja)."""
    if len(values) == 0:
        return pd.Series(0.0, index=idx)
    s = pd.Series(values.to_numpy(dtype=float), index=pd.DatetimeIndex(times).normalize())
    cum = s.groupby(level=0).sum().sort_index().cumsum()
    return cum.reindex(cum.index.union(idx)).ffill().reindex(idx).fillna(0.0)


def _col(prices: pd.DataFrame, ticker: str | None) -> pd.Series | None:
    if not ticker or ticker not in prices.columns:
        return None
    s = prices[ticker].astype(float)
    return None if s.dropna().empty else s


def _unit_value_pln(xtb_ticker: str, trades: pd.DataFrame, prices: pd.DataFrame,
                    idx: pd.DatetimeIndex) -> pd.Series:
    """Wartosc 1 sztuki w PLN na kazdy dzien: Yahoo x FX, a gdy brak/niewiarygodne — z transakcji."""
    t = trades.assign(day=trades["time"].dt.normalize())
    unit = (t["amount_pln"].abs() / t["qty"].abs()).groupby(t["day"]).last()
    fallback = unit.reindex(unit.index.union(idx)).ffill().reindex(idx)

    currency = currency_for(xtb_ticker) or "PLN"
    close = _col(prices, xtb_to_yahoo(xtb_ticker))
    fx = pd.Series(1.0, index=prices.index) if currency == "PLN" else _col(prices, fx_ticker(currency))
    if close is None or fx is None:
        return fallback
    close = close / price_divisor(xtb_ticker)
    full = close.index.union(idx)
    close_ff = close.reindex(full).ffill()
    at_trades = close_ff.reindex(t["day"]).to_numpy()
    ratio = at_trades / t["price"].to_numpy()
    ratio = ratio[~pd.isna(ratio)]
    if len(ratio) and (abs(ratio - 1) > _SANITY).any():
        return fallback
    live = (close_ff * fx.reindex(full).ffill()).reindex(idx)
    return live.combine_first(fallback)


def reconstruct(accounts: list[XtbAccount], prices: pd.DataFrame,
                account_type: str | None = None) -> tuple[pd.DataFrame, dict]:
    """Dzienna historia: DataFrame[value, deposits, flow] (indeks: dni robocze) + kontrole.

    checks['volume_mismatch']: tickery, dla ktorych sztuki odtworzone z historii != Open Positions
    (eksport nie obejmuje calej historii konta / split). checks['unparsed']: niesparsowane transakcje.
    """
    chosen = [a for a in accounts if account_type is None or a.account_type == account_type]
    ops = pd.concat([a.cash_ops for a in chosen if not a.cash_ops.empty], ignore_index=True) \
        if any(not a.cash_ops.empty for a in chosen) else pd.DataFrame()
    checks = {"volume_mismatch": [], "unparsed": 0}
    if ops.empty:
        return pd.DataFrame(columns=["value", "deposits", "flow"]), checks
    ops["time"] = pd.to_datetime(ops["time"])
    start = ops["time"].min().normalize()
    end = ops["time"].max().normalize()
    if not prices.empty:
        end = max(end, pd.Timestamp(prices.index.max()).normalize())
    idx = pd.bdate_range(start, end)

    value = _daily_cum(ops["time"], ops["amount_pln"].fillna(0.0), idx)
    fl = ops[ops["type"].map(is_flow)]
    deposits = _daily_cum(fl["time"], fl["amount_pln"].fillna(0.0), idx)

    mismatch: set[str] = set()
    all_trades = []
    for acc in chosen:
        tr, unparsed = parse_trades(acc.cash_ops)
        checks["unparsed"] += unparsed
        all_trades.append(tr)
        final = tr.groupby("xtb_ticker")["qty"].sum() if not tr.empty else pd.Series(dtype=float)
        held = acc.lots.groupby("xtb_ticker")["volume"].sum() if not acc.lots.empty else pd.Series(dtype=float)
        for tk in final.index.union(held.index):
            if abs(float(final.get(tk, 0.0)) - float(held.get(tk, 0.0))) > 1e-6:
                mismatch.add(tk)
    nonempty = [tr for tr in all_trades if not tr.empty]
    trades = pd.concat(nonempty, ignore_index=True) if nonempty else all_trades[0]
    for tk, g in trades.groupby("xtb_ticker"):
        qty = _daily_cum(g["time"], g["qty"], idx)
        unit = _unit_value_pln(tk, g, prices, idx)
        value = value + (qty * unit).where(qty.abs() > 1e-12, 0.0).fillna(0.0)

    checks["volume_mismatch"] = sorted(mismatch)
    flow = deposits.diff().fillna(deposits.iloc[0])
    return pd.DataFrame({"value": value, "deposits": deposits, "flow": flow}), checks


def whatif(flows: pd.Series, bench: pd.Series, idx: pd.DatetimeIndex) -> pd.Series:
    """Wartosc 'co gdyby' kazdy przeplyw kupowal/sprzedawal benchmark po close dnia (lub najblizszej sesji)."""
    b = bench.astype(float).reindex(bench.index.union(idx)).reindex(idx)
    valid = b.dropna()
    if valid.empty:
        return pd.Series(float("nan"), index=idx)
    delta = pd.Series(0.0, index=idx)
    units = 0.0
    for d, amt in sorted(flows.items()):
        if not amt:
            continue
        after = valid[valid.index >= pd.Timestamp(d).normalize()]
        day, price = (after.index[0], after.iloc[0]) if not after.empty else (valid.index[-1], valid.iloc[-1])
        change = amt / price if amt > 0 else -min(units, -amt / price)
        units += change
        delta[day] += change
    return delta.cumsum() * b.ffill()


def benchmark_prices_pln(prices: pd.DataFrame) -> pd.DataFrame:
    """Close benchmarkow w PLN (kolumny: nazwy z BENCHMARKS); brak danych -> kolumna pominieta."""
    out = {}
    for name, (ticker, fx) in BENCHMARKS.items():
        s = _col(prices, ticker)
        if s is None:
            continue
        if fx:
            f = _col(prices, fx)
            if f is None:
                continue
            s = s.ffill() * f.ffill()
        out[name] = s
    return pd.DataFrame(out, index=prices.index)


def history_tickers(accounts: list[XtbAccount]) -> set[str]:
    """Tickery Yahoo potrzebne do historii: wszystkie papiery z transakcji, kursy walut, benchmarki."""
    out: set[str] = set()
    for acc in accounts:
        tr, _ = parse_trades(acc.cash_ops)
        for xt in set(tr["xtb_ticker"]) | set(acc.lots["xtb_ticker"]):
            y = xtb_to_yahoo(xt)
            if y:
                out.add(y)
            fx = fx_ticker(currency_for(xt))
            if fx:
                out.add(fx)
    for ticker, fx in BENCHMARKS.values():
        out.add(ticker)
        if fx:
            out.add(fx)
    return out


def history_start(accounts: list[XtbAccount]) -> datetime | None:
    times = [a.cash_ops["time"].min() for a in accounts if not a.cash_ops.empty]
    return pd.Timestamp(min(times)).to_pydatetime() if times else None


def fetch_history(tickers: tuple[str, ...], start: str) -> pd.DataFrame:
    """Dzienne close (auto_adjust) od `start` — JEDNO yf.download z timeoutem; blad -> pusty DataFrame."""
    if not tickers:
        return pd.DataFrame()
    try:
        import yfinance as yf
        data = yf.download(" ".join(tickers), start=start, auto_adjust=True,
                           progress=False, threads=True, timeout=30)
    except Exception:
        return pd.DataFrame()
    if data is None or data.empty or "Close" not in data.columns.get_level_values(0):
        return pd.DataFrame()
    close = data["Close"]
    if isinstance(close, pd.Series):
        close = close.to_frame(tickers[0])
    idx = pd.DatetimeIndex(close.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    close.index = idx.normalize()
    return close[~close.index.duplicated(keep="last")].sort_index()
