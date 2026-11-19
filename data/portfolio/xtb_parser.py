"""Parser eksportu historii konta XTB (xStation -> Historia -> Eksport, plik XLSX).

Jeden plik = jedno konto (zwykle / IKE / IKZE). Pozycje bierzemy z arkusza
'Open Positions' (stan na moment wygenerowania raportu), wplaty i dywidendy
z 'Cash Operations'. Kolumny szukamy po nazwie naglowka, nie po indeksie.
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd

LOT_COLUMNS = ["xtb_ticker", "name", "category", "volume", "open_price", "open_time",
               "value_pln", "gross_profit_pln", "cost_pln", "file_price"]
CASH_COLUMNS = ["type", "ticker", "time", "amount_pln", "comment"]
_EXCEL_EPOCH = datetime(1899, 12, 30)
_PRODUCT_TO_TYPE = {"IKE": "IKE", "IKZE": "IKZE"}


class XtbFormatError(ValueError):
    """Plik nie wyglada na eksport XTB (komunikat po polsku, do pokazania uzytkownikowi)."""


@dataclass
class XtbAccount:
    account_id: str
    account_type: str            # "IKE" | "IKZE" | "ZWYKLE"
    report_time: datetime | None
    lots: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=LOT_COLUMNS))
    cash_ops: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=CASH_COLUMNS))
    skipped_cfd: int = 0


def excel_to_datetime(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    try:
        dt = _EXCEL_EPOCH + timedelta(days=float(value))
    except (TypeError, ValueError):
        return None
    return dt.replace(microsecond=0)


def _num(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _rows(ws) -> list[tuple]:
    return [tuple(r) for r in ws.iter_rows(values_only=True)]


def _find_header(rows: list[tuple], first_cell: str, sheet: str) -> int:
    for i, r in enumerate(rows):
        if r and r[0] == first_cell:
            return i
    raise XtbFormatError(f"Arkusz '{sheet}' nie ma naglowka zaczynajacego sie od '{first_cell}'.")


def _records(rows: list[tuple], header_idx: int, required: list[str], sheet: str) -> list[dict]:
    header = [str(c).strip() if c is not None else "" for c in rows[header_idx]]
    missing = [c for c in required if c not in header]
    if missing:
        raise XtbFormatError(f"Arkusz '{sheet}': brak kolumn {', '.join(missing)}.")
    out = []
    for r in rows[header_idx + 1:]:
        if not r or all(c is None or c == "" for c in r):
            continue
        out.append({h: (r[i] if i < len(r) else None) for i, h in enumerate(header) if h})
    return out


def _account_type(product: str | None) -> str | None:
    if not product:
        return None
    return _PRODUCT_TO_TYPE.get(str(product).strip().upper(), "ZWYKLE")


def _type_from_filename(filename: str | None) -> str | None:
    if not filename:
        return None
    prefix = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].split("_", 1)[0].upper()
    return {"IKE": "IKE", "IKZE": "IKZE", "PLN": "ZWYKLE"}.get(prefix)


def _parse_open_positions(rows: list[tuple]) -> tuple[pd.DataFrame, int, str | None, datetime | None]:
    report_time = None
    for r in rows[:8]:
        if r and r[0] == "Data as of report generated":
            report_time = excel_to_datetime(r[1] if len(r) > 1 else None)
    hdr = _find_header(rows, "Product", "Open Positions")
    # pierwszy 'Product' to tabela podsumowania (Product, Metric, Amount...) — szukamy tej z 'Ticker'
    while "Ticker" not in rows[hdr]:
        nxt = _find_header(rows[hdr + 1:], "Product", "Open Positions")
        hdr = hdr + 1 + nxt
    recs = _records(rows, hdr, ["Instrument/Position", "Ticker", "Category", "Type", "Volume",
                                "Value", "Current price", "Open price", "Open time (UTC)",
                                "Gross Profit"], "Open Positions")
    lots, skipped, product = [], 0, None
    agg_name, agg_category = None, None
    for rec in recs:
        product = product or rec.get("Product")
        if rec.get("Category") and not rec.get("Type"):     # wiersz zbiorczy spolki
            agg_name, agg_category = rec.get("Instrument/Position"), rec.get("Category")
            continue
        if str(rec.get("Type") or "").upper() != "BUY":
            continue
        category = rec.get("Category") or agg_category
        if str(category or "").upper() == "CFD":
            skipped += 1
            continue
        value = _num(rec.get("Value")) or 0.0
        gross = _num(rec.get("Gross Profit")) or 0.0
        lots.append({
            "xtb_ticker": str(rec.get("Ticker") or "").strip(),
            "name": agg_name or rec.get("Ticker"),
            "category": category,
            "volume": _num(rec.get("Volume")) or 0.0,
            "open_price": _num(rec.get("Open price")),
            "open_time": excel_to_datetime(rec.get("Open time (UTC)")),
            "value_pln": value,
            "gross_profit_pln": gross,
            "cost_pln": value - gross,
            "file_price": _num(rec.get("Current price")),
        })
    return pd.DataFrame(lots, columns=LOT_COLUMNS), skipped, product, report_time


def _parse_cash(rows: list[tuple]) -> tuple[pd.DataFrame, str | None, str | None]:
    account_id = None
    if rows and rows[0] and rows[0][0] == "Account number" and len(rows[0]) > 1:
        raw = rows[0][1]
        account_id = str(int(float(raw))) if _num(raw) is not None else str(raw)
    hdr = _find_header(rows, "Type", "Cash Operations")
    recs = _records(rows, hdr, ["Type", "Ticker", "Time", "Amount", "Comment"], "Cash Operations")
    product = next((r.get("Product") for r in recs if r.get("Product")), None)
    ops = [{
        "type": str(r.get("Type") or "").strip(),
        "ticker": r.get("Ticker"),
        "time": excel_to_datetime(r.get("Time")),
        "amount_pln": _num(r.get("Amount")) or 0.0,
        "comment": r.get("Comment"),
    } for r in recs]
    return pd.DataFrame(ops, columns=CASH_COLUMNS), account_id, product


def parse_xtb_xlsx(data: bytes, filename: str | None = None) -> XtbAccount:
    """Bajty pliku XLSX z XTB -> XtbAccount. XtbFormatError gdy to nie eksport XTB."""
    if filename and filename.lower().endswith(".zip"):
        raise XtbFormatError("To jest archiwum ZIP — rozpakuj je i wczytaj pliki .xlsx ze srodka.")
    try:
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except (zipfile.BadZipFile, KeyError, OSError, ValueError) as exc:
        raise XtbFormatError("Nie udalo sie otworzyc pliku — oczekiwany plik XLSX z XTB.") from exc
    for sheet in ("Open Positions", "Cash Operations"):
        if sheet not in wb.sheetnames:
            raise XtbFormatError(f"Brak arkusza '{sheet}' — to nie wyglada na eksport z XTB.")
    lots, skipped, open_product, report_time = _parse_open_positions(_rows(wb["Open Positions"]))
    cash, account_id, cash_product = _parse_cash(_rows(wb["Cash Operations"]))
    wb.close()
    account_type = (_account_type(cash_product) or _account_type(open_product)
                    or _type_from_filename(filename) or "ZWYKLE")
    if not account_id:
        raise XtbFormatError("Brak numeru konta w arkuszu 'Cash Operations'.")
    return XtbAccount(account_id=account_id, account_type=account_type, report_time=report_time,
                      lots=lots, cash_ops=cash, skipped_cfd=skipped)
