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
