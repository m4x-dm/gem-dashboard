from datetime import datetime

import pytest

from data.portfolio.xtb_parser import XtbFormatError, parse_xtb_xlsx
from tests.xtb_fixtures import make_ike_xlsx, make_not_xtb_xlsx, make_zwykle_xlsx


def test_ike_lots():
    acc = parse_xtb_xlsx(make_ike_xlsx(), "IKE_11111111_2006-01-01_2026-11-08.xlsx")
    lots = acc.lots
    assert len(lots) == 5
    assert list(lots["xtb_ticker"]) == ["SNT.PL", "SNT.PL", "META.US", "IS3N.DE", "ABC.XX"]
    snt = lots[lots["xtb_ticker"] == "SNT.PL"]
    assert list(snt["name"]) == ["Synektik", "Synektik"]  # nazwa z wiersza zbiorczego
    assert list(snt["category"]) == ["STOCK", "STOCK"]
    assert list(snt["volume"]) == [2.0, 1.0]
    assert list(snt["open_price"]) == [300.0, 340.0]
    assert list(snt["cost_pln"]) == [600.0, 340.0]       # Value - Gross Profit
    assert list(snt["file_price"]) == [330.0, 330.0]
    assert lots.iloc[0]["open_time"] == datetime(2026, 6, 17, 12, 0)
    assert lots[lots["xtb_ticker"] == "IS3N.DE"].iloc[0]["category"] == "ETF"


def test_ike_metadata():
    acc = parse_xtb_xlsx(make_ike_xlsx())
    assert acc.account_id == "11111111"     # z Cash Operations, nie z Open Positions
    assert acc.account_type == "IKE"
    assert acc.report_time == datetime(2026, 11, 8, 12, 0)
    assert acc.skipped_cfd == 0


def test_cfd_skipped_on_regular_account():
    acc = parse_xtb_xlsx(make_zwykle_xlsx())
    assert acc.account_type == "ZWYKLE"
    assert acc.account_id == "22222222"
    assert acc.lots.empty
    assert acc.skipped_cfd == 1


def test_not_xtb_file_raises():
    with pytest.raises(XtbFormatError, match="Open Positions"):
        parse_xtb_xlsx(make_not_xtb_xlsx())


def test_garbage_bytes_raise():
    with pytest.raises(XtbFormatError, match="XLSX"):
        parse_xtb_xlsx(b"to nie jest plik excela")


from tests.xtb_fixtures import _book  # noqa: E402


def test_cash_operations_parsed():
    acc = parse_xtb_xlsx(make_ike_xlsx())
    ops = acc.cash_ops
    assert len(ops) == 6
    assert list(ops["type"]) == ["IKE deposit", "IKE deposit", "Stock purchase", "Dividend",
                                 "Withholding tax", "Free funds interest"]
    assert ops["amount_pln"].sum() == pytest.approx(1000 + 4000 - 1300 + 10 - 1.5 + 0.12)
    assert ops.iloc[3]["ticker"] == "META.US"
    assert isinstance(ops.iloc[0]["time"], datetime)


def test_regular_account_cash():
    ops = parse_xtb_xlsx(make_zwykle_xlsx()).cash_ops
    assert list(ops["amount_pln"]) == [1500.0, -1000.0, -100.0]


def test_account_type_from_filename_when_no_product():
    """Konto bez operacji i bez pozycji: typ z prefiksu nazwy pliku."""
    data = _book("33333333", "33333333", None, [], [])
    assert parse_xtb_xlsx(data, "IKZE_33333333_2006-01-01_2026-11-08.xlsx").account_type == "IKZE"
    assert parse_xtb_xlsx(data, "PLN_33333333_x.xlsx").account_type == "ZWYKLE"
    assert parse_xtb_xlsx(data, None).account_type == "ZWYKLE"


def test_zip_rejected_with_hint():
    with pytest.raises(XtbFormatError, match="ZIP"):
        parse_xtb_xlsx(b"PK\x03\x04", "53853640_2006-01-01_2026-11-08.zip")


def test_missing_cash_column_raises():
    from openpyxl import Workbook
    import io
    wb = Workbook()
    wb.active.title = "Open Positions"
    wb.active.append(["Product", "Instrument/Position", "Ticker", "Category", "Type", "Volume", "Value",
                      "Current price", "Open price", "Open time (UTC)", "Gross Profit"])
    cash = wb.create_sheet("Cash Operations")
    cash.append(["Account number", "1"])
    cash.append(["Type", "Ticker", "Time"])          # brak Amount i Comment
    buf = io.BytesIO()
    wb.save(buf)
    with pytest.raises(XtbFormatError, match="Amount"):
        parse_xtb_xlsx(buf.getvalue())
