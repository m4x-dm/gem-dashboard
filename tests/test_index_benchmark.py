"""Testy benchmarku indeksow GPW: sklejanie historii z ETF i wykrywanie nieswiezosci.

Kontekst: stooq.com przestal oddawac CSV (2026-08), a data/cache/*.csv zamarzly
na 2026-04-16. Zrodlem live sa teraz ETF-y Beta na GPW pobierane przez yfinance.
ETF-y siegaja 2019, wiec starsza historia idzie dalej z cache - sklejona
wspolczynnikiem na dacie styku (chain-linking).
"""

import pandas as pd
import pytest

from data.downloader import (
    GPW_INDEX_ETF,
    STOOQ_TICKERS,
    benchmark_status,
    splice_series,
)


def _series(start: str, periods: int, start_value: float, step: float) -> pd.Series:
    idx = pd.bdate_range(start=start, periods=periods)
    values = [start_value + i * step for i in range(periods)]
    return pd.Series(values, index=idx, dtype=float)


class TestSpliceSeries:
    """splice_series(hist, live) - historia z cache + ETF od daty styku."""

    def test_zwraca_live_gdy_brak_historii(self):
        live = _series("2024-01-01", 10, 100.0, 1.0)
        out = splice_series(None, live)
        pd.testing.assert_series_equal(out, live)

    def test_zwraca_historie_gdy_brak_live(self):
        hist = _series("2024-01-01", 10, 100.0, 1.0)
        out = splice_series(hist, None)
        pd.testing.assert_series_equal(out, hist)

    def test_oba_puste_daje_none(self):
        assert splice_series(None, None) is None
        assert splice_series(pd.Series(dtype=float), pd.Series(dtype=float)) is None

    def test_sklejone_konczy_sie_na_ostatniej_dacie_live(self):
        hist = _series("2020-01-01", 300, 1000.0, 1.0)
        live = _series("2021-01-01", 300, 50.0, 0.1)
        out = splice_series(hist, live)
        assert out.index[-1] == live.index[-1]
        assert out.index[0] == hist.index[0]

    def test_ciaglosc_na_dacie_styku(self):
        """Na dacie styku sklejona seria ma wartosc z historii, bez skoku."""
        hist = _series("2020-01-01", 300, 1000.0, 1.0)
        live = _series("2021-01-01", 300, 50.0, 0.1)
        out = splice_series(hist, live)

        join = live.index[0]
        assert out.loc[join] == pytest.approx(hist.loc[join])

        # brak skoku: zmiana dzien po dniu wokol styku jest niewielka
        pos = out.index.get_loc(join)
        before, after = out.iloc[pos - 1], out.iloc[pos + 1]
        assert abs(after / before - 1.0) < 0.05

    def test_zachowuje_dynamike_live_po_styku(self):
        """Po sklejeniu zwroty z czesci live sa identyczne jak w oryginale."""
        hist = _series("2020-01-01", 300, 1000.0, 1.0)
        live = _series("2021-01-01", 300, 50.0, 0.1)
        out = splice_series(hist, live)

        tail = out.loc[live.index[0]:]
        expected = live.pct_change().dropna()
        actual = tail.pct_change().dropna()
        pd.testing.assert_series_equal(actual, expected, check_names=False)

    def test_bez_pokrycia_zwraca_live(self):
        """Gdy historia konczy sie przed startem ETF, nie ma czego skleic."""
        hist = _series("2015-01-01", 100, 1000.0, 1.0)
        live = _series("2024-01-01", 100, 50.0, 0.1)
        out = splice_series(hist, live)
        pd.testing.assert_series_equal(out, live)

    def test_live_starszy_niz_historia_zwraca_live(self):
        hist = _series("2024-01-01", 50, 1000.0, 1.0)
        live = _series("2020-01-01", 800, 50.0, 0.1)
        out = splice_series(hist, live)
        assert out.index[0] == live.index[0]

    def test_wynik_jest_rosnacy_i_bez_duplikatow(self):
        hist = _series("2020-01-01", 300, 1000.0, 1.0)
        live = _series("2021-01-01", 300, 50.0, 0.1)
        out = splice_series(hist, live)
        assert out.index.is_monotonic_increasing
        assert not out.index.has_duplicates
        assert out.notna().all()

    def test_odporny_na_zera_w_live(self):
        """Zero na dacie styku nie moze wyprodukowac inf ani NaN."""
        hist = _series("2020-01-01", 300, 1000.0, 1.0)
        live = _series("2021-01-01", 300, 50.0, 0.1)
        live.iloc[0] = 0.0
        out = splice_series(hist, live)
        assert out is not None
        assert out.notna().all()
        assert (out.abs() != float("inf")).all()


class TestBenchmarkStatus:
    """benchmark_status(series) - wykrywanie cichej degradacji."""

    def test_swieza_seria_nie_jest_stale(self):
        idx = pd.bdate_range(end=pd.Timestamp.now().normalize(), periods=30)
        s = pd.Series(range(30), index=idx, dtype=float)
        status = benchmark_status(s)
        assert status["stale"] is False
        assert status["age_days"] <= 5
        assert status["last_date"] == idx[-1].date().isoformat()

    def test_stara_seria_jest_stale(self):
        idx = pd.bdate_range(end=pd.Timestamp.now().normalize() - pd.Timedelta(days=120), periods=30)
        s = pd.Series(range(30), index=idx, dtype=float)
        status = benchmark_status(s)
        assert status["stale"] is True
        assert status["age_days"] >= 100

    def test_prog_jest_konfigurowalny(self):
        idx = pd.bdate_range(end=pd.Timestamp.now().normalize() - pd.Timedelta(days=20), periods=30)
        s = pd.Series(range(30), index=idx, dtype=float)
        assert benchmark_status(s, max_age_days=10)["stale"] is True
        assert benchmark_status(s, max_age_days=60)["stale"] is False

    def test_pusta_seria_jest_stale(self):
        for empty in (None, pd.Series(dtype=float)):
            status = benchmark_status(empty)
            assert status["stale"] is True
            assert status["last_date"] is None


class TestEtfMapping:
    """Mapowanie indeks -> ETF musi pokrywac wszystkie indeksy GPW."""

    def test_kazdy_indeks_ma_etf(self):
        assert set(GPW_INDEX_ETF) == set(STOOQ_TICKERS)

    def test_tickery_etf_sa_z_gpw(self):
        for symbol, etf in GPW_INDEX_ETF.items():
            assert etf.endswith(".WA"), f"{symbol}: {etf} nie jest tickerem GPW"
