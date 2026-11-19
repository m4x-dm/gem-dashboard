"""Syntetyczne eksporty XTB (XLSX) do testow — struktura 1:1 z prawdziwym eksportem,
liczby i numery kont zmyslone. Generowane w pamieci, zadnych plikow binarnych w repo."""
from __future__ import annotations

import io

from openpyxl import Workbook

OPEN_HEADER = ["Product", "Instrument/Position", "Ticker", "Category", "Type", "Volume", "Value",
               "Current price", "Open price", "Open time (UTC)", "Stop Loss", "Take Profit",
               "Net Profit %", "Net Profit", "Gross Profit", "Margin", "Open Commission", "Swap",
               "Rollover"]
CASH_HEADER = ["Type", "Instrument", "Ticker", "Category", "Time", "Amount", "ID", "Comment",
               "Product", "Position ID"]
CLOSED_HEADER = ["Instrument", "Ticker", "Category", "Type", "Volume", "Open Price",
                 "Open Time (UTC)", "Close Price", "Close Time (UTC)", "Product", "Profit/Loss"]

REPORT_SERIAL = 46334.5  # 2026-11-08 12:00 UTC


def _agg(product, name, ticker, category, volume, value):
    """Wiersz zbiorczy spolki (Category wypelnione, Type puste)."""
    return [product, name, ticker, category, None, volume, value]


def _lot(product, pos_id, ticker, volume, value, current, open_price, open_serial, gross):
    """Wiersz pojedynczego zakupu (Type=BUY, Category puste)."""
    return [product, pos_id, ticker, None, "BUY", volume, value, current, open_price, open_serial,
            None, None, None, gross, gross]


def _book(account_id: str, main_account_id: str, product: str, open_rows: list, cash_rows: list) -> bytes:
    wb = Workbook()
    closed = wb.active
    closed.title = "Closed Positions"
    closed.append(["Account number", account_id])
    closed.append(["Closed Positions"])
    closed.append(["Date from (UTC)", 38718.0])
    closed.append(["Date to (UTC)", 46334.43])
    closed.append(CLOSED_HEADER)

    cash = wb.create_sheet("Cash Operations")
    cash.append(["Account number", account_id])
    cash.append(["Cash Operations"])
    cash.append(["Date from (UTC)", 38718.0])
    cash.append(["Date to (UTC)", 46334.43])
    cash.append(CASH_HEADER)
    for r in cash_rows:
        cash.append(r)

    op = wb.create_sheet("Open Positions")
    op.append(["Account number", main_account_id])  # XTB wpisuje tu numer konta glownego
    op.append(["Open Positions"])
    op.append(["Data as of report generated", REPORT_SERIAL])
    op.append(["Product", "Metric", "Amount", "Currency"])
    op.append([product, "Open position value", 0.0])
    op.append([product, "Open position profit", 0.0])
    op.append([])
    op.append(["Note", "Summary values and open positions are shown as of the report generation time"])
    op.append(OPEN_HEADER)
    for r in open_rows:
        op.append(r)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def make_ike_xlsx() -> bytes:
    """Konto IKE 11111111: SNT.PL (2 zakupy), META.US, IS3N.DE (ETF), ABC.XX (nieznana gielda)."""
    p = "IKE"
    open_rows = [
        _agg(p, "Synektik", "SNT.PL", "STOCK", 3, 990.0),
        _lot(p, "1001", "SNT.PL", 2, 660.0, 330.0, 300.0, 46190.5, 60.0),
        _lot(p, "1002", "SNT.PL", 1, 330.0, 330.0, 340.0, 46300.5, -10.0),
        _agg(p, "Meta", "META.US", "STOCK", 0.5, 1200.0),
        _lot(p, "1003", "META.US", 0.5, 1200.0, 600.0, 650.0, 46315.5, -100.0),
        _agg(p, "Core MSCI EM IMI", "IS3N.DE", "ETF", 10, 2001.0),
        _lot(p, "1004", "IS3N.DE", 10, 2001.0, 46.0, 45.0, 46250.5, 43.5),
        _agg(p, "Abc Corp", "ABC.XX", "STOCK", 1, 100.0),
        _lot(p, "1005", "ABC.XX", 1, 100.0, 100.0, 90.0, 46260.5, 10.0),
    ]
    cash_rows = [
        ["IKE deposit", None, None, None, 46300.1, 1000.0, 1, "Transfer in operation", p, None],
        ["IKE deposit", None, None, None, 46310.1, 4000.0, 2, "Transfer in operation", p, None],
        ["Stock purchase", "Meta", "META.US", "STOCK", 46315.5, -1300.0, 3,
         "OPEN BUY META.US 0.5 @ 650.00", p, 1003],
        ["Dividend", "Meta", "META.US", "STOCK", 46320.5, 10.0, 4, "META.US USD 0.5250/ SHR", p, None],
        ["Withholding tax", "Meta", "META.US", "STOCK", 46320.5, -1.5, 5, "META.US USD WHT 15%", p, None],
        ["Free funds interest", None, None, None, 46329.7, 0.12, 6, "Free-funds Interest 2026-10", p, None],
    ]
    return _book("11111111", "99999999", p, open_rows, cash_rows)


def make_zwykle_xlsx() -> bytes:
    """Konto zwykle 22222222 (Product = My Trades): tylko otwarty CFD + wplaty/przelew na IKE."""
    p = "My Trades"
    open_rows = [
        _agg(p, "OIL.WTI", "OIL.WTI", "CFD", 0.01, 350.0),
        _lot(p, "2001", "OIL.WTI", 0.01, 350.0, 88.0, 87.0, 46330.5, 5.0),
    ]
    cash_rows = [
        ["Deposit", None, None, None, 46299.1, 1500.0, 10, "BLIK deposit", p, None],
        ["IKE deposit", None, None, None, 46300.1, -1000.0, 11, "Transfer out operation", p, None],
        ["Withdrawal", None, None, None, 46305.1, -100.0, 12, "Withdrawal to bank", p, None],
    ]
    return _book("22222222", "22222222", p, open_rows, cash_rows)


def make_not_xtb_xlsx() -> bytes:
    """Poprawny XLSX, ale nie eksport XTB."""
    wb = Workbook()
    wb.active.title = "Sheet1"
    wb.active.append(["a", "b"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def with_bogus_dimension(xlsx: bytes) -> bytes:
    """XTB exports declare dimension A1 in every sheet, which breaks openpyxl read_only mode."""
    import io
    import re
    import zipfile

    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(xlsx)) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            raw = zin.read(item.filename)
            if re.match(r"xl/worksheets/[^/]+\.xml$", item.filename):
                text = raw.decode("utf-8")
                text = re.sub(r'<dimension ref="[^"]*"\s*/>', '<dimension ref="A1"/>', text)
                raw = text.encode("utf-8")
            zout.writestr(item, raw)
    return out.getvalue()
