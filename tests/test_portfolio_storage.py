import json
from datetime import datetime, timedelta

import pandas as pd
import pytest

from components import portfolio_storage as ps
from data.portfolio.xtb_parser import parse_xtb_xlsx
from tests.xtb_fixtures import make_ike_xlsx, make_zwykle_xlsx


class DictLS:
    """Atrapa streamlit_local_storage.LocalStorage (getItem/setItem)."""

    def __init__(self, items=None):
        self.items = dict(items or {})

    def getItem(self, itemKey):
        return self.items.get(itemKey)

    def setItem(self, itemKey=None, itemValue=None, key=None):
        self.items[itemKey] = itemValue


def test_roundtrip():
    ls = DictLS()
    ike = parse_xtb_xlsx(make_ike_xlsx())
    zw = parse_xtb_xlsx(make_zwykle_xlsx())
    accounts = {ike.account_id: ike, zw.account_id: zw}
    assert ps.save_portfolio(ls, accounts) is False          # nie przycinano
    loaded, corrupt = ps.load_portfolio(ls)
    assert corrupt is False
    assert set(loaded) == {"11111111", "22222222"}
    a = loaded["11111111"]
    assert a.account_type == "IKE" and a.report_time == ike.report_time and a.skipped_cfd == 0
    pd.testing.assert_frame_equal(a.lots, ike.lots, check_dtype=False)
    pd.testing.assert_frame_equal(a.cash_ops, ike.cash_ops, check_dtype=False)
    assert loaded["22222222"].lots.empty and loaded["22222222"].skipped_cfd == 2


def test_stored_json_shape():
    ls = DictLS()
    ike = parse_xtb_xlsx(make_ike_xlsx())
    ps.save_portfolio(ls, {ike.account_id: ike})
    data = json.loads(ls.items[ps.PORTFOLIO_KEY])
    assert data["v"] == 1 and list(data["accounts"]) == ["11111111"]


def test_empty_and_corrupt():
    assert ps.load_portfolio(DictLS()) == ({}, False)
    assert ps.load_portfolio(DictLS({ps.PORTFOLIO_KEY: "{nie json"})) == ({}, True)
    assert ps.load_portfolio(DictLS({ps.PORTFOLIO_KEY: json.dumps({"v": 99})})) == ({}, True)


def test_clear():
    ls = DictLS()
    ike = parse_xtb_xlsx(make_ike_xlsx())
    ps.save_portfolio(ls, {ike.account_id: ike})
    ps.clear_portfolio(ls)
    assert ps.load_portfolio(ls) == ({}, False)


def test_large_cash_history_trimmed(monkeypatch):
    monkeypatch.setattr(ps, "MAX_BYTES", 2000)
    ike = parse_xtb_xlsx(make_ike_xlsx())
    old = datetime(2015, 1, 1)
    ike.cash_ops = pd.DataFrame([{"type": "Deposit", "ticker": None, "time": old + timedelta(days=i),
                                  "amount_pln": 1.0, "comment": "x" * 50} for i in range(200)]
                                + ike.cash_ops.to_dict("records"))
    ls = DictLS()
    assert ps.save_portfolio(ls, {ike.account_id: ike}) is True
    loaded, _ = ps.load_portfolio(ls)
    assert loaded["11111111"].cash_ops["time"].min() >= datetime(2021, 1, 1)


def test_missing_time_roundtrips_as_null():
    ls = DictLS()
    ike = parse_xtb_xlsx(make_ike_xlsx())
    ike.lots.loc[0, "open_time"] = pd.NaT
    ps.save_portfolio(ls, {ike.account_id: ike})
    assert json.loads(ls.items[ps.PORTFOLIO_KEY])["accounts"]["11111111"]["lots"][0]["open_time"] is None
    loaded, corrupt = ps.load_portfolio(ls)
    assert corrupt is False and pd.isna(loaded["11111111"].lots.loc[0, "open_time"])
