import math

import pandas as pd
import pytest

from data.portfolio.valuation import deposits_net, dividends_net, value_portfolio
from data.portfolio.xtb_parser import parse_xtb_xlsx
from tests.xtb_fixtures import make_ike_xlsx, make_zwykle_xlsx

QUOTES = pd.DataFrame(
    {"last": [335.0, 610.0, 47.0, 4.0, 4.3], "prev": [330.0, 600.0, 46.0, 4.0, 4.3]},
    index=["SNT.WA", "META", "IS3N.DE", "USDPLN=X", "EURPLN=X"],
)


@pytest.fixture
def accounts():
    return [parse_xtb_xlsx(make_ike_xlsx()), parse_xtb_xlsx(make_zwykle_xlsx())]


def test_deposits_net_no_double_counting(accounts):
    ike, zwykle = accounts
    assert deposits_net(ike.cash_ops) == pytest.approx(5000.0)
    assert deposits_net(zwykle.cash_ops) == pytest.approx(400.0)   # 1500 - 1000 przelew na IKE - 100


def test_dividends_net_case_insensitive():
    ops = pd.DataFrame({"type": ["Dividend", "DIVIDENT", "Withholding tax", "Deposit"],
                        "amount_pln": [10.0, 5.0, -2.25, 999.0]})
    assert dividends_net(ops) == pytest.approx(12.75)


def test_positions_live(accounts):
    pos, summary = value_portfolio(accounts, QUOTES)
    by = pos.set_index("xtb_ticker")
    snt = by.loc["SNT.PL"]
    assert snt["volume"] == 3
    assert snt["avg_price"] == pytest.approx((2 * 300 + 340) / 3)
    assert snt["value_pln"] == pytest.approx(1005.0)
    assert snt["cost_pln"] == pytest.approx(940.0)
    assert snt["profit_pln"] == pytest.approx(65.0)
    assert snt["day_pln"] == pytest.approx(15.0)
    assert bool(snt["live"]) is True
    assert snt["yahoo"] == "SNT.WA" and snt["account"] == "IKE"
    meta = by.loc["META.US"]
    assert meta["value_pln"] == pytest.approx(0.5 * 610 * 4.0)
    assert meta["day_pln"] == pytest.approx(0.5 * 10 * 4.0)
    assert by.loc["IS3N.DE"]["value_pln"] == pytest.approx(10 * 47 * 4.3)


def test_unknown_ticker_uses_file_value(accounts):
    pos, _ = value_portfolio(accounts, QUOTES)
    abc = pos.set_index("xtb_ticker").loc["ABC.XX"]
    assert abc["value_pln"] == pytest.approx(100.0)
    assert abc["price"] == pytest.approx(100.0)
    assert bool(abc["live"]) is False
    assert math.isnan(abc["day_pln"])


def test_summary(accounts):
    pos, s = value_portfolio(accounts, QUOTES)
    assert s["value"] == pytest.approx(1005 + 1220 + 2021 + 100)
    assert s["cost"] == pytest.approx(940 + 1300 + 1957.5 + 90)
    assert s["profit"] == pytest.approx(s["value"] - s["cost"])
    assert s["profit_pct"] == pytest.approx(s["profit"] / s["cost"])
    assert s["day"] == pytest.approx(15 + 20 + 43)
    assert s["day_pct"] == pytest.approx(78 / (s["value"] - 78))
    assert s["deposits"] == pytest.approx(5400.0)
    assert s["dividends"] == pytest.approx(8.5)
    assert pos["share"].sum() == pytest.approx(1.0)
    assert list(pos["value_pln"]) == sorted(pos["value_pln"], reverse=True)


def test_account_filter(accounts):
    pos, s = value_portfolio(accounts, QUOTES, account_type="ZWYKLE")
    assert pos.empty
    assert s["value"] == 0.0 and s["deposits"] == pytest.approx(400.0)
    pos, s = value_portfolio(accounts, QUOTES, account_type="IKE")
    assert len(pos) == 4 and s["deposits"] == pytest.approx(5000.0)


def test_no_quotes_falls_back_to_file(accounts):
    pos, s = value_portfolio(accounts, pd.DataFrame(columns=["last", "prev"]))
    assert s["value"] == pytest.approx(990 + 1200 + 2001 + 100)
    assert not pos["live"].any()
    assert s["day"] == 0.0
