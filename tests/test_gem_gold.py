"""Testy strategii Gold Momentum (strona 25, regula z inwestomat.eu).

Regula: (1) najwyzsze 12M z S&P 500 / zloto / bony 3M wybiera galaz,
(2) w galezi akcji najlepszy z SPY/VEA/EEM (VEA jak w GEM, przed 2007 zwroty EFA), w galezi obligacji lepsze
z bonow 3M / obligacji 7-10Y, w galezi zlota zloto.
"""

import numpy as np
import pandas as pd
import pytest

from data.momentum import (
    annual_returns,
    backtest_gold_momentum,
    gold_momentum_now,
    gold_momentum_pick,
    gold_momentum_sensitivity,
    splice_proxy,
    signal_time_share,
    tbill_index,
)


def _prices(drifts: dict[str, float], n: int = 1300, seed: int | None = None) -> tuple[pd.DataFrame, pd.Series]:
    idx = pd.bdate_range("2010-01-01", periods=n)
    rng = np.random.default_rng(seed) if seed is not None else None
    data = {}
    for t, mu in drifts.items():
        r = np.full(n, mu) if rng is None else rng.normal(mu, 0.01, n)
        data[t] = 100 * np.cumprod(1 + r)
    irx = pd.Series(2.0, index=idx)  # 2% rocznie
    return pd.DataFrame(data, index=idx), tbill_index(irx)


BASE = {"SPY": 0.0004, "VEA": 0.0002, "EEM": 0.0001, "GLD": 0.0001, "IEF": 0.00005}


class TestPick:
    def test_galaz_akcji_wybiera_najlepszy_indeks(self):
        mom = {"SPY": 0.10, "VEA": 0.15, "EEM": 0.05, "GLD": 0.02, "TBILL": 0.03, "IEF": 0.01}
        assert gold_momentum_pick(mom) == ("Akcje", "VEA")

    def test_vea_nie_decyduje_o_galezi(self):
        # VEA najsilniejsze, ale galaz wybiera tylko SPY vs zloto vs bony
        mom = {"SPY": 0.01, "VEA": 0.30, "EEM": 0.20, "GLD": 0.05, "TBILL": 0.02, "IEF": 0.0}
        assert gold_momentum_pick(mom) == ("Zloto", "GLD")

    def test_galaz_obligacji(self):
        mom = {"SPY": -0.1, "VEA": -0.1, "EEM": -0.2, "GLD": -0.05, "TBILL": 0.03, "IEF": 0.06}
        assert gold_momentum_pick(mom) == ("Obligacje", "IEF")
        mom["IEF"] = 0.01
        assert gold_momentum_pick(mom) == ("Obligacje", "TBILL")

    def test_inny_ticker_zlota(self):
        mom = {"SPY": 0.0, "VEA": 0, "EEM": 0, "IAU": 0.2, "TBILL": 0.01, "IEF": 0}
        assert gold_momentum_pick(mom, gold="IAU") == ("Zloto", "IAU")


    def test_qqq_zamiast_spy(self):
        mom = {"SPY": 0.50, "QQQ": 0.10, "VEA": 0.05, "EEM": 0.0, "GLD": 0.08, "TBILL": 0.02, "IEF": 0}
        # SPY ignorowany, gdy galaz akcji reprezentuje QQQ
        assert gold_momentum_pick(mom, us="QQQ") == ("Akcje", "QQQ")
        mom["GLD"] = 0.12
        assert gold_momentum_pick(mom, us="QQQ") == ("Zloto", "GLD")

    def test_backtest_qqq_ma_benchmark_qqq(self):
        prices, tb = _prices({**BASE, "QQQ": 0.0008})
        res = backtest_gold_momentum(prices, tb, us="QQQ")
        assert "QQQ B&H" in res["equity"] and "SPY B&H" not in res["equity"]
        assert res["signals"][-1][1] == "QQQ"
        assert gold_momentum_now(prices, tb, us="QQQ")["asset"] == "QQQ"


class TestTbill:
    def test_indeks_rosnie_o_rentownosc(self):
        idx = pd.bdate_range("2020-01-01", periods=253)
        tb = tbill_index(pd.Series(5.0, index=idx))
        assert tb.iloc[-1] / tb.iloc[0] - 1 == pytest.approx((1 + 0.05 / 252) ** 252 - 1, rel=1e-6)


class TestBacktest:
    def test_trend_zlota_trzyma_zloto(self):
        prices, tb = _prices({**BASE, "GLD": 0.0010})
        res = backtest_gold_momentum(prices, tb)
        assert res["signals"] == [(res["signals"][0][0], "GLD")]
        gld = res["equity"]["GLD B&H"]
        gm = res["equity"]["GEM Gold Momentum"]
        # trzyma zloto od 2. miesiaca — zwroty miesieczne identyczne
        np.testing.assert_allclose(gm.pct_change().iloc[1:], gld.pct_change().iloc[1:], rtol=1e-9)

    def test_bessa_ucieka_w_obligacje(self):
        prices, tb = _prices({"SPY": -0.0005, "VEA": -0.0005, "EEM": -0.0006,
                              "GLD": -0.0003, "IEF": 0.0002})
        res = backtest_gold_momentum(prices, tb)
        assert res["signals"][-1][1] == "IEF"
        assert set(res["branches"]) == {"Obligacje"}

    def test_brak_lookaheadu(self):
        prices, tb = _prices(BASE, seed=3)
        base = backtest_gold_momentum(prices, tb)
        bumped = prices.copy()
        bumped.iloc[-30:] *= 3.0
        res = backtest_gold_momentum(bumped, tb)
        n = len(base["equity"]["GEM Gold Momentum"])
        # ostatnie ~30 sesji to ostatni (czesciowo przedostatni) miesiac: wczesniejsza krzywa bez zmian
        pd.testing.assert_series_equal(res["equity"]["GEM Gold Momentum"].iloc[: n - 3],
                                       base["equity"]["GEM Gold Momentum"].iloc[: n - 3])

    def test_koszt_i_belka_obnizaja_wynik_tylko_przy_zmianach(self):
        prices, tb = _prices(BASE, seed=5)
        a = backtest_gold_momentum(prices, tb)
        b = backtest_gold_momentum(prices, tb, transaction_cost=0.003, tax_belka=0.19)
        if len(a["signals"]) > 1:
            assert b["equity"]["GEM Gold Momentum"].iloc[-1] < a["equity"]["GEM Gold Momentum"].iloc[-1]
        assert b["signals"] == a["signals"]

    def test_wszystkie_krzywe_na_tych_samych_datach(self):
        prices, tb = _prices(BASE, seed=1)
        res = backtest_gold_momentum(prices, tb, start_capital=1000)
        idx = res["equity"]["GEM Gold Momentum"].index
        assert set(res["equity"]) == {"GEM Gold Momentum", "SPY B&H", "GLD B&H", "VEA B&H", "EEM B&H"}
        for s in res["equity"].values():
            assert s.index.equals(idx)
            assert s.iloc[0] == pytest.approx(1000)

    def test_za_malo_danych_lub_brak_tickera(self):
        prices, tb = _prices(BASE, n=200)
        assert backtest_gold_momentum(prices, tb) is None
        prices, tb = _prices(BASE)
        assert backtest_gold_momentum(prices.drop(columns=["EEM"]), tb) is None


class TestNowISensitivity:
    def test_sygnal_teraz(self):
        prices, tb = _prices({**BASE, "GLD": 0.0010})
        out = gold_momentum_now(prices, tb)
        assert (out["branch"], out["asset"]) == ("Zloto", "GLD")
        assert out["returns"]["GLD"] > out["returns"]["SPY"]

    def test_wrazliwosc_wspolny_okres(self):
        prices, tb = _prices(BASE, seed=9)
        df = gold_momentum_sensitivity(prices, tb, windows=[3, 6, 12])
        assert list(df.index) == [3, 6, 12]
        assert {"CAGR", "Max Drawdown", "Sharpe", "Zmiany"} <= set(df.columns)


class TestHelpers:
    def test_annual_returns(self):
        idx = pd.to_datetime(["2020-01-02", "2020-12-31", "2021-06-30", "2021-12-31"])
        eq = pd.Series([100.0, 110.0, 99.0, 121.0], index=idx)
        out = annual_returns({"A": eq})
        assert out.loc[2020, "A"] == pytest.approx(0.10)
        assert out.loc[2021, "A"] == pytest.approx(0.10)

    def test_signal_time_share_sumuje_sie_do_jedynki(self):
        idx = pd.bdate_range("2020-01-01", periods=100)
        log = [(idx[0], "QQQ"), (idx[40], "GLD"), (idx[70], "QQQ")]
        share = signal_time_share(log, idx)
        assert share.sum() == pytest.approx(1.0)
        assert share["QQQ"] == pytest.approx(70 / 100)
        assert share["GLD"] == pytest.approx(30 / 100)


class TestVeaIOkno252:
    def test_splice_proxy_dokleja_historie_sprzed_debiutu(self):
        idx = pd.bdate_range("2006-01-02", periods=10)
        efa = pd.Series(np.linspace(100, 109, 10), index=idx)
        vea = pd.Series([np.nan] * 4 + [50.0, 51, 52, 53, 54, 55], index=idx)
        out = splice_proxy(pd.DataFrame({"VEA": vea, "EFA": efa}), "VEA", "EFA")
        # od debiutu bez zmian
        pd.testing.assert_series_equal(out["VEA"].iloc[4:], vea.iloc[4:], check_names=False)
        # przed debiutem zwroty EFA 1:1, styk w dniu debiutu
        np.testing.assert_allclose(out["VEA"].iloc[:5].pct_change().iloc[1:],
                                   efa.iloc[:5].pct_change().iloc[1:], rtol=1e-12)
        assert out["VEA"].isna().sum() == 0

    def test_splice_bez_proxy_lub_bez_primary(self):
        idx = pd.bdate_range("2006-01-02", periods=3)
        df = pd.DataFrame({"VEA": [1.0, 2.0, 3.0]}, index=idx)
        pd.testing.assert_frame_equal(splice_proxy(df, "VEA", "EFA"), df)
        only_efa = pd.DataFrame({"EFA": [1.0, 2.0, 3.0]}, index=idx)
        assert list(splice_proxy(only_efa, "VEA", "EFA")["VEA"]) == [1.0, 2.0, 3.0]

    def test_backtest_dziala_na_samym_efa_przed_debiutem_vea(self):
        prices, tb = _prices({**BASE, "SPY": -0.0003, "VEA": 0.0008})
        prices["EFA"] = prices["VEA"]
        prices.loc[prices.index[:400], "VEA"] = np.nan   # VEA "debiutuje" pozniej
        res = backtest_gold_momentum(prices, tb)
        assert res is not None
        assert res["equity"]["GEM Gold Momentum"].index[0] < prices.index[400]

    def test_sygnal_teraz_liczy_252_sesje(self):
        prices, tb = _prices(BASE, seed=4)
        out = gold_momentum_now(prices, tb)
        exp = prices["VEA"].iloc[-1] / prices["VEA"].iloc[-253] - 1
        assert out["returns"]["VEA"] == pytest.approx(exp, rel=1e-12)

    def test_sygnal_teraz_pomija_dni_bez_sesji_akcji(self):
        prices, tb = _prices(BASE, seed=6)
        extra = prices.index[-100] + pd.Timedelta(hours=12)   # dzien tylko z ^IRX
        p2 = pd.concat([prices, pd.DataFrame(index=[extra])]).sort_index()
        tb2 = tb.reindex(p2.index).ffill()
        a = gold_momentum_now(prices, tb)["returns"]["SPY"]
        b = gold_momentum_now(p2, tb2)["returns"]["SPY"]
        assert a == pytest.approx(b, rel=1e-12)
