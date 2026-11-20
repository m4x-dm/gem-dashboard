"""Zapis portfela (wczytane konta XTB) w localStorage przegladarki.

Format: {"v": 1, "accounts": {"<account_id>": {...}}}. Surowy plik XLSX nie jest
zapisywany — tylko sparsowane pozycje i operacje gotowkowe. localStorage ma ~5 MB
na domene, wiec przy duzej historii operacji przycinamy ja do ostatnich 5 lat.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pandas as pd

from data.portfolio.xtb_parser import CASH_COLUMNS, LOT_COLUMNS, XtbAccount

if TYPE_CHECKING:
    from streamlit_local_storage import LocalStorage

PORTFOLIO_KEY = "gem_dashboard_portfolio_v1"
SCHEMA_VERSION = 1
MAX_BYTES = 1_500_000
KEEP_YEARS = 5


def _iso(v):
    if v is None or pd.isna(v):
        return None
    return v.isoformat() if isinstance(v, datetime) else None


def _df_to_records(df: pd.DataFrame, time_cols: tuple[str, ...]) -> list[dict]:
    out = []
    for rec in df.to_dict("records"):
        for c in time_cols:
            rec[c] = _iso(rec.get(c))
        out.append({k: (None if isinstance(v, float) and v != v else v) for k, v in rec.items()})
    return out


def _records_to_df(recs: list[dict], columns: list[str], time_cols: tuple[str, ...]) -> pd.DataFrame:
    df = pd.DataFrame(recs, columns=columns)
    for c in time_cols:
        df[c] = [datetime.fromisoformat(v) if v else None for v in df[c]]
    return df


def account_to_dict(acc: XtbAccount) -> dict:
    return {
        "account_id": acc.account_id,
        "account_type": acc.account_type,
        "report_time": _iso(acc.report_time),
        "skipped_cfd": acc.skipped_cfd,
        "lots": _df_to_records(acc.lots, ("open_time",)),
        "cash_ops": _df_to_records(acc.cash_ops, ("time",)),
    }


def account_from_dict(d: dict) -> XtbAccount:
    return XtbAccount(
        account_id=str(d["account_id"]),
        account_type=d["account_type"],
        report_time=datetime.fromisoformat(d["report_time"]) if d.get("report_time") else None,
        lots=_records_to_df(d.get("lots", []), LOT_COLUMNS, ("open_time",)),
        cash_ops=_records_to_df(d.get("cash_ops", []), CASH_COLUMNS, ("time",)),
        skipped_cfd=int(d.get("skipped_cfd", 0)),
    )


def _dump(accounts: dict[str, XtbAccount]) -> str:
    return json.dumps({"v": SCHEMA_VERSION,
                       "accounts": {k: account_to_dict(a) for k, a in accounts.items()}},
                      ensure_ascii=False, separators=(",", ":"))


def save_portfolio(ls: "LocalStorage", accounts: dict[str, XtbAccount]) -> bool:
    """Zapisuje wszystkie konta. Zwraca True, gdy historie operacji przycieto (za duzy JSON)."""
    payload = _dump(accounts)
    trimmed = False
    if len(payload.encode("utf-8")) > MAX_BYTES:
        cutoff = datetime.now() - timedelta(days=365 * KEEP_YEARS)
        for acc in accounts.values():
            ops = acc.cash_ops
            if not ops.empty:
                acc.cash_ops = ops[ops["time"].map(lambda t: t is not None and t >= cutoff)].reset_index(drop=True)
        payload = _dump(accounts)
        trimmed = True
    ls.setItem(PORTFOLIO_KEY, payload, key="pf_set")
    return trimmed


def load_portfolio(ls: "LocalStorage") -> tuple[dict[str, XtbAccount], bool]:
    """(konta, czy_dane_uszkodzone). Brak danych -> ({}, False)."""
    raw = ls.getItem(PORTFOLIO_KEY)
    if not raw:
        return {}, False
    try:
        data = json.loads(raw)
        if not isinstance(data, dict) or data.get("v") != SCHEMA_VERSION:
            return {}, True
        return {k: account_from_dict(v) for k, v in data.get("accounts", {}).items()}, False
    except (json.JSONDecodeError, TypeError, ValueError, KeyError):
        return {}, True


def clear_portfolio(ls: "LocalStorage") -> None:
    ls.setItem(PORTFOLIO_KEY, _dump({}), key="pf_set")
