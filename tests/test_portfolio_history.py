"""Offline: odtworzenie historii portfela z operacji XTB i symulacja 'co gdyby' benchmarku."""
from datetime import datetime

import pandas as pd
import pytest

from data.portfolio import history as h
from data.portfolio.xtb_parser import CASH_COLUMNS, LOT_COLUMNS, XtbAccount


def _ops(rows):
    return pd.DataFrame([{"type": t, "ticker": tk, "time": pd.Timestamp(d), "amount_pln": a, "comment": c}
                         for t, tk, d, a, c in rows], columns=CASH_COLUMNS)


def _lots(rows):
    return pd.DataFrame([{"xtb_ticker": t, "name": t, "category": "STC", "volume": v, "open_price": None,
                          "open_time": None, "value_pln": 0.0, "gross_profit_pln": 0.0, "cost_pln": 0.0,
                          "file_price": None} for t, v in rows], columns=LOT_COLUMNS)


def _acc(acc_type, ops, lots=()):
    return XtbAccount(account_id=acc_type, account_type=acc_type, report_time=datetime(2026, 1, 9),
                      lots=_lots(lots), cash_ops=_ops(ops))


def _prices(**cols):
    idx = pd.bdate_range("2026-01-05", "2026-01-09")
    return pd.DataFrame({k: v for k, v in cols.items()}, index=idx)


def test_parse_trades_open_and_partial_close():
    ops = _ops([
        ("Stock purchase", "SNT.PL", "2026-01-05 10:00", -300.0, "OPEN BUY SNT.PL 3 @ 100.00"),
        ("Stock sell", "SNT.PL", "2026-01-07 10:00", 165.0, "CLOSE BUY SNT.PL 1.5/3 @ 110.00"),
        ("Stock purchase", "X.PL", "2026-01-07 10:00", -10.0, "dziwny komentarz"),
    ])
    tr, unparsed = h.parse_trades(ops)
    assert list(tr["qty"]) == [3.0, -1.5]
    assert list(tr["price"]) == [100.0, 110.0]
    assert list(tr["xtb_ticker"]) == ["SNT.PL", "SNT.PL"]
    assert unparsed == 1


def test_parse_trades_without_ticker_in_comment_and_partial_open():
    ops = _ops([
        ("Stock purchase", "SNT.PL", "2026-01-05 10:00", -200.0, "OPEN BUY 2 @ 100.00"),
        ("Stock purchase", "META.US", "2026-01-05 10:00", -100.0, "OPEN BUY 0.25/1.0000 @ 400.00"),
        ("Stock sell", "META.US", "2026-01-06 10:00", 50.0, "CLOSE BUY 0.1250/0.2500 @ 400.00"),
        ("Stock purchase", None, "2026-01-06 10:00", -1.0, "OPEN BUY 1 @ 1.00"),
    ])
    tr, unparsed = h.parse_trades(ops)
    assert list(tr["xtb_ticker"]) == ["SNT.PL", "META.US", "META.US"]
    assert list(tr["qty"]) == [2.0, 0.25, -0.125]
    assert unparsed == 1


@pytest.mark.parametrize("t,expected", [("Deposit", True), ("IKE deposit", True), ("Withdrawal", True),
                                        ("Transfer", True), ("Stock purchase", False), ("Dividend", False)])
def test_is_flow(t, expected):
    assert h.is_flow(t) is expected


def test_reconstruct_value_and_deposits():
    acc = _acc("IKE", [
        ("IKE deposit", None, "2026-01-05 09:00", 1000.0, "Transfer in"),
        ("Stock purchase", "SNT.PL", "2026-01-05 10:00", -300.0, "OPEN BUY SNT.PL 3 @ 100.00"),
        ("Stock sell", "SNT.PL", "2026-01-07 10:00", 110.0, "CLOSE BUY SNT.PL 1/3 @ 110.00"),
    ], lots=[("SNT.PL", 2.0)])
    prices = _prices(**{"SNT.WA": [100, 105, 110, 120, 130]})
    df, checks = h.reconstruct([acc], prices)
    assert df.loc["2026-01-05", "value"] == pytest.approx(700 + 300)
    assert df.loc["2026-01-06", "value"] == pytest.approx(700 + 315)
    # 07.01: gotowka 810, 2 szt. x 110
    assert df.loc["2026-01-07", "value"] == pytest.approx(810 + 220)
    assert df.loc["2026-01-09", "value"] == pytest.approx(810 + 260)
    assert (df["deposits"] == 1000).all()
    assert checks["volume_mismatch"] == []
    assert checks["unparsed"] == 0


def test_transfer_between_accounts_cancels_in_all_view():
    zw = _acc("ZWYKLE", [
        ("Deposit", None, "2026-01-05 08:00", 1000.0, "BLIK deposit"),
        ("IKE deposit", None, "2026-01-06 08:00", -400.0, "Transfer out"),
    ])
    ike = _acc("IKE", [("IKE deposit", None, "2026-01-06 08:00", 400.0, "Transfer in")])
    prices = _prices(**{"USDPLN=X": [4.0] * 5})
    all_df, _ = h.reconstruct([zw, ike], prices)
    assert all_df.loc["2026-01-09", "deposits"] == pytest.approx(1000)
    assert all_df.loc["2026-01-09", "value"] == pytest.approx(1000)
    ike_df, _ = h.reconstruct([zw, ike], prices, account_type="IKE")
    assert ike_df.loc["2026-01-09", "deposits"] == pytest.approx(400)
    assert ike_df.index[0] == pd.Timestamp("2026-01-06")


def test_withdrawal_reduces_deposits():
    acc = _acc("ZWYKLE", [
        ("Deposit", None, "2026-01-05 08:00", 1000.0, ""),
        ("Withdrawal", None, "2026-01-08 08:00", -300.0, ""),
    ])
    df, _ = h.reconstruct([acc], _prices(x=[1] * 5))
    assert df.loc["2026-01-08", "deposits"] == pytest.approx(700)
    assert df.loc["2026-01-08", "value"] == pytest.approx(700)


def test_usd_stock_uses_fx_and_missing_ticker_uses_trade_price():
    acc = _acc("IKE", [
        ("IKE deposit", None, "2026-01-05 08:00", 2000.0, ""),
        ("Stock purchase", "META.US", "2026-01-05 10:00", -800.0, "OPEN BUY META.US 2 @ 100.00"),
        ("Stock purchase", "GONE.US", "2026-01-05 10:00", -400.0, "OPEN BUY GONE.US 1 @ 100.00"),
    ], lots=[("META.US", 2.0), ("GONE.US", 1.0)])
    prices = _prices(**{"META": [100, 110, 110, 110, 110], "USDPLN=X": [4.0] * 5})
    df, _ = h.reconstruct([acc], prices)
    # gotowka 800 + META 2*110*4 + GONE z transakcji 400 zl
    assert df.loc["2026-01-06", "value"] == pytest.approx(800 + 880 + 400)


def test_insane_yahoo_price_falls_back_to_trade_value():
    acc = _acc("IKE", [
        ("IKE deposit", None, "2026-01-05 08:00", 1000.0, ""),
        ("Stock purchase", "CNDX.UK", "2026-01-05 10:00", -400.0, "OPEN BUY CNDX.UK 1 @ 100.00"),
    ], lots=[("CNDX.UK", 1.0)])
    # Yahoo w pensach /100 = 9 zamiast 100 -> rozjazd >50% -> wycena z transakcji
    prices = _prices(**{"CNDX.L": [900] * 5, "GBPPLN=X": [5.0] * 5})
    df, _ = h.reconstruct([acc], prices)
    assert df.loc["2026-01-09", "value"] == pytest.approx(600 + 400)


def test_volume_mismatch_reported():
    acc = _acc("IKE", [
        ("Stock purchase", "SNT.PL", "2026-01-05 10:00", -100.0, "OPEN BUY SNT.PL 1 @ 100.00"),
    ], lots=[("SNT.PL", 3.0)])
    _, checks = h.reconstruct([acc], _prices(**{"SNT.WA": [100] * 5}))
    assert checks["volume_mismatch"] == ["SNT.PL"]


def test_reconstruct_empty_accounts():
    df, checks = h.reconstruct([_acc("IKE", [])], _prices(x=[1] * 5))
    assert df.empty
    assert checks["volume_mismatch"] == []


def test_whatif_buys_and_sells_units():
    idx = pd.bdate_range("2026-01-05", "2026-01-09")
    bench = pd.Series([100, 100, 200, 200, 200], index=idx, dtype=float)
    flows = pd.Series({pd.Timestamp("2026-01-05"): 1000.0, pd.Timestamp("2026-01-07"): 1000.0,
                       pd.Timestamp("2026-01-08"): -400.0})
    out = h.whatif(flows, bench, idx)
    assert out.loc["2026-01-06"] == pytest.approx(1000)
    assert out.loc["2026-01-07"] == pytest.approx(3000)   # 10 j. x 200 + 5 j. x 200
    assert out.loc["2026-01-09"] == pytest.approx(2600)


def test_whatif_flow_on_non_session_day_uses_next_close():
    idx = pd.bdate_range("2026-01-05", "2026-01-09")
    bench = pd.Series([100, None, 200, 200, 200], index=idx, dtype=float)
    out = h.whatif(pd.Series({pd.Timestamp("2026-01-06"): 1000.0}), bench, idx)
    assert out.loc["2026-01-07"] == pytest.approx(1000)


def test_benchmark_prices_pln_converts_usd():
    idx = pd.bdate_range("2026-01-05", "2026-01-06")
    prices = pd.DataFrame({"SPY": [500.0, 510.0], "QQQ": [400.0, 400.0], "USDPLN=X": [4.0, 4.0],
                           "ETFBW20TR.WA": [80.0, 81.0]}, index=idx)
    b = h.benchmark_prices_pln(prices)
    assert b["S&P 500"].iloc[1] == pytest.approx(2040)
    assert b["WIG20"].iloc[0] == pytest.approx(80)
    assert "mWIG40" not in b.columns


def test_history_tickers_include_closed_positions_fx_and_benchmarks():
    acc = _acc("IKE", [
        ("Stock purchase", "META.US", "2026-01-05 10:00", -800.0, "OPEN BUY META.US 2 @ 100.00"),
        ("Stock sell", "META.US", "2026-01-06 10:00", 800.0, "CLOSE BUY META.US 2/2 @ 100.00"),
    ])
    t = h.history_tickers([acc])
    assert {"META", "USDPLN=X", "SPY", "QQQ", "ETFBW20TR.WA", "ETFBM40TR.WA"} <= t
