"""Wycena portfela: pozycje z eksportu XTB x kursy Yahoo x kursy walut (PLN)."""
from __future__ import annotations

import math

import pandas as pd

from data.portfolio.tickers import currency_for, fx_ticker, price_divisor, xtb_to_yahoo
from data.portfolio.xtb_parser import XtbAccount

DEPOSIT_TYPES = {"deposit", "ike deposit", "ikze deposit", "withdrawal"}
DIVIDEND_TYPES = {"dividend", "divident", "withholding tax"}
POSITION_COLUMNS = ["account", "xtb_ticker", "yahoo", "name", "category", "currency", "volume",
                    "avg_price", "price", "value_pln", "cost_pln", "profit_pln", "profit_pct",
                    "day_pln", "share", "live"]


def _sum_types(cash_ops: pd.DataFrame, types: set[str]) -> float:
    if cash_ops is None or cash_ops.empty:
        return 0.0
    mask = cash_ops["type"].astype(str).str.strip().str.lower().isin(types)
    return float(cash_ops.loc[mask, "amount_pln"].sum())


def deposits_net(cash_ops: pd.DataFrame) -> float:
    """Wplaty - wyplaty. Przelew z konta zwyklego na IKE/IKZE jest ujemny na koncie zwyklym
    i dodatni na IKE/IKZE, wiec suma po wszystkich kontach liczy pieniadze z banku raz."""
    return _sum_types(cash_ops, DEPOSIT_TYPES)


def dividends_net(cash_ops: pd.DataFrame) -> float:
    """Dywidendy po podatku u zrodla."""
    return _sum_types(cash_ops, DIVIDEND_TYPES)


def _quote(quotes: pd.DataFrame, ticker: str | None, col: str) -> float | None:
    if ticker is None or quotes is None or ticker not in quotes.index:
        return None
    v = quotes.at[ticker, col]
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def _fx(quotes: pd.DataFrame, currency: str | None) -> float | None:
    if currency == "PLN":
        return 1.0
    return _quote(quotes, fx_ticker(currency), "last")


def value_portfolio(accounts: list[XtbAccount], quotes: pd.DataFrame,
                    account_type: str | None = None) -> tuple[pd.DataFrame, dict]:
    """Zwraca (tabela pozycji per konto+ticker posortowana malejaco po wartosci, podsumowanie).

    quotes: DataFrame indeksowany tickerem Yahoo, kolumny 'last' i 'prev' (ostatni i
    przedostatni close); zawiera tez kursy walut 'USDPLN=X' itd. Brak tickera -> kurs z pliku.
    account_type: None = wszystkie konta, inaczej 'IKE' / 'IKZE' / 'ZWYKLE'.
    """
    chosen = [a for a in accounts if account_type is None or a.account_type == account_type]
    rows = []
    for acc in chosen:
        if acc.lots.empty:
            continue
        for xtb_ticker, g in acc.lots.groupby("xtb_ticker", sort=False):
            volume = float(g["volume"].sum())
            avg_price = float((g["open_price"] * g["volume"]).sum() / volume) if volume else float("nan")
            cost = float(g["cost_pln"].sum())
            yahoo = xtb_to_yahoo(xtb_ticker)
            currency = currency_for(xtb_ticker) or "PLN"
            div = price_divisor(xtb_ticker)
            last, prev = _quote(quotes, yahoo, "last"), _quote(quotes, yahoo, "prev")
            fx = _fx(quotes, currency)
            if last is not None and fx is not None:
                price = last / div
                value = volume * price * fx
                day = volume * (last - prev) / div * fx if prev is not None else float("nan")
                live = True
            else:
                price = float(g["file_price"].iloc[-1]) if g["file_price"].notna().any() else float("nan")
                value = float(g["value_pln"].sum())
                day = float("nan")
                live = False
            profit = value - cost
            rows.append({
                "account": acc.account_type, "xtb_ticker": xtb_ticker, "yahoo": yahoo,
                "name": g["name"].iloc[0], "category": g["category"].iloc[0], "currency": currency,
                "volume": volume, "avg_price": avg_price, "price": price, "value_pln": value,
                "cost_pln": cost, "profit_pln": profit,
                "profit_pct": profit / cost if cost > 0 else float("nan"),
                "day_pln": day, "share": 0.0, "live": live,
            })
    pos = pd.DataFrame(rows, columns=POSITION_COLUMNS)
    total = float(pos["value_pln"].sum()) if not pos.empty else 0.0
    if total > 0:
        pos["share"] = pos["value_pln"] / total
    pos = pos.sort_values("value_pln", ascending=False, ignore_index=True)

    cost = float(pos["cost_pln"].sum()) if not pos.empty else 0.0
    day = float(pos["day_pln"].fillna(0.0).sum()) if not pos.empty else 0.0
    reports = [a.report_time for a in chosen if a.report_time is not None]
    summary = {
        "value": total,
        "cost": cost,
        "profit": total - cost,
        "profit_pct": (total - cost) / cost if cost > 0 else float("nan"),
        "day": day,
        "day_pct": day / (total - day) if total - day > 0 else float("nan"),
        "deposits": sum(deposits_net(a.cash_ops) for a in chosen),
        "dividends": sum(dividends_net(a.cash_ops) for a in chosen),
        "report_time": min(reports) if reports else None,
    }
    return pos, summary
