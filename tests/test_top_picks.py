"""Testy silnika Top Picks (F18) — syntetyczne ramki, bez sieci."""
import json

import numpy as np
import pandas as pd
import pytest

from data import top_picks as tp


def _frame(n_days: int = 400, tickers=("AAA", "BBB", "CCC"), start="2024-01-01"):
    """Ramka cen rosnacych liniowo, kazdy ticker o inny wspolczynnik."""
    idx = pd.bdate_range(start, periods=n_days)
    data = {}
    for i, t in enumerate(tickers):
        data[t] = np.linspace(100.0, 100.0 + 10 * (i + 1), n_days)
    return pd.DataFrame(data, index=idx)


def _volumes(prices: pd.DataFrame, shares: float = 1_000_000.0):
    return pd.DataFrame(shares, index=prices.index, columns=prices.columns)


def test_eligible_odrzuca_ticker_z_krotka_historia():
    prices = _frame(400, ("AAA", "BBB"))
    prices.loc[prices.index[:250], "BBB"] = np.nan  # BBB ma tylko 150 sesji
    vols = _volumes(prices)
    out = tp._eligible(prices, vols, prices.index[-1], min_turnover=0.0)
    assert "AAA" in out
    assert "BBB" not in out


def test_eligible_odrzuca_ticker_ponizej_progu_plynnosci():
    prices = _frame(400, ("AAA", "BBB"))
    vols = _volumes(prices)
    vols["BBB"] = 10.0  # ~1000 obrotu dziennie
    out = tp._eligible(prices, vols, prices.index[-1], min_turnover=1_000_000.0)
    assert "AAA" in out
    assert "BBB" not in out


def test_select_picks_zwraca_dokladnie_top_n():
    tickers = tuple(f"T{i}" for i in range(10))
    prices = _frame(400, tickers)
    vols = _volumes(prices)
    groups = {t: f"S{i}" for i, t in enumerate(tickers)}  # kazdy inny sektor
    picks = tp.select_picks(prices, vols, groups, prices.index[-1], top_n=5)
    assert len(picks) == 5
    scores = [p["score"] for p in picks]
    assert scores == sorted(scores, reverse=True), "wynik nie jest posortowany malejaco"
    assert len({p["ticker"] for p in picks}) == 5, "duplikaty w skladzie"


def test_select_picks_egzekwuje_limit_sektorowy():
    # 5 najmocniejszych tickerow w jednym sektorze, 3 slabsze w innych
    tickers = ("A1", "A2", "A3", "A4", "A5", "B1", "C1", "D1")
    idx = pd.bdate_range("2024-01-01", periods=400)
    data = {}
    for i, t in enumerate(tickers[:5]):
        data[t] = np.linspace(100.0, 400.0 - i, 400)      # mocne
    for i, t in enumerate(tickers[5:]):
        data[t] = np.linspace(100.0, 120.0 - i, 400)      # slabe
    prices = pd.DataFrame(data, index=idx)
    vols = _volumes(prices)
    groups = {t: ("SEKTOR_A" if t.startswith("A") else t[0]) for t in tickers}

    picks = tp.select_picks(prices, vols, groups, idx[-1], top_n=5, max_per_group=2)

    assert len(picks) == 5
    a_count = sum(1 for p in picks if p["group"] == "SEKTOR_A")
    assert a_count == 2, f"limit sektorowy zlamany: {a_count} spolek z SEKTOR_A"


def test_select_picks_nie_widzi_przyszlosci():
    """asof=T musi dac ten sam wynik z ramka pelna i z ramka przycieta do T."""
    tickers = tuple(f"T{i}" for i in range(8))
    prices = _frame(500, tickers)
    # Po dacie T odwracamy trendy — gdyby regula podgladala przyszlosc,
    # wynik na pelnej ramce bylby inny.
    asof = prices.index[400]
    prices.loc[prices.index[401]:] = prices.loc[prices.index[401]:].iloc[::-1].values
    vols = _volumes(prices)
    groups = {t: f"S{i}" for i, t in enumerate(tickers)}

    full = tp.select_picks(prices, vols, groups, asof, top_n=5)
    trimmed = tp.select_picks(prices.loc[:asof], vols.loc[:asof], groups, asof, top_n=5)

    assert [p["ticker"] for p in full] == [p["ticker"] for p in trimmed]
    assert [p["entry_price"] for p in full] == [p["entry_price"] for p in trimmed]


def test_select_picks_wagi_sumuja_sie_do_jeden():
    tickers = tuple(f"T{i}" for i in range(6))
    prices = _frame(400, tickers)
    vols = _volumes(prices)
    groups = {t: f"S{i}" for i, t in enumerate(tickers)}
    picks = tp.select_picks(prices, vols, groups, prices.index[-1], top_n=5)
    assert sum(p["weight"] for p in picks) == pytest.approx(1.0, abs=1e-6)


def test_append_snapshot_tworzy_plik_gdy_nie_istnieje(tmp_path):
    path = tmp_path / "hist.json"
    payload = {"asof": "2026-07-31", "rule_version": 1, "sp500": [], "gpw": []}
    added = tp.append_snapshot("2026-08-01", payload, path=path)
    assert added is True
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert "2026-08-01" in saved
    assert saved["2026-08-01"]["asof"] == "2026-07-31"


def test_append_snapshot_nie_nadpisuje_istniejacego_miesiaca(tmp_path):
    path = tmp_path / "hist.json"
    first = {"asof": "2026-07-31", "rule_version": 1, "sp500": [{"ticker": "MU"}], "gpw": []}
    second = {"asof": "2026-07-31", "rule_version": 1, "sp500": [{"ticker": "XXX"}], "gpw": []}
    tp.append_snapshot("2026-08-01", first, path=path)
    added = tp.append_snapshot("2026-08-01", second, path=path)
    assert added is False
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["2026-08-01"]["sp500"][0]["ticker"] == "MU", "log zostal nadpisany"


def test_portfolio_equity_liczy_zwrot_recznie_sprawdzalny():
    idx = pd.bdate_range("2026-01-01", periods=45)
    prices = pd.DataFrame({
        "AAA": np.linspace(100.0, 110.0, 45),   # +10%
        "BBB": np.linspace(50.0, 60.0, 45),     # +20%
    }, index=idx)
    history = {
        "2026-01-01": {
            "asof": idx[0].strftime("%Y-%m-%d"),
            "sp500": [
                {"ticker": "AAA", "weight": 0.5, "entry_price": 100.0},
                {"ticker": "BBB", "weight": 0.5, "entry_price": 50.0},
            ],
        }
    }
    equity = tp.portfolio_equity(history, prices, "sp500", start_capital=10000.0)
    # 50% * 1.10 + 50% * 1.20 = 1.15
    assert float(equity.iloc[-1]) == pytest.approx(11500.0, rel=1e-6)
    assert float(equity.iloc[0]) == pytest.approx(10000.0, rel=1e-9)


def test_portfolio_equity_z_pustym_logiem_zwraca_pusta_serie():
    prices = _frame(50, ("AAA",))
    equity = tp.portfolio_equity({}, prices, "sp500")
    assert isinstance(equity, pd.Series)
    assert equity.empty


def test_simulate_rule_zwraca_miesieczna_serie_i_reaguje_na_koszty():
    tickers = tuple(f"T{i}" for i in range(8))
    prices = _frame(700, tickers, start="2023-01-02")
    vols = _volumes(prices)
    groups = {t: f"S{i}" for i, t in enumerate(tickers)}

    bez_kosztow = tp.simulate_rule(prices, vols, groups, start=prices.index[300],
                                   min_turnover=0.0, transaction_cost=0.0, tax_belka=0.0)
    z_kosztami = tp.simulate_rule(prices, vols, groups, start=prices.index[300],
                                  min_turnover=0.0, transaction_cost=0.01, tax_belka=0.0)

    assert isinstance(bez_kosztow, pd.Series)
    assert len(bez_kosztow) >= 6, "za malo punktow miesiecznych"
    assert isinstance(bez_kosztow.index, pd.DatetimeIndex)
    assert float(z_kosztami.iloc[-1]) < float(bez_kosztow.iloc[-1]), \
        "koszty transakcyjne nie obnizyly wyniku"
